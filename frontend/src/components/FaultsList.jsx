import React from 'react';
import { AlertTriangle } from 'lucide-react';

function formatFaultType(value) {
  return value.replace('fault_', '').replace(/_/g, ' ');
}

export default function FaultsList({ faults }) {
  if (!faults || faults.length === 0) {
    return <div className="empty-copy">No recent faults detected.</div>;
  }

  return (
    <div>
      {faults.map((fault) => (
        <div key={fault.id} className="fault-item">
          <div className="fault-name">
            <AlertTriangle size={16} />
            {formatFaultType(fault.fault_type)}
          </div>
          <div className="fault-time">{new Date(fault.ts).toLocaleString()}</div>
        </div>
      ))}
    </div>
  );
}
