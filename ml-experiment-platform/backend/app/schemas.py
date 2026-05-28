from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    name: str = Field(default="Demo Experiment", min_length=2, max_length=160)
    task_type: str = Field(default="classification")
    dataset: str = Field(default="synthetic-customer-churn")
    model_name: str = Field(default="GradientBoostingClassifier")
    seed: int = 42
    config: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    id: str
    name: str
    task_type: str
    dataset: str
    model_name: str
    status: str
    seed: int
    git_commit: str | None
    config: dict[str, Any]
    summary: dict[str, Any]
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class MetricResponse(BaseModel):
    id: int
    run_id: str
    step: int
    train_loss: float | None
    val_loss: float | None
    accuracy: float | None
    f1: float | None
    auroc: float | None
    rmse: float | None
    mae: float | None
    r2: float | None
    learning_rate: float | None
    created_at: datetime


class LogResponse(BaseModel):
    id: int
    run_id: str
    level: str
    message: str
    created_at: datetime


class ArtifactResponse(BaseModel):
    id: int
    run_id: str
    kind: str
    name: str
    path: str
    metadata: dict[str, Any]
    created_at: datetime


class CompareRow(BaseModel):
    id: str
    name: str
    status: str
    task_type: str
    dataset: str
    model_name: str
    best_metric: str | None
    best_value: float | None
    final_train_loss: float | None
    final_val_loss: float | None
    duration_seconds: float | None
