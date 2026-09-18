import type { DashboardSummary } from '../types';
import './KpiBar.css';

function trustColor(score: number) {
  if (score >= 80) return 'var(--signal-good)';
  if (score >= 60) return 'var(--signal-warn)';
  return 'var(--signal-bad)';
}

export default function KpiBar({ summary, connected }: { summary: DashboardSummary | null; connected: boolean }) {
  return (
    <div className="kpi-bar">
      <div className="kpi-cell">
        <span className="kpi-label">Network</span>
        <span className="kpi-value">
          {summary ? `${summary.healthy_stations}/${summary.total_stations}` : '—'}
          <span className="kpi-unit">stations healthy</span>
        </span>
      </div>
      <div className="kpi-divider" />
      <div className="kpi-cell">
        <span className="kpi-label">Active Alerts</span>
        <span className="kpi-value" style={{ color: summary && summary.active_alerts > 0 ? 'var(--signal-bad)' : 'var(--signal-good)' }}>
          {summary ? summary.active_alerts : '—'}
        </span>
      </div>
      <div className="kpi-divider" />
      <div className="kpi-cell">
        <span className="kpi-label">Avg Trust Score</span>
        <span className="kpi-value" style={{ color: summary ? trustColor(summary.avg_trust_score) : undefined }}>
          {summary ? `${summary.avg_trust_score}%` : '—'}
        </span>
      </div>
      <div className="kpi-divider" />
      <div className="kpi-cell kpi-cell-wide">
        <span className="kpi-label">Root Causes (open)</span>
        <div className="kpi-tags">
          {summary && Object.keys(summary.root_cause_breakdown).length > 0 ? (
            Object.entries(summary.root_cause_breakdown).map(([cause, count]) => (
              <span key={cause} className="kpi-tag">{cause.replace('_', ' ')} · {count}</span>
            ))
          ) : (
            <span className="kpi-tag kpi-tag-muted">none</span>
          )}
        </div>
      </div>
      <div className="kpi-connection">
        <span className={`dot ${connected ? 'dot-live' : 'dot-dead'}`} />
        {connected ? 'Live' : 'Reconnecting…'}
      </div>
    </div>
  );
}
