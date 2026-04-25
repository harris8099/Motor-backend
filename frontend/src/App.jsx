import React, { useState, useEffect } from 'react';
import { Activity, Zap, Thermometer, Clock, Cpu, RefreshCw } from 'lucide-react';
import { fetchDeviceData, fetchDeviceFaults, fetchDevicePredictions } from './api';
import MetricCard from './components/MetricCard';
import LiveChart from './components/LiveChart';
import FaultsList from './components/FaultsList';
import PredictionsBadge from './components/PredictionsBadge';
import './App.css';

function App() {
  const [deviceId, setDeviceId] = useState('DEVICE_001');
  const [data, setData] = useState([]);
  const [faults, setFaults] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    async function loadAllData() {
      try {
        setLoading(true);
        setError('');
        const [dataRes, faultsRes, predsRes] = await Promise.all([
          fetchDeviceData(deviceId),
          fetchDeviceFaults(deviceId),
          fetchDevicePredictions(deviceId),
        ]);
        setData(dataRes.data || []);
        setFaults(faultsRes.data || []);
        setPredictions(predsRes.data || []);
        setLastUpdated(new Date());
      } catch (err) {
        console.error('Failed to load data', err);
        setError('Could not load telemetry. Please check API URL or device ID.');
      } finally {
        setLoading(false);
      }
    }

    if (deviceId) {
      loadAllData();
      const interval = setInterval(loadAllData, 5000);
      return () => clearInterval(interval);
    }

    return undefined;
  }, [deviceId, refreshTrigger]);

  const latest = data.length > 0 ? data[0] : null;
  const averageTemp = latest ? ((latest.temp1 + latest.temp2) / 2).toFixed(1) : '0.0';
  const uptimeHours = latest ? Math.floor(latest.uptime_seconds / 3600) : 0;

  return (
    <div className="app-shell">
      <div className="background-grid" />
      <main className="dashboard-container">
        <header className="dashboard-header animate-fade-in">
          <div>
            <p className="kicker">Smart Motor Command Center</p>
            <h1>
              <Activity size={30} />
              Live Operations Dashboard
            </h1>
            <p className="subtitle">Realtime device health, AI warnings, and performance trends</p>
          </div>
          <div className="header-controls">
            <label htmlFor="device-id">Device ID</label>
            <div className="input-row">
              <Cpu size={16} />
              <input
                id="device-id"
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                placeholder="Enter Device ID"
              />
              <button className="refresh-button" type="button" onClick={() => setRefreshTrigger(prev => prev + 1)}>
                <RefreshCw size={14} />
                Refresh
              </button>
            </div>
            <p className="last-updated">
              {lastUpdated && lastUpdated.getTime() > 0
                ? `Last sync: ${lastUpdated.toLocaleTimeString()}`
                : 'Waiting for sync...'}
            </p>
          </div>
        </header>

        {error && <div className="status-banner error">{error}</div>}
        {!latest && loading ? <div className="status-banner">Loading telemetry...</div> : null}
        {!latest && !loading && !error ? (
          <div className="status-banner">No data available for this device yet.</div>
        ) : null}

        <section className="metrics-grid">
          <MetricCard title="Current RPM" value={latest?.rpm ?? '--'} unit="RPM" icon={Activity} delay="delay-1" />
          <MetricCard
            title="Power Consumption"
            value={latest?.power?.toFixed(1) ?? '0.0'}
            unit="W"
            icon={Zap}
            delay="delay-2"
          />
          <MetricCard title="Average Temp" value={averageTemp} unit="deg C" icon={Thermometer} delay="delay-3" />
          <MetricCard title="Uptime" value={uptimeHours} unit="hrs" icon={Clock} delay="delay-3" />
        </section>

        <section className="main-grid">
          <div className="panel chart-panel animate-fade-in delay-2">
            <h2 className="section-title">Telemetry History</h2>
            {latest ? <LiveChart data={data} /> : <div className="empty-copy">No chart data yet.</div>}
          </div>

          <div className="side-panel">
            <div className="panel animate-fade-in delay-3">
              <h2 className="section-title">AI Predictions</h2>
              <PredictionsBadge predictions={predictions} />
            </div>

            <div className="panel animate-fade-in delay-3">
              <h2 className="section-title">Recent Faults</h2>
              <FaultsList faults={faults} />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
