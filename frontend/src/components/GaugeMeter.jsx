import React from 'react';
import './GaugeMeter.css';

function GaugeMeter({ value, max, unit, label, color = '#38bdf8', size = 120 }) {
  const percentage = Math.min((value / max) * 100, 100);
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  // Determine color based on percentage
  let gaugeColor = color;
  if (percentage > 80) gaugeColor = '#ef4444';
  else if (percentage > 60) gaugeColor = '#eab308';

  return (
    <div className="gauge-meter" style={{ width: size, height: size + 30 }}>
      <svg width={size} height={size} className="gauge-svg">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(148, 163, 184, 0.2)"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={gaugeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="gauge-progress"
        />
      </svg>
      <div className="gauge-content">
        <span className="gauge-value">{value !== undefined && value !== null ? value : '--'}</span>
        <span className="gauge-unit">{unit}</span>
      </div>
      <div className="gauge-label">{label}</div>
    </div>
  );
}

export default GaugeMeter;
