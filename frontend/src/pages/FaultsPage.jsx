import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { AlertTriangle, Zap, Flame, Wind, CheckCircle, Clock } from 'lucide-react';
import { fetchDeviceData, fetchDeviceFaults } from '../api';
import MetricCard from '../components/MetricCard';
import FaultsList from '../components/FaultsList';
import Breadcrumbs from '../components/Breadcrumbs';
import LiveIndicator from '../components/LiveIndicator';
import SkeletonCard from '../components/SkeletonCard';
import './PageStyles.css';

function FaultsPage() {
  const { deviceId } = useParams();
  const [data, setData] = useState([]);
  const [faults, setFaults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError('');
        const [dataRes, faultsRes] = await Promise.all([
          fetchDeviceData(deviceId),
          fetchDeviceFaults(deviceId, 20),
        ]);
        setData(dataRes.data || []);
        setFaults(faultsRes.data || []);
      } catch (err) {
        console.error('Failed to load faults data', err);
        setError('Could not load fault data. Please check API connection.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [deviceId]);

  const latest = data.length > 0 ? data[0] : null;

  const faultTypes = [
    { key: 'fault_overcurrent', name: 'Over Current', icon: Zap },
    { key: 'fault_overtemp', name: 'Over Temperature', icon: Flame },
    { key: 'fault_stall', name: 'Motor Stall', icon: AlertTriangle },
    { key: 'fault_vibration', name: 'Vibration', icon: Wind },
    { key: 'fault_overvoltage', name: 'Over Voltage', icon: Zap },
    { key: 'fault_undervoltage', name: 'Under Voltage', icon: Zap },
  ];

  const activeFaults = latest ? faultTypes.filter(f => latest[f.key]) : [];

  return (
    <div className="page-container">
      <Breadcrumbs />
      
      <header className="page-header">
        <div className="header-with-icon">
          <div className="header-icon-wrapper faults">
            <AlertTriangle size={28} />
          </div>
          <div>
            <h1>Fault Status</h1>
            <p className="page-subtitle">Current faults and protection events</p>
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
          {/* Fault Status Grid */}
          <section className="metrics-section">
            <h2>Current Fault Status</h2>
            <div className="metrics-grid faults-grid">
              {faultTypes.map((fault, idx) => (
                <MetricCard 
                  key={fault.key}
                  title={fault.name} 
                  value={latest[fault.key] ? 'FAULT' : 'OK'} 
                  unit="" 
                  icon={fault.icon} 
                  delay={`delay-${(idx % 3) + 1}`}
                  isFault={latest[fault.key]}
                />
              ))}
            </div>
          </section>

          {/* Active Faults Summary */}
          <section className="active-faults-section">
            <h2>Active Faults Summary</h2>
            <div className="panel">
              {activeFaults.length > 0 ? (
                <div className="active-faults-list">
                  {activeFaults.map((fault) => (
                    <div key={fault.key} className="active-fault-item">
                      <fault.icon size={24} />
                      <div className="fault-details">
                        <span className="fault-name">{fault.name}</span>
                        <span className="fault-status">ACTIVE</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-faults-message">
                  <CheckCircle size={32} />
                  <p>No active faults - all systems operating normally</p>
                </div>
              )}
            </div>
          </section>

          {/* Trip Count */}
          <section className="trip-count-section">
            <h2>Protection Statistics</h2>
            <div className="metrics-grid compact">
              <MetricCard 
                title="Total Fault Trips" 
                value={latest.prot_fault_trip_count ?? 0} 
                unit="" 
                icon={AlertTriangle} 
                delay="delay-1" 
              />
              <MetricCard 
                title="Uptime" 
                value={Math.floor(latest.uptime_seconds / 3600)} 
                unit="hrs" 
                icon={Clock} 
                delay="delay-2" 
              />
            </div>
          </section>

          {/* Recent Faults History */}
          <section className="faults-history-section">
            <h2>Recent Fault Events</h2>
            <div className="panel">
              <FaultsList faults={faults} />
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export default FaultsPage;
