const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'your-secret-key-same-as-esp32';

const headers = {
  'Content-Type': 'application/json',
  'x-api-key': API_KEY,
};

export async function fetchDeviceData(deviceId, limit = 50) {
  const res = await fetch(`${API_BASE_URL}/data/${deviceId}?limit=${limit}`, { headers });
  if (!res.ok) throw new Error('Failed to fetch data');
  return res.json();
}

export async function fetchDeviceFaults(deviceId, limit = 10) {
  const res = await fetch(`${API_BASE_URL}/faults/${deviceId}?limit=${limit}`, { headers });
  if (!res.ok) throw new Error('Failed to fetch faults');
  return res.json();
}

export async function fetchDevicePredictions(deviceId, limit = 5) {
  const res = await fetch(`${API_BASE_URL}/predictions/${deviceId}?limit=${limit}`, { headers });
  if (!res.ok) throw new Error('Failed to fetch predictions');
  return res.json();
}
