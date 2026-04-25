import React from 'react';

export default function MetricCard({ title, value, unit, icon: Icon, delay, isFault }) {
  return (
    <div className={`panel metric-card animate-fade-in ${delay} ${isFault ? 'metric-fault' : ''}`}>
      <div className="metric-header">
        <span>{title}</span>
        {Icon && <Icon size={18} color={isFault ? '#f5a99d' : 'var(--accent-2)'} />}
      </div>
      <div className="metric-value" style={isFault ? { color: '#f5a99d' } : {}}>
        {value} <span className="metric-unit">{unit}</span>
      </div>
    </div>
  );
}
