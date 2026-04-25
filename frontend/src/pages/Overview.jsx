import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Gauge, Zap, Thermometer, Clock, Activity, Brain, AlertTriangle, RefreshCw, TrendingUp } from 'lucide-react';
import { fetchDeviceData, fetchDevicePredictions, fetchDeviceFaults } from '../api';
import MetricCard from '../components/MetricCard';
import PredictionsBadge from '../components/PredictionsBadge';
import LiveChart from '../components/LiveChart';
import Breadcrumbs from '../components/Breadcrumbs';
import LiveIndicator from '../components/LiveIndicator';
import GaugeMeter from '../components/GaugeMeter';
import SkeletonCard from '../components/SkeletonCard';
import './PageStyles.css';

function Overview() {
  const { deviceId } = useParams();
  const [data, setData] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [faults, setFaults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError('');
        const [dataRes, predsRes, faultsRes] = await Promise.all([
          fetchDeviceData(deviceId),
          fetchDevicePredictions(deviceId),
          fetchDeviceFaults(deviceId),
        ]);
        setData(dataRes.data || []);
        setPredictions(predsRes.data || []);
        setFaults(faultsRes.data || []);
        setLastUpdated(new Date());
      } catch (err) {
        console.error('Failed to load data', err);
        setError('Could not load telemetry. Please check API connection.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [deviceId]);

  const latest = data.length > 0 ? data[0] : null;
  const uptimeHours = latest ? Math.floor(latest.uptime_seconds / 3600) : 0;
  const averageTemp = latest ? ((latest.temp1 + latest.temp2) / 2).toFixed(1) : '0.0';
  
  // Calculate max values for gauges (can be adjusted based on device specs)
  const maxRPM = 3000;
  const maxPower = 2000;
  const maxTemp = 100;

  const refreshData = () => {
    window.location.reload();
  };

  return (
    <div className="page-container">
      <Breadcrumbs />
      
      <header className="page-header">
        <div className="header-with-icon">
          <div className="header-icon-wrapper overview">
            <Activity size={28} />
          </div>
          <div>
            <h1>Overview</h1>
            <p className="page-subtitle">Real-time device status and key metrics</p>
          </div>
        </div>
        <div className="header-meta">
          <LiveIndicator isLive={!!latest} />
          <span className="last-updated">
            {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Waiting...'}
          </span>
          <button className="refresh-btn" onClick={refreshData} title="Refresh">
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}
      
      {/* Skeleton Loading State */}
      {!latest && loading && (
        <div className="skeleton-grid">
          {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {latest && (
        <>
          {/* Quick Stats Gauges */}
          <section className="gauges-section">
            <div className="gauges-grid">
              <div className="gauge-card">
                <GaugeMeter 
                  value={latest.rpm || 0} 
                  max={maxRPM} 
                  unit="RPM" 
                  label="Motor Speed" 
                  color="#38bdf8"
                  size={140}
                />
                <div className="gauge-details">
                  <span className={`status-pill ${latest.motor_running ? 'running' : 'stopped'}`}>
                    {latest.motor_running ? 'RUNNING' : 'STOPPED'}
                  </span>
                </div>
              </div>
              
              <div className="gauge-card">
                <GaugeMeter 
                  value={latest.power?.toFixed(0) || 0} 
                  max={maxPower} 
                  unit="W" 
                  label="Power" 
                  color="#f59e0b"
                  size={140}
                />
                <div className="gauge-details">
                  <span className="gauge-detail-value">{latest.voltage?.toFixed(1)}V</span>
                  <span className="gauge-detail-separator">|</span>
                  <span className="gauge-detail-value">{latest.current?.toFixed(2)}A</span>
                </div>
              </div>
              
              <div className="gauge-card">
                <GaugeMeter 
                  value={averageTemp} 
                  max={maxTemp} 
                  unit="°C" 
                  label="Temperature" 
                  color="#ef4444"
                  size={140}
                />
                <div className="gauge-details">
                  <span className={`status-pill ${parseFloat(averageTemp) > 80 ? 'warning' : 'normal'}`}>
                    {parseFloat(averageTemp) > 80 ? 'HIGH' : 'NORMAL'}
                  </span>
                </div>
              </div>
              
              <div className="gauge-card uptime-card">
                <div className="uptime-display">
                  <Clock size={48} className="uptime-icon" />
                  <div className="uptime-value">{uptimeHours}</div>
                  <div className="uptime-label">Hours Uptime</div>
                </div>
              </div>
            </div>
          </section>

          {/* Key Metrics Grid */}
          <section className="metrics-section">
            <h2>Quick Stats</h2>
            <div className="metrics-grid compact">
              <MetricCard title="Voltage" value={latest.voltage?.toFixed(1) ?? '--'} unit="V" icon={Zap} delay="delay-1" />
              <MetricCard title="Current" value={latest.current?.toFixed(2) ?? '--'} unit="A" icon={Activity} delay="delay-1" />
              <MetricCard title="Power Factor" value={latest.power_factor?.toFixed(2) ?? '--'} unit="" icon={TrendingUp} delay="delay-2" />
              <MetricCard title="Frequency" value={latest.frequency?.toFixed(1) ?? '--'} unit="Hz" icon={Zap} delay="delay-2" />
              <MetricCard title="Pulse Count" value={latest.pulse ?? '--'} unit="" icon={Activity} delay="delay-3" />
              <MetricCard 
                title="Active Faults" 
                value={latest.fault_overcurrent || latest.fault_overtemp || latest.fault_stall || latest.fault_vibration ? 'YES' : 'NO'} 
                unit="" 
                icon={AlertTriangle} 
                delay="delay-3"
                isFault={latest.fault_overcurrent || latest.fault_overtemp || latest.fault_stall || latest.fault_vibration}
              />
            </div>
          </section>

          {/* AI Insights Summary */}
          <section className="ai-summary-section">
            <div className="section-header-with-icon">
              <Brain size={24} />
              <h2>AI Insights</h2>
            </div>
            <div className="panel">
              {predictions.length > 0 ? (
                <div className="predictions-preview">
                  {predictions.slice(0, 3).map((pred, idx) => (
                    <div key={idx} className={`prediction-pill severity-${pred.severity}`}>
                      <span className="pred-type">{pred.prediction_type?.replace('_', ' ')}</span>
                      <span className="pred-confidence">{Math.round(pred.confidence * 100)}% confidence</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="status-ok-message">
                  <span className="status-dot"></span>
                  All systems normal - no predictions at this time
                </div>
              )}
            </div>
          </section>

          {/* Live Chart */}
          <section className="chart-section">
            <h2>Telemetry History</h2>
            <div className="panel chart-panel">
              <LiveChart data={data} />
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export default Overview;
