import React from 'react';

export const IconOverview = ({ size = 24, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect x="3" y="3" width="7" height="7" rx="2" stroke="#00f0ff" strokeWidth="2" fill="rgba(0,240,255,0.2)" />
    <rect x="14" y="3" width="7" height="7" rx="2" stroke="#b026ff" strokeWidth="2" fill="rgba(176,38,255,0.2)" />
    <rect x="3" y="14" width="7" height="7" rx="2" stroke="#b026ff" strokeWidth="2" fill="rgba(176,38,255,0.2)" />
    <rect x="14" y="14" width="7" height="7" rx="2" stroke="#00f0ff" strokeWidth="2" fill="rgba(0,240,255,0.2)" />
  </svg>
);

export const IconAI = ({ size = 24, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="#b026ff" strokeWidth="2" fill="rgba(176,38,255,0.3)"/>
    <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="#00f0ff" strokeWidth="2"/>
  </svg>
);

export const IconPower = ({ size = 24, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="#ffd700" strokeWidth="2" fill="rgba(255,215,0,0.3)" />
  </svg>
);

export const IconTemp = ({ size = 24, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" stroke="#ff0055" strokeWidth="2" fill="rgba(255,0,85,0.3)" />
  </svg>
);

export const IconVibration = ({ size = 24, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path d="M2 12h4l3-9 5 18 3-9h5" stroke="#00ffaa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const IconFaults = ({ size = 24, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path d="M12 2L1 21h22L12 2z" stroke="#ff5500" strokeWidth="2" fill="rgba(255,85,0,0.2)"/>
    <line x1="12" y1="9" x2="12" y2="15" stroke="#ff0000" strokeWidth="2" strokeLinecap="round"/>
    <circle cx="12" cy="18" r="1" fill="#ff0000"/>
  </svg>
);

export const IconSettings = ({ size = 24, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <circle cx="12" cy="12" r="3" stroke="#94a3b8" strokeWidth="2" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" stroke="#94a3b8" strokeWidth="2"/>
  </svg>
);

export const IconTerminal = ({ size = 24, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect x="2" y="4" width="20" height="16" rx="2" stroke="#00f0ff" strokeWidth="2" fill="rgba(0,240,255,0.1)"/>
    <path d="M6 8l4 4-4 4M14 16h4" stroke="#00f0ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
