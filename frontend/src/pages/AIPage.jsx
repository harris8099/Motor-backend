import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Brain, TrendingUp, AlertTriangle, Wind, Wrench, Activity, RefreshCw } from 'lucide-react';
import { fetchDevicePredictions, fetchDeviceData } from '../api';
import PredictionsBadge from '../components/PredictionsBadge';
import Breadcrumbs from '../components/Breadcrumbs';
import LiveIndicator from '../components/LiveIndicator';
import SkeletonCard from '../components/SkeletonCard';
import './PageStyles.css';

function AIPage() {
  const { deviceId } = useParams();
  const [predictions, setPredictions] = useState([]);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError('');
        const [predsRes, dataRes] = await Promise.all([
          fetchDevicePredictions(deviceId, 10),
          fetchDeviceData(deviceId, 20),
        ]);
        setPredictions(predsRes.data || []);
        setData(dataRes.data || []);
        setLastUpdated(new Date());
      } catch (err) {
        console.error('Failed to load AI data', err);
        setError('Could not load AI predictions. Please check API connection.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [deviceId]);

  const aiModels = [
    {
      id: 'anomaly',
      name: 'Anomaly Detection',
      icon: TrendingUp,
      description: 'Isolation Forest ML algorithm detects unusual patterns in sensor data',
      status: 'ML-Based (Isolation Forest)'
    },
    {
      id: 'overheating',
      name: 'Overheating Prediction',
      icon: TrendingUp,
      description: 'Time series analysis predicts temperature trends and thermal runaway',
      status: 'ML-Based (Linear Regression)'
    },
    {
      id: 'bearing',
      name: 'Bearing Failure Prediction',
      icon: Wind,
      description: 'Statistical ML analysis of vibration patterns for bearing degradation',
      status: 'ML-Based (Statistical Analysis)'
    },
    {
      id: 'stall',
      name: 'Stall Risk Prediction',
      icon: AlertTriangle,
      description: 'ML models analyze power, current, and efficiency for stall detection',
      status: 'ML-Based (Multi-factor Analysis)'
    },
    {
      id: 'efficiency',
      name: 'Efficiency Degradation',
      icon: Activity,
      description: 'Polynomial regression tracks motor efficiency degradation over time',
      status: 'ML-Based (Polynomial Regression)'
    },
    {
      id: 'maintenance',
      name: 'Predictive Maintenance',
      icon: Wrench,
      description: 'Usage pattern analysis and stress-based maintenance scheduling',
      status: 'ML-Based (Pattern Analysis)'
    },
    {
      id: 'gemini',
      name: 'AI Expert Commentary',
      icon: Brain,
      description: 'Gemini AI provides expert comments on ML predictions (not making predictions)',
      status: 'AI Commentary Only'
    }
  ];

  return (
    <div className="page-container">
      <Breadcrumbs />
      
      <header className="page-header">
        <div className="header-with-icon">
          <div className="header-icon-wrapper ai">
            <Brain size={28} />
          </div>
          <div>
            <h1>AI Insights</h1>
            <p className="page-subtitle">Machine learning predictions and maintenance forecasts</p>
          </div>
        </div>
        <div className="header-meta">
          <LiveIndicator isLive={!loading && !error} />
          <span className="last-updated">
            {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Waiting...'}
          </span>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}
      
      {/* Skeleton Loading State */}
      {loading && (
        <div className="skeleton-grid">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {/* AI Hero Banner */}
      <section className="ai-hero-section">
        <div className="ai-hero-card">
          <div className="ai-hero-icon">
            <Brain size={40} />
          </div>
          <div className="ai-hero-content">
            <h2>AI-Powered Predictive Maintenance</h2>
            <p>Our machine learning models analyze real-time sensor data to predict failures before they happen, helping you prevent costly downtime.</p>
          </div>
        </div>
      </section>

      {/* AI Models Grid */}
      <section className="ai-models-section">
        <h2>Active AI Models</h2>
        <div className="ai-models-grid">
          {aiModels.map((model) => (
            <div key={model.id} className="ai-model-card">
              <div className="ai-model-header">
                <model.icon size={24} />
                <h3>{model.name}</h3>
              </div>
              <p className="ai-model-desc">{model.description}</p>
              <div className="ai-model-status">
                <span className="status-dot active"></span>
                {model.status}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Current Predictions */}
      <section className="predictions-section">
        <h2>Current Predictions</h2>
        <div className="panel">
          <PredictionsBadge predictions={predictions} />
        </div>
      </section>

      {/* Recent Predictions Table */}
      {predictions.length > 0 && (
        <section className="predictions-table-section">
          <h2>Prediction History</h2>
          <div className="panel">
            <div className="predictions-table">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Severity</th>
                    <th>Confidence</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((pred, idx) => (
                    <tr key={idx}>
                      <td>{new Date(pred.predicted_at).toLocaleString()}</td>
                      <td>{pred.prediction_type?.replace('_', ' ')}</td>
                      <td>
                        <span className={`severity-badge severity-${pred.severity}`}>
                          {pred.severity}
                        </span>
                      </td>
                      <td>{Math.round(pred.confidence * 100)}%</td>
                      <td>{pred.predicted_value?.toFixed ? pred.predicted_value.toFixed(2) : pred.predicted_value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default AIPage;
