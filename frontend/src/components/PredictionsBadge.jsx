import React from 'react';

function formatPredictionName(value) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatDetails(details) {
  if (typeof details === 'string') {
    try {
      const parsed = JSON.parse(details);
      return formatDetails(parsed);
    } catch {
      return details.replace(/["{}]/g, ' ').trim();
    }
  }
  
  if (typeof details === 'object') {
    if (details.health_assessment) {
      // AI Analysis from Gemini
      return (
        <div className="ai-analysis">
          <div className="ai-health">
            <strong>Health:</strong> {details.health_assessment}
          </div>
          {details.key_concerns && (
            <div className="ai-concerns">
              <strong>Concerns:</strong> {details.key_concerns}
            </div>
          )}
          {details.recommended_actions && (
            <div className="ai-actions">
              <strong>Actions:</strong> {details.recommended_actions}
            </div>
          )}
          {details.maintenance_timeline && (
            <div className="ai-timeline">
              <strong>Timeline:</strong> {details.maintenance_timeline}
            </div>
          )}
        </div>
      );
    }
    
    return Object.entries(details).map(([key, value]) => (
      <div key={key}>
        <strong>{key.replace(/_/g, ' ')}:</strong> {typeof value === 'number' ? value.toFixed(2) : value}
      </div>
    ));
  }
  
  return JSON.stringify(details).replace(/["{}]/g, ' ').trim();
}

export default function PredictionsBadge({ predictions }) {
  if (!predictions || predictions.length === 0) {
    return <div className="empty-copy">No active AI alerts.</div>;
  }

  // Sort predictions: AI analysis first, then by confidence
  const sortedPredictions = [...predictions].sort((a, b) => {
    if (a.prediction_type === 'ai_analysis') return -1;
    if (b.prediction_type === 'ai_analysis') return 1;
    return (b.confidence || 0) - (a.confidence || 0);
  });

  return (
    <div>
      {sortedPredictions.map((pred) => (
        <div key={pred.id} className={`prediction-badge severity-${pred.severity} ${pred.prediction_type === 'ai_analysis' ? 'ai-analysis-badge' : ''}`}>
          <div className="prediction-header">
            <span className="prediction-type">
              {pred.prediction_type === 'ai_analysis' ? '🤖 AI Analysis' : formatPredictionName(pred.prediction_type)}
            </span>
            <span className="prediction-conf">{(pred.confidence * 100).toFixed(0)}% conf</span>
          </div>
          {pred.details && (
            <div className="prediction-details">
              {formatDetails(pred.details)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
