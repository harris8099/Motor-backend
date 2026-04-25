import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Thermometer, ThermometerSun, Flame, TrendingUp } from 'lucide-react';
import { fetchDeviceData } from '../api';
import MetricCard from '../components/MetricCard';
import LiveChart from '../components/LiveChart';
import Breadcrumbs from '../components/Breadcrumbs';
import LiveIndicator from '../components/LiveIndicator';
import SkeletonCard from '../components/SkeletonCard';
import './PageStyles.css';

function TemperaturePage() {
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
        console.error('Failed to load temperature data', err);
        setError('Could not load temperature data. Please check API connection.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [deviceId]);

  const latest = data.length > 0 ? data[0] : null;
  const averageTemp = latest ? ((latest.temp1 + latest.temp2) / 2).toFixed(1) : '0.0';
  const tempDiff = latest ? (latest.temp1 - latest.temp2).toFixed(1) : '0.0';

  // Calculate temperature trend
  const getTempTrend = () => {
    if (data.length < 5) return 'stable';
    const recent = data.slice(0, 5);
    const avgRecent = recent.reduce((sum, d) => sum + (d.temp1 + d.temp2) / 2, 0) / recent.length;
    const avgOlder = data.slice(5, 10).reduce((sum, d) => sum + (d.temp1 + d.temp2) / 2, 0) / Math.min(5, data.length - 5);
    if (avgRecent > avgOlder + 2) return 'rising';
    if (avgRecent < avgOlder - 2) return 'falling';
    return 'stable';
  };

  const trend = getTempTrend();

  return (
    <div className="page-container">
      <Breadcrumbs />
      
      <header className="page-header">
        <div className="header-with-icon">
          <div className="header-icon-wrapper temperature">
            <Thermometer size={28} />
          </div>
          <div>
            <h1>Temperature</h1>
            <p className="page-subtitle">Thermal monitoring and analysis</p>
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
          {/* Temperature Metrics */}
          <section className="metrics-section">
            <h2>Current Temperatures</h2>
            <div className="metrics-grid">
              <MetricCard title="Temperature 1" value={latest.temp1?.toFixed(1) ?? '--'} unit="°C" icon={Thermometer} delay="delay-1" />
              <MetricCard title="Temperature 2" value={latest.temp2?.toFixed(1) ?? '--'} unit="°C" icon={ThermometerSun} delay="delay-1" />
              <MetricCard title="Average" value={averageTemp} unit="°C" icon={Flame} delay="delay-2" />
              <MetricCard 
                title="Difference" 
                value={Math.abs(tempDiff)} 
                unit={`°C ${parseFloat(tempDiff) > 0 ? '(T1 > T2)' : '(T2 > T1)'}`} 
                icon={TrendingUp} 
                delay="delay-2" 
              />
            </div>
          </section>

          {/* Temperature Status */}
          <section className="temp-status-section">
            <h2>Temperature Status</h2>
            <div className="panel status-panel">
              <div className="status-row">
                <span className="status-label">Over Temperature Fault:</span>
                <span className={`status-value ${latest.fault_overtemp ? 'fault' : 'ok'}`}>
                  {latest.fault_overtemp ? 'ACTIVE' : 'OK'}
                </span>
              </div>
              <div className="status-row">
                <span className="status-label">Max Temperature Limit:</span>
                <span className="status-value">{latest.prot_max_temp?.toFixed(1) ?? '--'} °C</span>
              </div>
              <div className="status-row">
                <span className="status-label">Temperature Trend:</span>
                <span className={`status-value trend-${trend}`}>
                  {trend === 'rising' ? 'RISING ↑' : trend === 'falling' ? 'FALLING ↓' : 'STABLE →'}
                </span>
              </div>
            </div>
          </section>

          {/* Temperature History */}
          <section className="chart-section">
            <h2>Temperature History</h2>
            <div className="panel chart-panel">
              <LiveChart data={data} />
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export default TemperaturePage;
