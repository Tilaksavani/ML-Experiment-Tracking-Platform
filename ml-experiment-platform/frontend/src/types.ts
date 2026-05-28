export type RunStatus = 'created' | 'running' | 'completed' | 'failed';

export interface Run {
  id: string;
  name: string;
  task_type: string;
  dataset: string;
  model_name: string;
  status: RunStatus;
  seed: number;
  git_commit?: string | null;
  config: Record<string, unknown>;
  summary: Record<string, number | string | null>;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface MetricPoint {
  id: number;
  run_id: string;
  step: number;
  train_loss?: number | null;
  val_loss?: number | null;
  accuracy?: number | null;
  f1?: number | null;
  auroc?: number | null;
  rmse?: number | null;
  mae?: number | null;
  r2?: number | null;
  learning_rate?: number | null;
  created_at: string;
}

export interface LogEvent {
  id: number;
  run_id: string;
  level: string;
  message: string;
  created_at: string;
}

export interface Artifact {
  id: number;
  run_id: string;
  kind: string;
  name: string;
  path: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface CompareRow {
  id: string;
  name: string;
  status: string;
  task_type: string;
  dataset: string;
  model_name: string;
  best_metric?: string | null;
  best_value?: number | null;
  final_train_loss?: number | null;
  final_val_loss?: number | null;
  duration_seconds?: number | null;
}
