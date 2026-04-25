import React, { useState, useEffect } from 'react';
import { TrendingUp, IndianRupee, Zap, Calendar, Settings } from 'lucide-react';

export default function PowerForecast({ forecastData, electricityRate, onRateChange }) {
  const [localRate, setLocalRate] = useState(electricityRate || 8.0);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    if (electricityRate) {
      setLocalRate(electricityRate);
    }
  }, [electricityRate]);

  const handleRateChange = (e) => {
    const newRate = parseFloat(e.target.value) || 8.0;
    setLocalRate(newRate);
    if (onRateChange) {
      onRateChange(newRate);
    }
  };

  if (!forecastData || !forecastData.summary) {
    return (
      <div className="forecast-panel">
        <div className="forecast-header">
          <TrendingUp size={20} />
          <h3>Power & Cost Forecast</h3>
          <Settings size={16} className="settings-icon" />
        </div>
        <div className="forecast-empty">No forecast data available</div>
      </div>
    );
  }

  const { summary, forecast } = forecastData;
  const trend = summary.trend || 'stable';
  const trendIcon = trend === 'increasing' ? '↑' : trend === 'decreasing' ? '↓' : '→';
  const trendColor = trend === 'increasing' ? '#f5a99d' : trend === 'decreasing' ? '#2ed573' : '#8b95a5';

  return (
    <div className="forecast-panel">
      <div className="forecast-header" onClick={() => setShowSettings(!showSettings)}>
        <TrendingUp size={20} />
        <h3>Power & Cost Forecast</h3>
        <Settings size={16} className="settings-icon" />
      </div>

      {showSettings && (
        <div className="rate-settings">
          <label>
            <IndianRupee size={14} />
            Electricity Rate (₹/kWh)
          </label>
          <input
            type="number"
            step="0.1"
            min="0"
            value={localRate}
            onChange={handleRateChange}
            placeholder="8.0"
          />
        </div>
      )}

      <div className="forecast-summary">
        <div className="forecast-stat">
          <span className="stat-label">Avg Power</span>
          <span className="stat-value">{summary.avg_power || 0} W</span>
        </div>
        <div className="forecast-stat">
          <span className="stat-label">Trend</span>
          <span className="stat-value" style={{ color: trendColor }}>
            {trendIcon} {trend}
          </span>
        </div>
      </div>

      <div className="cost-projections">
        <h4>Cost Projections</h4>
        <div className="cost-grid">
          <div className="cost-card">
            <Calendar size={16} />
            <span className="cost-period">Hourly</span>
            <span className="cost-value">₹{summary.projected_hourly_cost?.toFixed(2) || 0}</span>
          </div>
          <div className="cost-card">
            <Calendar size={16} />
            <span className="cost-period">Daily</span>
            <span className="cost-value">₹{summary.projected_daily_cost?.toFixed(0) || 0}</span>
          </div>
          <div className="cost-card highlight">
            <Calendar size={16} />
            <span className="cost-period">Monthly</span>
            <span className="cost-value">₹{summary.projected_monthly_cost?.toFixed(0) || 0}</span>
          </div>
        </div>
      </div>

      {forecast && forecast.cost && forecast.cost.length > 0 && (
        <div className="forecast-chart">
          <h4>24-Hour Cost Forecast</h4>
          <div className="mini-chart">
            {forecast.cost.slice(0, 12).map((cost, idx) => (
              <div key={idx} className="chart-bar-container">
                <div 
                  className="chart-bar" 
                  style={{ 
                    height: `${Math.min((cost / Math.max(...forecast.cost)) * 100, 100)}%`,
                    backgroundColor: cost > (summary.projected_hourly_cost || 0) ? '#f5a99d' : '#54a0ff'
                  }}
                />
                <span className="bar-label">{(idx + 1) * 2}h</span>
              </div>
            ))}
          </div>
          <div className="chart-legend">
            <span className="legend-item">
              <span className="legend-dot" style={{ background: '#54a0ff' }}></span>
              Under average
            </span>
            <span className="legend-item">
              <span className="legend-dot" style={{ background: '#f5a99d' }}></span>
              Over average
            </span>
          </div>
        </div>
      )}

      <div className="rate-info">
        <IndianRupee size={14} />
        <span>Rate: ₹{localRate.toFixed(1)}/kWh</span>
      </div>
    </div>
  );
}