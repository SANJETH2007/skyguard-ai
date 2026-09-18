import { AnimatePresence, motion } from 'framer-motion';
import type { Anomaly } from '../types';
import { ROOT_CAUSE_LABELS } from '../types';
import './AnomalyFeed.css';

function causeClass(cause: string) {
  switch (cause) {
    case 'HARDWARE_FAULT': return 'cause-bad';
    case 'COMMS_LOSS': return 'cause-bad';
    case 'SENSOR_DRIFT': return 'cause-warn';
    case 'CALIBRATION_ERROR': return 'cause-warn';
    case 'EXTREME_WEATHER': return 'cause-info';
    default: return 'cause-neutral';
  }
}

export default function AnomalyFeed({
  anomalies,
  onFeedback,
}: {
  anomalies: Anomaly[];
  onFeedback: (id: string, verdict: 'CONFIRMED' | 'FALSE_POSITIVE') => void;
}) {
  return (
    <div className="anomaly-feed">
      <div className="feed-header">
        <span>Live Anomaly Feed</span>
        <span className="feed-count">{anomalies.length}</span>
      </div>
      <div className="feed-list">
        <AnimatePresence initial={false}>
          {anomalies.length === 0 && (
            <div className="feed-empty">No anomalies detected — network nominal.</div>
          )}
          {anomalies.map((a) => (
            <motion.div
              key={a.id}
              layout
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              className={`feed-card ${causeClass(a.root_cause)}`}
            >
              <div className="feed-card-top">
                <span className="feed-station">{a.station_name}</span>
                <span className="feed-trust">{a.trust_score}%</span>
              </div>
              <div className="feed-cause">{ROOT_CAUSE_LABELS[a.root_cause] ?? a.root_cause} · {a.parameter.replace('_', ' ')}</div>
              <p className="feed-explanation">{a.explanation}</p>
              {a.status === 'OPEN' && (
                <div className="feed-actions">
                  <button onClick={() => onFeedback(a.id, 'CONFIRMED')} className="feed-btn feed-btn-confirm">Confirm</button>
                  <button onClick={() => onFeedback(a.id, 'FALSE_POSITIVE')} className="feed-btn feed-btn-dismiss">False positive</button>
                </div>
              )}
              {a.status !== 'OPEN' && <div className="feed-status">{a.status.toLowerCase()}</div>}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
