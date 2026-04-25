import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Settings, Zap, Thermometer, Gauge, Timer, Save } from 'lucide-react';
import { fetchDeviceData } from '../api';
import MetricCard from '../components/MetricCard';
import Breadcrumbs from '../components/Breadcrumbs';
import LiveIndicator from '../components/LiveIndicator';
import SkeletonCard from '../components/SkeletonCard';
import './PageStyles.css';

function SettingsPage() {
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
        console.error('Failed to load settings data', err);
        setError('Could not load settings. Please check API connection.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [deviceId]);

  const latest = data.length > 0 ? data[0] : null;

  return (
    <div className="page-container">
      <Breadcrumbs />
      
      <header className="page-header">
        <div className="header-with-icon">
          <div className="header-icon-wrapper settings">
            <Settings size={28} />
          </div>
          <div>
            <h1>Protection Settings</h1>
            <p className="page-subtitle">Current protection thresholds and limits</p>
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
          {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {latest && (
        <>
          {/* Current Limits Display */}
          <section className="metrics-section">
            <h2>Current Protection Limits</h2>
            <div className="metrics-grid">
              <MetricCard title="Max Current" value={latest.prot_max_current?.toFixed(1) ?? '--'} unit="A" icon={Zap} delay="delay-1" />
              <MetricCard title="Max Temperature" value={latest.prot_max_temp?.toFixed(1) ?? '--'} unit="°C" icon={Thermometer} delay="delay-1" />
              <MetricCard title="Min RPM" value={latest.prot_min_rpm ?? '--'} unit="" icon={Gauge} delay="delay-2" />
              <MetricCard title="Over Voltage" value={latest.prot_overvoltage_v?.toFixed(1) ?? '--'} unit="V" icon={Zap} delay="delay-2" />
              <MetricCard title="Under Voltage" value={latest.prot_undervoltage_v?.toFixed(1) ?? '--'} unit="V" icon={Zap} delay="delay-3" />
              <MetricCard title="Stall Current" value={latest.prot_stall_current_a?.toFixed(1) ?? '--'} unit="A" icon={Zap} delay="delay-3" />
            </div>
          </section>

          {/* Additional Settings */}
          <section className="settings-section">
            <h2>Timing & Counts</h2>
            <div className="metrics-grid compact">
              <MetricCard title="Startup Grace" value={latest.prot_startup_grace_ms ?? '--'} unit="ms" icon={Timer} delay="delay-1" />
              <MetricCard title="Fault Trip Count" value={latest.prot_fault_trip_count ?? '--'} unit="" icon={Settings} delay="delay-2" />
            </div>
          </section>

          {/* Settings Info */}
          <section className="info-section">
            <h2>About Protection Settings</h2>
            <div className="panel info-panel">
              <div className="settings-info-grid">
                <div className="setting-info-item">
                  <h4>Max Current</h4>
                  <p>Maximum allowed current before overcurrent protection triggers</p>
                </div>
                <div className="setting-info-item">
                  <h4>Max Temperature</h4>
                  <p>Temperature threshold for overtemperature protection</p>
                </div>
                <div className="setting-info-item">
                  <h4>Min RPM</h4>
                  <p>Minimum RPM threshold to detect stall conditions</p>
                </div>
                <div className="setting-info-item">
                  <h4>Over/Under Voltage</h4>
                  <p>Voltage limits for protection against power supply issues</p>
                </div>
                <div className="setting-info-item">
                  <h4>Stall Current</h4>
                  <p>Current threshold used to detect motor stall</p>
                </div>
                <div className="setting-info-item">
                  <h4>Startup Grace</h4>
                  <p>Time delay before protection checks begin after motor start</p>
                </div>
              </div>
            </div>
          </section>

          {/* Note about changing settings */}
          <section className="note-section">
            <div className="panel note-panel">
              <Settings size={20} />
              <p>
                <strong>Note:</strong> Protection settings are configured on the device firmware. 
                Changes must be made through the device configuration interface or API.
              </p>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export default SettingsPage;
