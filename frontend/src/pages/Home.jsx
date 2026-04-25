import React, { useState, useEffect } from 'react';
import { Activity, Plus, Cpu, ArrowRight, Trash2, Search, Wifi, WifiOff, Clock, Layers, X, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { fetchDevices, createDevice, createDevicesBulk, deleteDevice, updateDevice } from '../api';
import './Home.css';

function Home() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [bulkMode, setBulkMode] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Single device add
  const [newDeviceId, setNewDeviceId] = useState('');
  const [newDeviceName, setNewDeviceName] = useState('');
  
  // Bulk add
  const [bulkInput, setBulkInput] = useState('');

  // Fetch devices from backend on mount
  useEffect(() => {
    loadDevices();
    // Refresh every 10 seconds for more responsive updates
    const interval = setInterval(loadDevices, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadDevices = async () => {
    try {
      const data = await fetchDevices();
      // Transform backend data to frontend format
      const transformed = data.map(d => ({
        id: d.id,
        name: d.name || d.id,
        added: d.created_at,
        lastSeen: d.last_seen_at || d.created_at,
        isOnline: d.is_active && d.last_seen_at 
          ? (new Date() - new Date(d.last_seen_at)) / 1000 < 120 // Consider online if seen in last 2 min
          : false, // Devices that have never sent data should be offline
        is_active: d.is_active
      }));
      setDevices(transformed);
      setError('');
    } catch (err) {
      console.error('Failed to load devices:', err);
      setError('Failed to load devices. Please check API connection.');
    } finally {
      setLoading(false);
    }
  };

  const addSingleDevice = async (e) => {
    e.preventDefault();
    if (!newDeviceId.trim()) return;
    
    if (devices.some(d => d.id === newDeviceId.trim())) {
      alert('Device ID already exists!');
      return;
    }
    
    setIsSubmitting(true);
    try {
      await createDevice({
        id: newDeviceId.trim(),
        name: newDeviceName.trim() || undefined
      });
      
      await loadDevices();
      setNewDeviceId('');
      setNewDeviceName('');
      setShowAddPanel(false);
    } catch (err) {
      alert(`Failed to add device: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const addBulkDevices = async (e) => {
    e.preventDefault();
    const lines = bulkInput.split('\n').map(l => l.trim()).filter(l => l);
    const devicesToCreate = [];
    
    lines.forEach(line => {
      const parts = line.split(',').map(p => p.trim());
      const id = parts[0];
      const name = parts[1] || undefined;
      
      if (!id) return;
      if (!devices.some(d => d.id === id)) {
        devicesToCreate.push({ id, name });
      }
    });
    
    if (devicesToCreate.length === 0) {
      alert('No new devices to add (duplicates skipped)');
      return;
    }
    
    setIsSubmitting(true);
    try {
      await createDevicesBulk(devicesToCreate);
      await loadDevices();
      setBulkInput('');
      setShowAddPanel(false);
      setBulkMode(false);
    } catch (err) {
      alert(`Failed to add devices: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const removeDevice = async (deviceId) => {
    if (confirm(`Remove device ${deviceId}?`)) {
      try {
        await deleteDevice(deviceId);
        await loadDevices();
      } catch (err) {
        alert(`Failed to remove device: ${err.message}`);
      }
    }
  };

  const toggleDeviceStatus = async (e, deviceId) => {
    e.preventDefault();
    e.stopPropagation();
    const device = devices.find(d => d.id === deviceId);
    if (device) {
      try {
        await updateDevice(deviceId, { is_active: !device.is_active });
        await loadDevices();
      } catch (err) {
        alert(`Failed to update device: ${err.message}`);
      }
    }
  };

  const filteredDevices = devices.filter(d => 
    d.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatLastSeen = (date) => {
    const now = new Date();
    const then = new Date(date);
    const diff = Math.floor((now - then) / 1000);
    
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  return (
    <div className="home-page">
      <header className="home-header">
        <div className="header-content">
          <div className="logo">
            <Activity size={32} />
            <h1>Smart Motor Command Center</h1>
          </div>
          <p className="subtitle">Manage and monitor your motor devices</p>
        </div>
      </header>

      <main className="home-main">
        {error && <div className="error-banner">{error}</div>}
        
        {/* Stats Bar */}
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-value">{devices.length}</span>
            <span className="stat-label">Total Devices</span>
          </div>
          <div className="stat-item">
            <span className="stat-value online">{devices.filter(d => d.isOnline).length}</span>
            <span className="stat-label">Online</span>
          </div>
          <div className="stat-item">
            <span className="stat-value offline">{devices.filter(d => !d.isOnline).length}</span>
            <span className="stat-label">Offline</span>
          </div>
          <button 
            className="refresh-btn"
            onClick={loadDevices}
            title="Refresh device status"
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'spinning' : ''} />
          </button>
        </div>

        {/* Devices Section */}
        <section className="devices-section">
          <div className="section-header-row">
            <h2>Your Devices</h2>
            <button 
              className="toggle-add-btn"
              onClick={() => setShowAddPanel(!showAddPanel)}
            >
              {showAddPanel ? <X size={18} /> : <Plus size={18} />}
              {showAddPanel ? 'Cancel' : 'Add Device'}
            </button>
          </div>

          {/* Search */}
          <div className="search-bar">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search devices by name or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="clear-search" onClick={() => setSearchQuery('')}>
                <X size={14} />
              </button>
            )}
          </div>

          {/* Add Device Panel */}
          {showAddPanel && (
            <div className="add-device-panel">
              {isSubmitting && <div className="submitting-overlay">Processing...</div>}
              <div className="add-mode-toggle">
                <button 
                  className={!bulkMode ? 'active' : ''}
                  onClick={() => setBulkMode(false)}
                >
                  Single Device
                </button>
                <button 
                  className={bulkMode ? 'active' : ''}
                  onClick={() => setBulkMode(true)}
                >
                  <Layers size={16} />
                  Bulk Add
                </button>
              </div>

              {!bulkMode ? (
                <form onSubmit={addSingleDevice} className="add-device-form">
                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="device-id">Device ID *</label>
                      <input
                        id="device-id"
                        type="text"
                        value={newDeviceId}
                        onChange={(e) => setNewDeviceId(e.target.value)}
                        placeholder="e.g., DEVICE_002"
                        required
                        autoFocus
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="device-name">Device Name</label>
                      <input
                        id="device-name"
                        type="text"
                        value={newDeviceName}
                        onChange={(e) => setNewDeviceName(e.target.value)}
                        placeholder="e.g., Motor 2"
                      />
                    </div>
                  </div>
                  <button type="submit" className="add-btn">
                    <Plus size={18} />
                    Add Device
                  </button>
                </form>
              ) : (
                <form onSubmit={addBulkDevices} className="bulk-add-form">
                  <div className="form-group">
                    <label>Bulk Device List</label>
                    <p className="help-text">Enter one device per line: ID, Name (optional)</p>
                    <textarea
                      value={bulkInput}
                      onChange={(e) => setBulkInput(e.target.value)}
                      placeholder={`DEVICE_002, Motor 2\nDEVICE_003, Motor 3\nDEVICE_004`}
                      rows={6}
                      autoFocus
                    />
                  </div>
                  <button type="submit" className="add-btn">
                    <Layers size={18} />
                    Add {bulkInput.split('\n').filter(l => l.trim()).length || 0} Devices
                  </button>
                </form>
              )}
            </div>
          )}

          {/* Devices Grid */}
          <div className="devices-grid">
            {filteredDevices.length === 0 ? (
              <div className="no-devices">
                <Cpu size={48} />
                <p>{searchQuery ? 'No devices match your search' : 'No devices added yet'}</p>
              </div>
            ) : (
              filteredDevices.map((device) => (
                <Link 
                  key={device.id} 
                  to={`/device/${device.id}/overview`}
                  className={`device-card ${device.isOnline ? 'online' : 'offline'}`}
                >
                  <div className="device-header">
                    <div className="device-icon">
                      <Cpu size={24} />
                    </div>
                    <button 
                      className={`status-toggle ${device.isOnline ? 'online' : 'offline'}`}
                      onClick={(e) => toggleDeviceStatus(e, device.id)}
                      title={device.isOnline ? 'Set offline' : 'Set online'}
                    >
                      {device.isOnline ? <Wifi size={16} /> : <WifiOff size={16} />}
                    </button>
                  </div>

                  <div className="device-info">
                    <h3>{device.name}</h3>
                    <p className="device-id">{device.id}</p>
                  </div>

                  <div className="device-meta">
                    <span className={`status-badge ${device.isOnline ? 'online' : 'offline'}`}>
                      {device.isOnline ? 'Online' : 'Offline'}
                    </span>
                    <span className="last-seen">
                      <Clock size={12} />
                      {formatLastSeen(device.lastSeen)}
                    </span>
                  </div>

                  <div className="device-actions">
                    <ArrowRight size={20} />
                  </div>

                  <button 
                    className="remove-btn"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      removeDevice(device.id);
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                </Link>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default Home;
