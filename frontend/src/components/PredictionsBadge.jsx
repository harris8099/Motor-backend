import React from 'react';

export default function PredictionsBadge({ predictions }) {
  if (!predictions || predictions.length === 0) {
    return <div style={{ color: 'var(--text-muted)' }}>No active AI alerts.</div>;
  }

  return (
    <div>
      {predictions.map(pred => (
        <div key={pred.id} className={`prediction-badge severity-${pred.severity}`}>
          <div className="prediction-header">
            <span className="prediction-type">{pred.prediction_type.replace('_', ' ')}</span>
            <span className="prediction-conf">{(pred.confidence * 100).toFixed(0)}% Conf</span>
          </div>
          {pred.details && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              {JSON.stringify(pred.details).replace(/["{}]/g, ' ')}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
