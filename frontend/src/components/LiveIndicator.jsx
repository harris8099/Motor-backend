import React from 'react';
import './LiveIndicator.css';

function LiveIndicator({ isLive = true }) {
  return (
    <div className={`live-indicator ${isLive ? 'live' : 'offline'}`}>
      <span className="live-dot"></span>
      <span className="live-text">{isLive ? 'LIVE' : 'OFFLINE'}</span>
    </div>
  );
}

export default LiveIndicator;
