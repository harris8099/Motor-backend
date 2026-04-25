import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Zap, Battery, Plug, Gauge, BatteryCharging, IndianRupee } from 'lucide-react';
import { fetchDeviceData, fetchPowerForecast } from '../api';
import MetricCard from '../components/MetricCard';
import PowerForecast from '../components/PowerForecast';
import LiveChart from '../components/LiveChart';
import Breadcrumbs from '../components/Breadcrumbs';
import LiveIndicator from '../components/LiveIndicator';
import SkeletonCard from '../components/SkeletonCard';
import './PageStyles.css';

function PowerPage() {
  const { deviceId } = useParams();
  const [data, setData] = useState([]);
  const [forecastData, setForecastData] = useState(null);
  const [electricityRate, setElectricityRate] = useState(8.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError('');
        const [dataRes, forecastRes] = await Promise.all([
          fetchDeviceData(deviceId),
          fetchPowerForecast(deviceId, electricityRate, 24),
        ]);
        setData(dataRes.data || []);
        setForecastData(forecastRes);
      } catch (err) {
        console.error('Failed to load power data', err);
        setError('Could not load power data. Please check API connection.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [deviceId, electricityRate]);

  const latest = data.length > 0 ? data[0] : null;

  return (
    <div className="page-container">
      <Breadcrumbs />
      
      <header className="page-header">
        <div className="header-with-icon">
          <div className="header-icon-wrapper power">
            <Zap size={28} />
          </div>
          <div>
            <h1>Power & Energy</h1>
            <p className="page-subtitle">Electrical parameters and consumption analysis</p>
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
          {/* Power Metrics */}
          <section className="metrics-section">
            <h2>Electrical Parameters</h2>
            <div className="metrics-grid">
              <MetricCard title="Voltage" value={latest.voltage?.toFixed(1) ?? '--'} unit="V" icon={Zap} delay="delay-1" />
              <MetricCard title="Current" value={latest.current?.toFixed(2) ?? '--'} unit="A" icon={Battery} delay="delay-1" />
              <MetricCard title="Power" value={latest.power?.toFixed(1) ?? '--'} unit="W" icon={Plug} delay="delay-2" />
              <MetricCard title="Power Factor" value={latest.power_factor?.toFixed(2) ?? '--'} unit="" icon={Gauge} delay="delay-2" />
              <MetricCard title="Energy" value={latest.energy?.toFixed(2) ?? '--'} unit="kWh" icon={BatteryCharging} delay="delay-3" />
              <MetricCard title="Frequency" value={latest.frequency?.toFixed(1) ?? '--'} unit="Hz" icon={Zap} delay="delay-3" />
            </div>
          </section>

          {/* Power History Chart */}
          <section className="chart-section">
            <h2>Power History</h2>
            <div className="panel chart-panel">
              <LiveChart data={data} />
            </div>
          </section>

          {/* Power Forecast */}
          <section className="forecast-section">
            <PowerForecast 
              forecastData={forecastData} 
              electricityRate={electricityRate}
              onRateChange={setElectricityRate}
            />
          </section>
        </>
      )}
    </div>
  );
}

export default PowerPage;
