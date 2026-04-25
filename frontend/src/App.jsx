import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Home from './pages/Home';
import DeviceLayout from './pages/DeviceLayout';
import Overview from './pages/Overview';
import AIPage from './pages/AIPage';
import PowerPage from './pages/PowerPage';
import TemperaturePage from './pages/TemperaturePage';
import VibrationPage from './pages/VibrationPage';
import FaultsPage from './pages/FaultsPage';
import TerminalPage from './pages/TerminalPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/device/:deviceId" element={<DeviceLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<Overview />} />
          <Route path="ai" element={<AIPage />} />
          <Route path="power" element={<PowerPage />} />
          <Route path="temperature" element={<TemperaturePage />} />
          <Route path="vibration" element={<VibrationPage />} />
          <Route path="faults" element={<FaultsPage />} />
          <Route path="terminal" element={<TerminalPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
