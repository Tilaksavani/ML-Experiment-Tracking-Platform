from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db, init_db
from .experiments.runner import run_demo_experiment
from .models import Artifact, ExperimentRun, LogEvent, MetricPoint
from .repository import artifact_to_response, create_run, run_to_response
from .schemas import ArtifactResponse, CompareRow, LogResponse, MetricResponse, RunCreate, RunResponse
from .utils import duration_seconds

settings = get_settings()

app = FastAPI(
    title="ML Experiment Control Platform",
    version="1.0.0",
    description="Internal ML platform APIs for experiment lifecycle tracking, metric visualization, logs, and artifacts.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ml-experiment-platform"}


@app.post("/runs", response_model=RunResponse)
def create_experiment_run(payload: RunCreate, db: Annotated[Session, Depends(get_db)]):
    run = create_run(db, payload)
    return run_to_response(run)


@app.post("/runs/demo/start", response_model=RunResponse)
def create_and_start_demo_run(
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    task_type: str = Query(default="classification", pattern="^(classification|regression|forecasting)$"),
):
    presets = {
        "classification": ("Customer Churn Classifier", "synthetic-customer-churn", "GradientBoostingClassifier"),
        "regression": ("Demand Forecasting Regressor", "synthetic-demand-forecasting", "RandomForestRegressor"),
        "forecasting": ("Sales Forecasting Model", "synthetic-sales-series", "TemporalMLP"),
    }
    name, dataset, model_name = presets[task_type]
    payload = RunCreate(
        name=name,
        task_type=task_type,
        dataset=dataset,
        model_name=model_name,
        seed=42,
        config={"epochs": 20, "learning_rate": 0.001, "batch_size": 64, "source": "demo"},
    )
    run = create_run(db, payload)
    background_tasks.add_task(run_demo_experiment, run.id)
    db.refresh(run)
    return run_to_response(run)


@app.post("/runs/{run_id}/start", response_model=RunResponse)
def start_existing_run(run_id: str, background_tasks: BackgroundTasks, db: Annotated[Session, Depends(get_db)]):
    run = db.get(ExperimentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in {"running", "completed"}:
        raise HTTPException(status_code=409, detail=f"Run is already {run.status}")
    background_tasks.add_task(run_demo_experiment, run.id)
    return run_to_response(run)


@app.get("/runs", response_model=list[RunResponse])
def list_runs(
    db: Annotated[Session, Depends(get_db)],
    status: str | None = None,
    dataset: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    query = db.query(ExperimentRun)
    if status:
        query = query.filter(ExperimentRun.status == status)
    if dataset:
        query = query.filter(ExperimentRun.dataset == dataset)
    rows = query.order_by(ExperimentRun.created_at.desc()).limit(limit).all()
    return [run_to_response(row) for row in rows]


@app.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Annotated[Session, Depends(get_db)]):
    run = db.get(ExperimentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_to_response(run)


@app.get("/runs/{run_id}/metrics", response_model=list[MetricResponse])
def get_metrics(run_id: str, db: Annotated[Session, Depends(get_db)]):
    rows = db.query(MetricPoint).filter(MetricPoint.run_id == run_id).order_by(MetricPoint.step).all()
    return rows


@app.get("/runs/{run_id}/logs", response_model=list[LogResponse])
def get_logs(run_id: str, db: Annotated[Session, Depends(get_db)]):
    rows = db.query(LogEvent).filter(LogEvent.run_id == run_id).order_by(LogEvent.id).all()
    return rows


@app.get("/runs/{run_id}/artifacts", response_model=list[ArtifactResponse])
def get_artifacts(run_id: str, db: Annotated[Session, Depends(get_db)]):
    rows = db.query(Artifact).filter(Artifact.run_id == run_id).order_by(Artifact.created_at.desc()).all()
    return [artifact_to_response(row) for row in rows]


@app.get("/compare", response_model=list[CompareRow])
def compare_runs(ids: str, db: Annotated[Session, Depends(get_db)]):
    run_ids = [item.strip() for item in ids.split(",") if item.strip()]
    if not run_ids:
        return []
    rows: list[CompareRow] = []
    for run_id in run_ids:
        run = db.get(ExperimentRun, run_id)
        if not run:
            continue
        final = db.query(MetricPoint).filter(MetricPoint.run_id == run.id).order_by(MetricPoint.step.desc()).first()
        best_metric = None
        best_value = None
        if final:
            if run.task_type in {"regression", "forecasting"}:
                best_metric, best_value = "r2", final.r2
            else:
                best_metric, best_value = "auroc", final.auroc
        rows.append(
            CompareRow(
                id=run.id,
                name=run.name,
                status=run.status,
                task_type=run.task_type,
                dataset=run.dataset,
                model_name=run.model_name,
                best_metric=best_metric,
                best_value=best_value,
                final_train_loss=final.train_loss if final else None,
                final_val_loss=final.val_loss if final else None,
                duration_seconds=duration_seconds(run.started_at, run.finished_at),
            )
        )
    return rows


@app.delete("/runs/{run_id}")
def delete_run(run_id: str, db: Annotated[Session, Depends(get_db)]):
    run = db.get(ExperimentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    db.delete(run)
    db.commit()
    return {"deleted": run_id}


@app.get("/events/{run_id}")
async def stream_run_events(run_id: str):
    async def event_generator():
        last_log_id = 0
        for _ in range(300):
            db = next(get_db())
            try:
                run = db.get(ExperimentRun, run_id)
                if not run:
                    yield "event: error\ndata: run not found\n\n"
                    break
                logs = (
                    db.query(LogEvent)
                    .filter(LogEvent.run_id == run_id, LogEvent.id > last_log_id)
                    .order_by(LogEvent.id)
                    .all()
                )
                for log in logs:
                    last_log_id = log.id
                    yield f"event: log\ndata: [{log.level}] {log.message}\n\n"
                yield f"event: status\ndata: {run.status}\n\n"
                if run.status in {"completed", "failed"}:
                    break
            finally:
                db.close()
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
