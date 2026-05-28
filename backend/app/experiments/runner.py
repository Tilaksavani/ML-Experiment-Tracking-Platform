from __future__ import annotations

import csv
import json
import math
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ExperimentRun, MetricPoint
from app.repository import add_artifact, add_log, add_metric
from app.utils import dumps, loads


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None


def _run_dir(run_id: str) -> Path:
    path = Path("storage") / "runs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _metric_curve(step: int, total_steps: int, rng: random.Random, task_type: str) -> dict:
    progress = step / max(total_steps, 1)
    noise = rng.uniform(-0.015, 0.015)
    train_loss = max(0.05, 1.4 * math.exp(-2.8 * progress) + rng.uniform(0.0, 0.04))
    val_loss = max(0.06, 1.5 * math.exp(-2.4 * progress) + 0.08 + rng.uniform(0.0, 0.05))
    lr = 0.001 * (0.98 ** step)

    if task_type == "regression" or task_type == "forecasting":
        rmse = max(12.0, 180 * math.exp(-2.1 * progress) + rng.uniform(-4, 4))
        mae = max(8.0, rmse * 0.72 + rng.uniform(-2, 2))
        r2 = min(0.96, 0.42 + 0.52 * progress + noise)
        return {
            "train_loss": round(train_loss, 5),
            "val_loss": round(val_loss, 5),
            "accuracy": None,
            "f1": None,
            "auroc": None,
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "r2": round(r2, 4),
            "learning_rate": round(lr, 8),
        }

    accuracy = min(0.985, 0.58 + 0.36 * progress + noise)
    f1 = min(0.975, 0.50 + 0.39 * progress + noise)
    auroc = min(0.995, 0.64 + 0.32 * progress + noise)
    return {
        "train_loss": round(train_loss, 5),
        "val_loss": round(val_loss, 5),
        "accuracy": round(accuracy, 4),
        "f1": round(f1, 4),
        "auroc": round(auroc, 4),
        "rmse": None,
        "mae": None,
        "r2": None,
        "learning_rate": round(lr, 8),
    }


def _write_artifacts(db: Session, run: ExperimentRun) -> None:
    run_dir = _run_dir(run.id)
    metrics = db.query(MetricPoint).filter(MetricPoint.run_id == run.id).order_by(MetricPoint.step).all()

    config_path = run_dir / "config.json"
    config_path.write_text(json.dumps(loads(run.config_json), indent=2), encoding="utf-8")
    add_artifact(db, run.id, "config", "config.json", str(config_path), {"description": "Experiment configuration"})

    metrics_path = run_dir / "metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["step", "train_loss", "val_loss", "accuracy", "f1", "auroc", "rmse", "mae", "r2", "learning_rate"])
        for m in metrics:
            writer.writerow([m.step, m.train_loss, m.val_loss, m.accuracy, m.f1, m.auroc, m.rmse, m.mae, m.r2, m.learning_rate])
    add_artifact(db, run.id, "metrics", "metrics.csv", str(metrics_path), {"rows": len(metrics)})

    rng = np.random.default_rng(run.seed)
    prediction_path = run_dir / "predictions_sample.csv"
    with prediction_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["row_id", "prediction", "confidence"])
        for idx in range(50):
            writer.writerow([idx, int(rng.random() > 0.5), round(float(rng.uniform(0.55, 0.99)), 4)])
    add_artifact(db, run.id, "predictions", "predictions_sample.csv", str(prediction_path), {"sample_rows": 50})

    summary = loads(run.summary_json)
    card = f"""# Model Card: {run.model_name}

Run ID: `{run.id}`  
Dataset: `{run.dataset}`  
Task: `{run.task_type}`  
Status: `{run.status}`  

## Final Summary

```json
{json.dumps(summary, indent=2)}
```

## Intended Use

This is a demo model run for validating experiment tracking, dashboarding, artifact management, and run comparison workflows.

## Limitations

Synthetic training curves are generated for platform demonstration. Replace this runner with real PyTorch/TensorFlow training before presenting as a production ML result.
"""
    card_path = run_dir / "model_card.md"
    card_path.write_text(card, encoding="utf-8")
    add_artifact(db, run.id, "model_card", "model_card.md", str(card_path), {"format": "markdown"})


def run_demo_experiment(run_id: str, total_steps: int = 20, sleep_seconds: float = 0.2) -> None:
    db = SessionLocal()
    try:
        run = db.get(ExperimentRun, run_id)
        if not run:
            return

        rng = random.Random(run.seed)
        run.status = "running"
        run.git_commit = _git_commit()
        run.started_at = datetime.now(timezone.utc)
        run.error_message = None
        db.commit()

        add_log(db, run.id, f"Starting {run.task_type} experiment with model={run.model_name}, dataset={run.dataset}")
        add_log(db, run.id, "Resolved run configuration and initialized metric writers")

        for step in range(1, total_steps + 1):
            metrics = _metric_curve(step, total_steps, rng, run.task_type)
            add_metric(db, run.id, step, **metrics)
            if step == 1:
                add_log(db, run.id, "First metric checkpoint recorded")
            elif step % 5 == 0:
                add_log(db, run.id, f"Checkpoint {step}/{total_steps}: validation loss={metrics['val_loss']}")
            time.sleep(sleep_seconds)

        final = db.query(MetricPoint).filter(MetricPoint.run_id == run.id).order_by(MetricPoint.step.desc()).first()
        summary = {
            "final_train_loss": final.train_loss if final else None,
            "final_val_loss": final.val_loss if final else None,
            "final_accuracy": final.accuracy if final else None,
            "final_f1": final.f1 if final else None,
            "final_auroc": final.auroc if final else None,
            "final_rmse": final.rmse if final else None,
            "final_mae": final.mae if final else None,
            "final_r2": final.r2 if final else None,
            "steps": total_steps,
        }
        run.summary_json = dumps(summary)
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

        add_log(db, run.id, "Training completed successfully")
        _write_artifacts(db, run)
        add_log(db, run.id, "Artifacts generated: config, metrics CSV, predictions sample, model card")
    except Exception as exc:
        run = db.get(ExperimentRun, run_id)
        if run:
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            add_log(db, run.id, f"Run failed: {exc}", level="ERROR")
    finally:
        db.close()
