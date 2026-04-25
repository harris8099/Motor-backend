import React from 'react';
import { useParams } from 'react-router-dom';
import { Brain } from 'lucide-react';

function AIPageTest() {
  const { deviceId } = useParams();

  return (
    <div style={{ padding: '2rem', minHeight: '100vh', background: '#0f172a' }}>
      <h1 style={{ color: '#f8fafc', marginBottom: '2rem' }}>AI Insights - Test Version</h1>
      
      <div style={{ 
        background: 'rgba(30, 41, 59, 0.6)', 
        border: '1px solid rgba(148, 163, 184, 0.1)', 
        borderRadius: '12px', 
        padding: '2rem',
        marginBottom: '2rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <div style={{ 
            background: 'linear-gradient(135deg, #b026ff 0%, #00f0ff 100%)', 
            color: 'white', 
            padding: '1rem', 
            borderRadius: '12px' 
          }}>
            <Brain size={28} />
          </div>
          <div>
            <h2 style={{ margin: 0, color: '#f8fafc' }}>Device: {deviceId}</h2>
            <p style={{ margin: '0.25rem 0 0 0', color: '#94a3b8' }}>Test page - no API dependencies</p>
          </div>
        </div>
        
        <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>
          This is a minimal test version of the AI page to verify that the basic component structure works.
          If this page loads and stays visible, the issue is with the API calls or data fetching.
        </p>
      </div>

      <div style={{ 
        background: 'rgba(30, 41, 59, 0.6)', 
        border: '1px solid rgba(148, 163, 184, 0.1)', 
        borderRadius: '12px', 
        padding: '2rem'
      }}>
        <h3 style={{ color: '#f8fafc', marginBottom: '1rem' }}>AI Models Status</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
          {[
            { name: 'Anomaly Detection', status: 'Active' },
            { name: 'Overheating Prediction', status: 'Active' },
            { name: 'Bearing Failure Prediction', status: 'Active' },
            { name: 'Stall Risk Prediction', status: 'Active' },
            { name: 'Efficiency Degradation', status: 'Active' },
            { name: 'Predictive Maintenance', status: 'Active' },
            { name: 'AI Expert Commentary', status: 'Active' }
          ].map((model, index) => (
            <div key={index} style={{ 
              background: 'rgba(30, 41, 59, 0.8)', 
              border: '1px solid rgba(148, 163, 184, 0.1)', 
              borderRadius: '8px', 
              padding: '1rem' 
            }}>
              <h4 style={{ margin: '0 0 0.5rem 0', color: '#f8fafc' }}>{model.name}</h4>
              <p style={{ margin: 0, color: '#22c55e', fontSize: '0.85rem' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', backgroundColor: '#22c55e', borderRadius: '50%', marginRight: '0.5rem' }}></span>
                {model.status}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default AIPageTest;
