import React from 'react';
import { Link, useParams, useLocation } from 'react-router-dom';
import { Home, ChevronRight } from 'lucide-react';
import './Breadcrumbs.css';

function Breadcrumbs() {
  const { deviceId } = useParams();
  const location = useLocation();
  
  const pathSegments = location.pathname.split('/').filter(Boolean);
  
  // Build breadcrumb items
  const items = [
    { label: 'Home', path: '/', icon: Home }
  ];
  
  if (deviceId) {
    items.push({ label: deviceId, path: `/device/${deviceId}/overview` });
    
    // Add current page
    const currentPage = pathSegments[pathSegments.length - 1];
    if (currentPage && currentPage !== deviceId) {
      const pageLabels = {
        'overview': 'Overview',
        'ai': 'AI Insights',
        'power': 'Power & Energy',
        'temperature': 'Temperature',
        'vibration': 'Vibration',
        'faults': 'Faults',
        'settings': 'Settings'
      };
      items.push({ label: pageLabels[currentPage] || currentPage, path: location.pathname, isLast: true });
    }
  }

  return (
    <nav className="breadcrumbs">
      {items.map((item, index) => (
        <React.Fragment key={index}>
          {index > 0 && <ChevronRight size={16} className="breadcrumb-separator" />}
          {item.isLast ? (
            <span className="breadcrumb-current">{item.label}</span>
          ) : (
            <Link to={item.path} className="breadcrumb-link">
              {item.icon && <item.icon size={14} />}
              <span>{item.label}</span>
            </Link>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}

export default Breadcrumbs;
