import React from 'react';

export default function MetricCard({ title, value, unit, icon: Icon, delay }) {
  return (
    <div className={`panel metric-card animate-fade-in ${delay}`}>
      <div className="metric-header">
        <span>{title}</span>
        {Icon && <Icon size={18} color="var(--accent-2)" />}
      </div>
      <div className="metric-value">
        {value} <span className="metric-unit">{unit}</span>
      </div>
    </div>
  );
}
