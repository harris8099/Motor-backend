import React from 'react';
import { Outlet, NavLink, useParams, Link } from 'react-router-dom';
import { ChevronLeft, Cpu } from 'lucide-react';
import { 
  IconOverview, IconAI, IconPower, IconTemp, 
  IconVibration, IconFaults, IconSettings, IconTerminal 
} from '../components/CustomIcons';
import './DeviceLayout.css';

function DeviceLayout() {
  const { deviceId } = useParams();

  const navItems = [
    { path: 'overview', label: 'Overview', icon: IconOverview },
    { path: 'ai', label: 'AI Insights', icon: IconAI },
    { path: 'power', label: 'Power & Energy', icon: IconPower },
    { path: 'temperature', label: 'Temperature', icon: IconTemp },
    { path: 'vibration', label: 'Vibration', icon: IconVibration },
    { path: 'faults', label: 'Faults', icon: IconFaults },
    { path: 'terminal', label: 'Terminal', icon: IconTerminal },
    { path: 'settings', label: 'Settings', icon: IconSettings },
  ];

  return (
    <div className="device-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <Link to="/" className="back-link">
            <ChevronLeft size={20} />
            Back to Devices
          </Link>
          <div className="device-info">
            <Cpu size={24} style={{ color: 'var(--accent-1)' }} />
            <span className="device-label">{deviceId}</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={`/device/${deviceId}/${item.path}`}
              className={({ isActive }) => 
                `nav-link ${isActive ? 'active' : ''}`
              }
            >
              <item.icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="device-content">
        <Outlet />
      </main>
    </div>
  );
}

export default DeviceLayout;
