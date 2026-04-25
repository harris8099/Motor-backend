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
    if (details.comment) {
      // AI Comment from Gemini - display as expert commentary
      return (
        <div className="ai-comment">
          <div className="comment-text">
            {details.comment}
          </div>
          <div className="comment-meta">
            <small>💭 Expert Analysis • Based on {details.ml_predictions_count} ML predictions</small>
          </div>
        </div>
      );
    }
    
    if (details.health_assessment) {
      // Legacy AI Analysis (backward compatibility)
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
    
    // ML Prediction details
    return Object.entries(details).map(([key, value]) => {
      // Skip certain internal fields
      if (['analysis_type', 'ml_predictions_count'].includes(key)) return null;
      
      let displayValue = value;
      if (typeof value === 'number') {
        if (key.includes('rate') || key.includes('ratio')) {
          displayValue = (value * 100).toFixed(1) + '%';
        } else if (key.includes('time') && key.includes('minutes')) {
          displayValue = Math.round(value) + ' min';
        } else if (key.includes('temp') || key.includes('power') || key.includes('current') || key.includes('vibration')) {
          displayValue = value.toFixed(2);
        } else {
          displayValue = value.toFixed(3);
        }
      }
      
      return (
        <div key={key}>
          <strong>{key.replace(/_/g, ' ')}:</strong> {displayValue}
        </div>
      );
    }).filter(Boolean);
  }
  
  return JSON.stringify(details).replace(/["{}]/g, ' ').trim();
}

export default function PredictionsBadge({ predictions }) {
  if (!predictions || predictions.length === 0) {
    return <div className="empty-copy">No active AI alerts.</div>;
  }

  // Sort predictions: AI comment last, ML predictions by confidence
  const sortedPredictions = [...predictions].sort((a, b) => {
    if (a.prediction_type === 'ai_comment') return 1;  // AI comments last
    if (b.prediction_type === 'ai_comment') return -1;
    return (b.confidence || 0) - (a.confidence || 0);  // ML predictions by confidence
  });

  return (
    <div>
      {sortedPredictions.map((pred) => (
        <div key={pred.id} className={`prediction-badge severity-${pred.severity} ${pred.prediction_type === 'ai_comment' ? 'ai-comment-badge' : pred.prediction_type === 'ai_analysis' ? 'ai-analysis-badge' : ''}`}>
          <div className="prediction-header">
            <span className="prediction-type">
              {pred.prediction_type === 'ai_comment' ? '💭 AI Expert Commentary' : 
               pred.prediction_type === 'ai_analysis' ? '🤖 AI Analysis' : 
               formatPredictionName(pred.prediction_type)}
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
