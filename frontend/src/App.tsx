import { useEffect, useMemo, useState } from 'react';
import { api } from './api';
import type { Artifact, CompareRow, LogEvent, MetricPoint, Run } from './types';

function fmt(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return Number(value).toFixed(4);
}

function statusClass(status: string) {
  return `status status-${status}`;
}

function MetricChart({ metrics }: { metrics: MetricPoint[] }) {
  const width = 720;
  const height = 220;
  const pad = 28;
  const points = metrics.filter((m) => m.val_loss !== null && m.val_loss !== undefined);
  if (points.length < 2) return <div className="empty">No metric history yet.</div>;

  const values = points.map((p) => p.val_loss ?? 0);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;

  const path = points
    .map((p, idx) => {
      const x = pad + (idx / (points.length - 1)) * (width - pad * 2);
      const y = height - pad - (((p.val_loss ?? 0) - min) / span) * (height - pad * 2);
      return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');

  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Validation loss chart">
      <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} />
      <line x1={pad} y1={pad} x2={pad} y2={height - pad} />
      <path d={path} fill="none" strokeWidth="3" />
      <text x={pad} y={18}>val_loss</text>
      <text x={width - 105} y={height - 8}>steps: {points.length}</text>
    </svg>
  );
}

function KpiCards({ runs }: { runs: Run[] }) {
  const completed = runs.filter((r) => r.status === 'completed').length;
  const running = runs.filter((r) => r.status === 'running').length;
  const datasets = new Set(runs.map((r) => r.dataset)).size;
  return (
    <div className="kpis">
      <div className="card"><span>Total Runs</span><strong>{runs.length}</strong></div>
      <div className="card"><span>Running</span><strong>{running}</strong></div>
      <div className="card"><span>Completed</span><strong>{completed}</strong></div>
      <div className="card"><span>Datasets</span><strong>{datasets}</strong></div>
    </div>
  );
}

