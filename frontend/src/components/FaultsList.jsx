import React from 'react';
import { AlertTriangle } from 'lucide-react';

export default function FaultsList({ faults }) {
  if (!faults || faults.length === 0) {
    return <div style={{ color: 'var(--text-muted)' }}>No recent faults detected.</div>;
  }

  return (
    <div>
      {faults.map(fault => (
        <div key={fault.id} className="fault-item">
          <div className="fault-name">
            <AlertTriangle size={16} />
            {fault.fault_type.replace('fault_', '').replace('_', ' ')}
          </div>
          <div className="fault-time">
            {new Date(fault.ts).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}
