from __future__ import annotations

import uuid
from sqlalchemy.orm import Session
from .models import Artifact, ExperimentRun, LogEvent, MetricPoint
from .schemas import RunCreate
from .utils import dumps, loads


def create_run(db: Session, payload: RunCreate) -> ExperimentRun:
    run = ExperimentRun(
        id=f"run_{uuid.uuid4().hex[:12]}",
        name=payload.name,
        task_type=payload.task_type,
        dataset=payload.dataset,
        model_name=payload.model_name,
        seed=payload.seed,
        config_json=dumps(payload.config or {}),
        summary_json="{}",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def add_log(db: Session, run_id: str, message: str, level: str = "INFO") -> LogEvent:
    row = LogEvent(run_id=run_id, message=message, level=level)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_metric(db: Session, run_id: str, step: int, **values) -> MetricPoint:
    row = MetricPoint(run_id=run_id, step=step, **values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_artifact(db: Session, run_id: str, kind: str, name: str, path: str, metadata: dict | None = None) -> Artifact:
    row = Artifact(run_id=run_id, kind=kind, name=name, path=path, metadata_json=dumps(metadata or {}))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_to_response(run: ExperimentRun) -> dict:
    return {
        "id": run.id,
        "name": run.name,
        "task_type": run.task_type,
        "dataset": run.dataset,
        "model_name": run.model_name,
        "status": run.status,
        "seed": run.seed,
        "git_commit": run.git_commit,
        "config": loads(run.config_json),
        "summary": loads(run.summary_json),
        "error_message": run.error_message,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


def artifact_to_response(artifact: Artifact) -> dict:
    return {
        "id": artifact.id,
        "run_id": artifact.run_id,
        "kind": artifact.kind,
        "name": artifact.name,
        "path": artifact.path,
        "metadata": loads(artifact.metadata_json),
        "created_at": artifact.created_at,
    }
