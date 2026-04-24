import React, { useState, useEffect } from 'react';
import { Activity, Zap, Thermometer, Clock } from 'lucide-react';
import { fetchDeviceData, fetchDeviceFaults, fetchDevicePredictions } from './api';
import MetricCard from './components/MetricCard';
import LiveChart from './components/LiveChart';
import FaultsList from './components/FaultsList';
import PredictionsBadge from './components/PredictionsBadge';
import './App.css';

function App() {
  const [deviceId, setDeviceId] = useState('DEVICE_001'); // default or get from input
  const [data, setData] = useState([]);
  const [faults, setFaults] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAllData() {
      try {
        setLoading(true);
        const [dataRes, faultsRes, predsRes] = await Promise.all([
          fetchDeviceData(deviceId),
          fetchDeviceFaults(deviceId),
          fetchDevicePredictions(deviceId)
        ]);
        setData(dataRes.data || []);
        setFaults(faultsRes.data || []);
        setPredictions(predsRes.data || []);
      } catch (err) {
        console.error("Failed to load data", err);
      } finally {
        setLoading(false);
      }
    }
    
    if (deviceId) {
      loadAllData();
      const interval = setInterval(loadAllData, 5000); // Poll every 5s
      return () => clearInterval(interval);
    }
  }, [deviceId]);

  const latest = data.length > 0 ? data[0] : null;

  return (
    <div className="dashboard-container">
      <header className="dashboard-header animate-fade-in">
        <h1>
          <Activity color="var(--accent-blue)" size={32} />
          Motor Intelligence
        </h1>
        <div className="header-controls">
          <input 
            value={deviceId} 
            onChange={(e) => setDeviceId(e.target.value)} 
            placeholder="Enter Device ID"
          />
        </div>
      </header>

      {loading && data.length === 0 ? (
        <div style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-muted)' }}>
          Loading telemetry...
        </div>
      ) : !latest ? (
        <div style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-muted)' }}>
          No data available for this device.
        </div>
      ) : (
        <>
          <div className="metrics-grid">
            <MetricCard 
              title="Current RPM" 
              value={latest.rpm} 
              unit="RPM" 
              icon={Activity} 
              delay="delay-1" 
            />
            <MetricCard 
              title="Power Consumption" 
              value={latest.power?.toFixed(1) || '0.0'} 
              unit="W" 
              icon={Zap} 
              delay="delay-2" 
            />
            <MetricCard 
              title="Average Temp" 
              value={((latest.temp1 + latest.temp2) / 2).toFixed(1)} 
              unit="°C" 
              icon={Thermometer} 
              delay="delay-3" 
            />
            <MetricCard 
              title="Uptime" 
              value={Math.floor(latest.uptime_seconds / 3600)} 
              unit="hrs" 
              icon={Clock} 
              delay="delay-3" 
            />
          </div>

          <div className="main-grid">
            <div className="glass-panel animate-fade-in delay-2">
              <h2 className="section-title">Telemetry History</h2>
              <LiveChart data={data} />
            </div>

            <div className="side-panel">
              <div className="glass-panel animate-fade-in delay-3">
                <h2 className="section-title">AI Predictions</h2>
                <PredictionsBadge predictions={predictions} />
              </div>

              <div className="glass-panel animate-fade-in delay-3">
                <h2 className="section-title">Recent Faults</h2>
                <FaultsList faults={faults} />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
