import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Terminal, Play, Square, Download, Trash2 } from 'lucide-react';
import { fetchDeviceData } from '../api';
import './PageStyles.css';
import './TerminalPage.css';

function TerminalPage() {
  const { deviceId } = useParams();
  const [logs, setLogs] = useState([]);
  const [isStreaming, setIsStreaming] = useState(true);
  const scrollRef = useRef(null);
  const streamInterval = useRef(null);

  // Poll for new data every 2 seconds to simulate a live stream
  useEffect(() => {
    if (isStreaming) {
      pollData();
      streamInterval.current = setInterval(pollData, 2000);
    } else {
      clearInterval(streamInterval.current);
    }
    return () => clearInterval(streamInterval.current);
  }, [isStreaming, deviceId]);

  const pollData = async () => {
    try {
      const result = await fetchDeviceData(deviceId, 1);
      if (result.data && result.data.length > 0) {
        const payload = result.data[0];
        
        // Check if we already have this exact timestamp in logs
        setLogs(prev => {
          if (prev.length > 0 && prev[prev.length - 1].ts === payload.ts) {
            return prev; // Duplicate, skip
          }
          
          const newLog = {
            id: Date.now() + Math.random(),
            ts: payload.ts,
            raw: JSON.stringify({
              deviceId: payload.device_id,
              motor: { running: payload.motor_running, rpm: payload.rpm },
              power: { voltage: payload.voltage, current: payload.current, power: payload.power },
              temperature: { t1: payload.temp1, t2: payload.temp2 },
              vibration: { x: payload.accel_x, y: payload.accel_y, z: payload.accel_z }
            }, null, 2)
          };
          
          const updated = [...prev, newLog];
          return updated.slice(-50); // Keep last 50
        });
      }
    } catch (err) {
      console.error("Stream error:", err);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const clearLogs = () => setLogs([]);

  const downloadLogs = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(logs.map(l => JSON.parse(l.raw)), null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `telemetry_${deviceId}_${Date.now()}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  return (
    <div className="page-container terminal-container animate-fade-in">
      <header className="page-header">
        <div>
          <div className="header-with-icon">
            <div className="header-icon-wrapper ai">
              <Terminal size={28} color="#000" />
            </div>
            <div>
              <h1>Telemetry Terminal</h1>
              <p className="page-subtitle">Live JSON payload stream from device</p>
            </div>
          </div>
        </div>
        
        <div className="terminal-controls">
          <button 
            className={`control-btn ${isStreaming ? 'active' : ''}`}
            onClick={() => setIsStreaming(!isStreaming)}
          >
            {isStreaming ? <><Square size={16}/> Pause</> : <><Play size={16}/> Resume</>}
          </button>
          <button className="control-btn" onClick={clearLogs}>
            <Trash2 size={16}/> Clear
          </button>
          <button className="control-btn primary" onClick={downloadLogs}>
            <Download size={16}/> Export
          </button>
        </div>
      </header>

      <section className="terminal-window">
        <div className="terminal-header-bar">
          <div className="window-dots">
            <span className="dot red"></span>
            <span className="dot yellow"></span>
            <span className="dot green"></span>
          </div>
          <div className="window-title">bash — {deviceId} — Live Stream</div>
          <div className="window-status">
            {isStreaming ? (
              <span className="status-indicator blinking">Receiving Data...</span>
            ) : (
              <span className="status-indicator paused">Paused</span>
            )}
          </div>
        </div>
        
        <div className="terminal-output" ref={scrollRef}>
          {logs.length === 0 ? (
            <div className="terminal-empty">
              <span className="cursor-blink">Waiting for payload...</span>
            </div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="log-entry">
                <div className="log-meta">
                  <span className="log-timestamp">[{new Date(log.ts).toISOString()}]</span>
                  <span className="log-source">INCOMING PAYLOAD:</span>
                </div>
                <pre className="log-code">{log.raw}</pre>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

export default TerminalPage;