function App() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [metrics, setMetrics] = useState<MetricPoint[]>([]);
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [compareRows, setCompareRows] = useState<CompareRow[]>([]);
  const [taskType, setTaskType] = useState('classification');
  const [filter, setFilter] = useState('');
  const [streamLines, setStreamLines] = useState<string[]>([]);
  const [error, setError] = useState<string>('');

  async function refreshRuns() {
    const data = await api.listRuns();
    setRuns(data);
    if (!selectedId && data.length > 0) setSelectedId(data[0].id);
  }

  async function loadRunDetails(runId: string) {
    if (!runId) return;
    const [metricData, logData, artifactData] = await Promise.all([
      api.getMetrics(runId),
      api.getLogs(runId),
      api.getArtifacts(runId),
    ]);
    setMetrics(metricData);
    setLogs(logData);
    setArtifacts(artifactData);
  }

  async function startDemo() {
    setError('');
    const run = await api.startDemo(taskType);
    setSelectedId(run.id);
    await refreshRuns();
  }

  async function compareSelected() {
    const ids = runs.slice(0, 3).map((r) => r.id);
    const data = await api.compare(ids);
    setCompareRows(data);
  }

  useEffect(() => {
    refreshRuns().catch((err) => setError(err.message));
    const timer = window.setInterval(() => refreshRuns().catch(() => undefined), 3000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    loadRunDetails(selectedId).catch((err) => setError(err.message));
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    const source = new EventSource(api.eventsUrl(selectedId));
    source.addEventListener('log', (event) => {
      setStreamLines((old) => [`${new Date().toLocaleTimeString()} ${event.data}`, ...old].slice(0, 8));
    });
    source.addEventListener('status', () => {
      refreshRuns().catch(() => undefined);
      loadRunDetails(selectedId).catch(() => undefined);
    });
    source.onerror = () => source.close();
    return () => source.close();
  }, [selectedId]);

  const filteredRuns = useMemo(() => {
    const query = filter.toLowerCase();
    return runs.filter((r) => [r.name, r.dataset, r.model_name, r.status].join(' ').toLowerCase().includes(query));
  }, [runs, filter]);

  const selected = runs.find((r) => r.id === selectedId);

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="logo">ML Hub</div>
        <p>Experiment lifecycle, metrics, logs, artifacts, and model comparison.</p>
        <div className="control">
          <label>Demo task</label>
          <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
            <option value="classification">Classification</option>
            <option value="regression">Regression</option>
            <option value="forecasting">Forecasting</option>
          </select>
        </div>
        <button onClick={startDemo}>Start demo run</button>
        <button className="secondary" onClick={compareSelected}>Compare latest 3</button>
      </aside>

      <section className="content">
        <header className="hero">
          <div>
            <p className="eyebrow">AI Infrastructure Portfolio Project</p>
            <h1>ML Experiment Control Platform</h1>
            <p>Launch, monitor, compare, and audit ML runs from one dashboard.</p>
          </div>
        </header>

        {error && <div className="error">{error}</div>}
        <KpiCards runs={runs} />

        <section className="grid two">
          <div className="panel">
            <div className="panel-head">
              <h2>Runs</h2>
              <input placeholder="Filter runs" value={filter} onChange={(e) => setFilter(e.target.value)} />
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Name</th><th>Status</th><th>Dataset</th><th>Model</th></tr>
                </thead>
                <tbody>
                  {filteredRuns.map((run) => (
                    <tr key={run.id} onClick={() => setSelectedId(run.id)} className={run.id === selectedId ? 'active' : ''}>
                      <td>{run.name}<small>{run.id}</small></td>
                      <td><span className={statusClass(run.status)}>{run.status}</span></td>
                      <td>{run.dataset}</td>
                      <td>{run.model_name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel">
            <h2>Selected Run</h2>
            {selected ? (
              <div className="details">
                <h3>{selected.name}</h3>
                <p><b>Status:</b> <span className={statusClass(selected.status)}>{selected.status}</span></p>
                <p><b>Task:</b> {selected.task_type}</p>
                <p><b>Model:</b> {selected.model_name}</p>
                <p><b>Seed:</b> {selected.seed}</p>
                <pre>{JSON.stringify(selected.summary, null, 2)}</pre>
              </div>
            ) : <div className="empty">Start a demo run to see details.</div>}
          </div>
        </section>

        <section className="panel">
          <h2>Validation Loss Trend</h2>
          <MetricChart metrics={metrics} />
        </section>

        <section className="grid two">
          <div className="panel">
            <h2>Live Stream</h2>
            <div className="logbox">
              {streamLines.length === 0 ? <span>No stream events yet.</span> : streamLines.map((line, i) => <p key={i}>{line}</p>)}
            </div>
            <h2>Stored Logs</h2>
            <div className="logbox compact">
              {logs.map((log) => <p key={log.id}>[{log.level}] {log.message}</p>)}
            </div>
          </div>
          <div className="panel">
            <h2>Artifacts</h2>
            <div className="artifact-list">
              {artifacts.length === 0 ? <div className="empty">Artifacts appear after a run completes.</div> : artifacts.map((artifact) => (
                <div className="artifact" key={artifact.id}>
                  <strong>{artifact.name}</strong>
                  <span>{artifact.kind}</span>
                  <code>{artifact.path}</code>
                </div>
              ))}
            </div>
          </div>
        </section>

        {compareRows.length > 0 && (
          <section className="panel">
            <h2>Run Comparison</h2>
            <table>
              <thead><tr><th>Run</th><th>Status</th><th>Metric</th><th>Value</th><th>Val Loss</th><th>Duration</th></tr></thead>
              <tbody>
                {compareRows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.name}</td>
                    <td><span className={statusClass(row.status)}>{row.status}</span></td>
                    <td>{row.best_metric ?? '—'}</td>
                    <td>{fmt(row.best_value)}</td>
                    <td>{fmt(row.final_val_loss)}</td>
                    <td>{row.duration_seconds ?? '—'}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </section>
    </main>
  );
}

export default App;
