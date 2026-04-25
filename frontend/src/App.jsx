import React, { useState, useEffect } from 'react';
import { Activity, Zap, Thermometer, Clock, Cpu, RefreshCw, Gauge, Flame, Wind, AlertTriangle, Settings, Timer, Battery, GaugeCircle, ThermometerSun, Plug, Radio, ChevronDown, ChevronRight, Brain, TrendingUp, Wrench, Shield } from 'lucide-react';
import { fetchDeviceData, fetchDeviceFaults, fetchDevicePredictions, fetchPowerForecast } from './api';
import MetricCard from './components/MetricCard';
import LiveChart from './components/LiveChart';
import FaultsList from './components/FaultsList';
import PredictionsBadge from './components/PredictionsBadge';
import PowerForecast from './components/PowerForecast';
import './App.css';

function App() {
  const [deviceId, setDeviceId] = useState('DEVICE_001');
  const [data, setData] = useState([]);
  const [faults, setFaults] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [forecastData, setForecastData] = useState(null);
  const [electricityRate, setElectricityRate] = useState(0.12);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [expandedSections, setExpandedSections] = useState({
    motor: true,
    power: true,
    temp: false,
    faults: true,
    protection: false,
    ai: true,
    forecast: true
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  useEffect(() => {
    async function loadAllData() {
      try {
        setLoading(true);
        setError('');
        const [dataRes, faultsRes, predsRes, forecastRes] = await Promise.all([
          fetchDeviceData(deviceId),
          fetchDeviceFaults(deviceId),
          fetchDevicePredictions(deviceId),
          fetchPowerForecast(deviceId, electricityRate, 24),
        ]);
        setData(dataRes.data || []);
        setFaults(faultsRes.data || []);
        setPredictions(predsRes.data || []);
        setForecastData(forecastRes);
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
  }, [deviceId, refreshTrigger, electricityRate]);

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

        {/* AI Predictions - Featured Section */}
        <section className="ai-predictions-section">
          <div className="panel ai-hero" onClick={() => toggleSection('ai')}>
            <div className="ai-hero-content">
              <div className="ai-icon">
                <Brain size={32} />
              </div>
              <div className="ai-hero-text">
                <h2><Brain size={20} /> AI-Powered Predictive Maintenance</h2>
                <p>Our machine learning models analyze real-time sensor data to predict failures before they happen</p>
              </div>
              <div className="ai-badges">
                {predictions.length > 0 ? (
                  predictions.slice(0, 3).map((pred, idx) => (
                    <span key={idx} className={`ai-badge severity-${pred.severity}`}>
                      {pred.prediction_type?.replace('_', ' ')} • {Math.round(pred.confidence * 100)}%
                    </span>
                  ))
                ) : (
                  <span className="ai-badge status-ok">All systems normal</span>
                )}
              </div>
            </div>
            {expandedSections.ai ? <ChevronDown size={24} /> : <ChevronRight size={24} />}
          </div>
          
          {expandedSections.ai && (
            <div className="ai-details-grid">
              <div className="panel ai-model-card">
                <div className="ai-model-header">
                  <TrendingUp size={20} />
                  <h3>Overheating Prediction</h3>
                </div>
                <p className="ai-model-desc">Analyzes temperature trends to predict thermal runaway before it occurs</p>
                <div className="ai-model-status">
                  <span className="status-dot active"></span>
                  Active Monitoring
                </div>
              </div>
              <div className="panel ai-model-card">
                <div className="ai-model-header">
                  <AlertTriangle size={20} />
                  <h3>Stall Risk Detection</h3>
                </div>
                <p className="ai-model-desc">Monitors current and RPM to detect stall conditions early</p>
                <div className="ai-model-status">
                  <span className="status-dot active"></span>
                  Active Monitoring
                </div>
              </div>
              <div className="panel ai-model-card">
                <div className="ai-model-header">
                  <Wind size={20} />
                  <h3>Bearing Fault Detection</h3>
                </div>
                <p className="ai-model-desc">Uses vibration analysis to identify bearing degradation patterns</p>
                <div className="ai-model-status">
                  <span className="status-dot active"></span>
                  Active Monitoring
                </div>
              </div>
              <div className="panel ai-model-card">
                <div className="ai-model-header">
                  <Wrench size={20} />
                  <h3>Maintenance Forecasting</h3>
                </div>
                <p className="ai-model-desc">Predicts optimal maintenance windows based on usage patterns</p>
                <div className="ai-model-status">
                  <span className="status-dot active"></span>
                  Active Monitoring
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Collapsible Sections */}
        
        {/* Motor Status Section */}
        <div className="collapsible-section">
          <div className="section-header" onClick={() => toggleSection('motor')}>
            <Gauge size={20} />
            <h3>Motor Status</h3>
            {expandedSections.motor ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </div>
          {expandedSections.motor && (
            <section className="metrics-grid">
              <MetricCard title="Motor Running" value={latest?.motor_running ? 'ON' : 'OFF'} unit="" icon={Gauge} delay="delay-1" />
              <MetricCard title="Current RPM" value={latest?.rpm ?? '--'} unit="RPM" icon={Activity} delay="delay-1" />
              <MetricCard title="Pulse Count" value={latest?.pulse ?? '--'} unit="" icon={GaugeCircle} delay="delay-2" />
              <MetricCard title="Uptime" value={uptimeHours} unit="hrs" icon={Clock} delay="delay-3" />
            </section>
          )}
        </div>

        {/* Power Section */}
        <div className="collapsible-section">
          <div className="section-header" onClick={() => toggleSection('power')}>
            <Zap size={20} />
            <h3>Power & Energy</h3>
            {expandedSections.power ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </div>
          {expandedSections.power && (
            <section className="metrics-grid">
              <MetricCard title="Voltage" value={latest?.voltage?.toFixed(1) ?? '--'} unit="V" icon={Zap} delay="delay-1" />
              <MetricCard title="Current" value={latest?.current?.toFixed(2) ?? '--'} unit="A" icon={Battery} delay="delay-1" />
              <MetricCard title="Power" value={latest?.power?.toFixed(1) ?? '--'} unit="W" icon={Plug} delay="delay-2" />
              <MetricCard title="Power Factor" value={latest?.power_factor?.toFixed(2) ?? '--'} unit="PF" icon={Gauge} delay="delay-2" />
              <MetricCard title="Energy" value={latest?.energy?.toFixed(2) ?? '--'} unit="kWh" icon={Battery} delay="delay-3" />
              <MetricCard title="Frequency" value={latest?.frequency?.toFixed(1) ?? '--'} unit="Hz" icon={GaugeCircle} delay="delay-3" />
            </section>
          )}
        </div>

        {/* Temperature & Vibration Section */}
        <div className="collapsible-section">
          <div className="section-header" onClick={() => toggleSection('temp')}>
            <Thermometer size={20} />
            <h3>Temperature & Vibration</h3>
            {expandedSections.temp ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </div>
          {expandedSections.temp && (
            <section className="metrics-grid">
              <MetricCard title="Temperature 1" value={latest?.temp1?.toFixed(1) ?? '--'} unit="°C" icon={Thermometer} delay="delay-1" />
              <MetricCard title="Temperature 2" value={latest?.temp2?.toFixed(1) ?? '--'} unit="°C" icon={ThermometerSun} delay="delay-1" />
              <MetricCard title="Avg Temp" value={averageTemp} unit="°C" icon={Flame} delay="delay-2" />
              <MetricCard title="Accel X" value={latest?.accel_x?.toFixed(2) ?? '--'} unit="g" icon={Wind} delay="delay-2" />
              <MetricCard title="Accel Y" value={latest?.accel_y?.toFixed(2) ?? '--'} unit="g" icon={Wind} delay="delay-3" />
              <MetricCard title="Accel Z" value={latest?.accel_z?.toFixed(2) ?? '--'} unit="g" icon={Wind} delay="delay-3" />
            </section>
          )}
        </div>

        {/* Faults Section */}
        <div className="collapsible-section">
          <div className="section-header" onClick={() => toggleSection('faults')}>
            <AlertTriangle size={20} />
            <h3>Fault Status</h3>
            {expandedSections.faults ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </div>
          {expandedSections.faults && (
            <section className="metrics-grid faults-grid">
              <MetricCard title="Over Current" value={latest?.fault_overcurrent ? 'FAULT' : 'OK'} unit="" icon={AlertTriangle} delay="delay-1" isFault={latest?.fault_overcurrent} />
              <MetricCard title="Over Temp" value={latest?.fault_overtemp ? 'FAULT' : 'OK'} unit="" icon={Flame} delay="delay-1" isFault={latest?.fault_overtemp} />
              <MetricCard title="Stall" value={latest?.fault_stall ? 'FAULT' : 'OK'} unit="" icon={AlertTriangle} delay="delay-2" isFault={latest?.fault_stall} />
              <MetricCard title="Vibration" value={latest?.fault_vibration ? 'FAULT' : 'OK'} unit="" icon={Wind} delay="delay-2" isFault={latest?.fault_vibration} />
              <MetricCard title="Over Voltage" value={latest?.fault_overvoltage ? 'FAULT' : 'OK'} unit="" icon={Zap} delay="delay-3" isFault={latest?.fault_overvoltage} />
              <MetricCard title="Under Voltage" value={latest?.fault_undervoltage ? 'FAULT' : 'OK'} unit="" icon={Zap} delay="delay-3" isFault={latest?.fault_undervoltage} />
            </section>
          )}
        </div>

        {/* Protection Settings Section */}
        <div className="collapsible-section">
          <div className="section-header" onClick={() => toggleSection('protection')}>
            <Settings size={20} />
            <h3>Protection Settings</h3>
            {expandedSections.protection ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </div>
          {expandedSections.protection && (
            <section className="metrics-grid">
              <MetricCard title="Max Current" value={latest?.prot_max_current?.toFixed(1) ?? '--'} unit="A" icon={Settings} delay="delay-1" />
              <MetricCard title="Max Temp" value={latest?.prot_max_temp?.toFixed(1) ?? '--'} unit="°C" icon={Thermometer} delay="delay-1" />
              <MetricCard title="Min RPM" value={latest?.prot_min_rpm ?? '--'} unit="" icon={Gauge} delay="delay-2" />
              <MetricCard title="Over Voltage" value={latest?.prot_overvoltage_v?.toFixed(1) ?? '--'} unit="V" icon={Zap} delay="delay-2" />
              <MetricCard title="Under Voltage" value={latest?.prot_undervoltage_v?.toFixed(1) ?? '--'} unit="V" icon={Zap} delay="delay-3" />
              <MetricCard title="Stall Current" value={latest?.prot_stall_current_a?.toFixed(1) ?? '--'} unit="A" icon={AlertTriangle} delay="delay-3" />
              <MetricCard title="Startup Grace" value={latest?.prot_startup_grace_ms ?? '--'} unit="ms" icon={Timer} delay="delay-3" />
              <MetricCard title="Fault Trip Count" value={latest?.prot_fault_trip_count ?? '--'} unit="" icon={AlertTriangle} delay="delay-3" />
            </section>
          )}
        </div>

        {/* Power Forecast Section */}
        <div className="collapsible-section">
          <div className="section-header" onClick={() => toggleSection('forecast')}>
            <TrendingUp size={20} />
            <h3>Power & Cost Forecast</h3>
            {expandedSections.forecast ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </div>
          {expandedSections.forecast && (
            <PowerForecast 
              forecastData={forecastData} 
              electricityRate={electricityRate}
              onRateChange={setElectricityRate}
            />
          )}
        </div>

        {/* Chart and Side Panels */}
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
