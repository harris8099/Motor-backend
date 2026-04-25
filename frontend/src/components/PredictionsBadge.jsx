import React from 'react';

function formatPredictionName(value) {
  return value.replace(/_/g, ' ');
}

function formatDetails(details) {
  return JSON.stringify(details).replace(/["{}]/g, ' ').trim();
}

export default function PredictionsBadge({ predictions }) {
  if (!predictions || predictions.length === 0) {
    return <div className="empty-copy">No active AI alerts.</div>;
  }

  return (
    <div>
      {predictions.map((pred) => (
        <div key={pred.id} className={`prediction-badge severity-${pred.severity}`}>
          <div className="prediction-header">
            <span className="prediction-type">{formatPredictionName(pred.prediction_type)}</span>
            <span className="prediction-conf">{(pred.confidence * 100).toFixed(0)}% conf</span>
          </div>
          {pred.details && <div className="prediction-details">{formatDetails(pred.details)}</div>}
        </div>
      ))}
    </div>
  );
}
