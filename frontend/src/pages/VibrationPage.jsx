import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Wind, Activity, AlertTriangle, Move } from 'lucide-react';
import { fetchDeviceData } from '../api';
import MetricCard from '../components/MetricCard';
import LiveChart from '../components/LiveChart';
import Breadcrumbs from '../components/Breadcrumbs';
import LiveIndicator from '../components/LiveIndicator';
import SkeletonCard from '../components/SkeletonCard';
import './PageStyles.css';

function VibrationPage() {
  const { deviceId } = useParams();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError('');
        const dataRes = await fetchDeviceData(deviceId);
        setData(dataRes.data || []);
      } catch (err) {
        console.error('Failed to load vibration data', err);
        setError('Could not load vibration data. Please check API connection.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [deviceId]);

  const latest = data.length > 0 ? data[0] : null;

  // Calculate total acceleration vector
  const totalAccel = latest ? 
    Math.sqrt(latest.accel_x**2 + latest.accel_y**2 + latest.accel_z**2).toFixed(2) : 
    '--';

  // Determine vibration level
  const getVibrationLevel = (accel) => {
    if (!accel) return 'unknown';
    const magnitude = Math.sqrt(accel.accel_x**2 + accel.accel_y**2 + accel.accel_z**2);
    if (magnitude < 0.5) return 'low';
    if (magnitude < 1.5) return 'moderate';
    return 'high';
  };

  const vibrationLevel = latest ? getVibrationLevel(latest) : 'unknown';

  return (
    <div className="page-container">
      <Breadcrumbs />
      
      <header className="page-header">
        <div className="header-with-icon">
          <div className="header-icon-wrapper vibration">
            <Wind size={28} />
          </div>
          <div>
            <h1>Vibration</h1>
            <p className="page-subtitle">Accelerometer data and vibration analysis</p>
          </div>
        </div>
        <div className="header-meta">
          <LiveIndicator isLive={!loading && !error && !!latest} />
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}
      
      {/* Skeleton Loading State */}
      {loading && (
        <div className="skeleton-grid">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {latest && (
        <>
          {/* Acceleration Metrics */}
          <section className="metrics-section">
            <h2>Acceleration (g-force)</h2>
            <div className="metrics-grid">
              <MetricCard title="X Axis" value={latest.accel_x?.toFixed(2) ?? '--'} unit="g" icon={Move} delay="delay-1" />
              <MetricCard title="Y Axis" value={latest.accel_y?.toFixed(2) ?? '--'} unit="g" icon={Move} delay="delay-1" />
              <MetricCard title="Z Axis" value={latest.accel_z?.toFixed(2) ?? '--'} unit="g" icon={Move} delay="delay-2" />
              <MetricCard title="Total Magnitude" value={totalAccel} unit="g" icon={Activity} delay="delay-2" />
            </div>
          </section>

          {/* Vibration Status */}
          <section className="vibration-status-section">
            <h2>Vibration Status</h2>
            <div className="panel status-panel">
              <div className="status-row">
                <span className="status-label">Vibration Level:</span>
                <span className={`status-value vibration-${vibrationLevel}`}>
                  {vibrationLevel.toUpperCase()}
                </span>
              </div>
              <div className="status-row">
                <span className="status-label">Vibration Fault:</span>
                <span className={`status-value ${latest.fault_vibration ? 'fault' : 'ok'}`}>
                  {latest.fault_vibration ? 'ACTIVE' : 'OK'}
                </span>
              </div>
              {latest.fault_vibration && (
                <div className="fault-alert">
                  <AlertTriangle size={20} />
                  <span>Excessive vibration detected - check motor alignment and bearings</span>
                </div>
              )}
            </div>
          </section>

          {/* Vibration Visualization */}
          <section className="chart-section">
            <h2>Vibration History</h2>
            <div className="panel chart-panel">
              <LiveChart data={data} />
            </div>
          </section>

          {/* Acceleration Info */}
          <section className="info-section">
            <h2>About Vibration Monitoring</h2>
            <div className="panel info-panel">
              <p>
                Vibration analysis helps detect bearing faults, misalignment, and mechanical issues 
                before they cause catastrophic failure. Normal vibration levels are typically below 0.5g. 
                Levels above 1.5g indicate potential mechanical problems requiring inspection.
              </p>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export default VibrationPage;
