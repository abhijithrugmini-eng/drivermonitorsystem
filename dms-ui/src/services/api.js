export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${options.method || 'GET'} ${path} failed: ${res.status} ${body}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function getVehicles() {
  return request('/api/vehicles');
}

export function getAlerts(status = 'active') {
  return request(`/api/alerts?status=${encodeURIComponent(status)}`);
}

export function getAlertDetail(id) {
  return request(`/api/alerts/${encodeURIComponent(id)}`);
}

export function acknowledgeAlert(id, acknowledgedBy = 'dispatcher') {
  return request(`/api/alerts/${encodeURIComponent(id)}/acknowledge`, {
    method: 'POST',
    body: JSON.stringify({ acknowledged_by: acknowledgedBy }),
  });
}

export function sendAdvisory(id, message) {
  return request(`/api/alerts/${encodeURIComponent(id)}/advisory`, {
    method: 'POST',
    body: JSON.stringify({ message: message ?? null }),
  });
}

export function evidenceUrl(path) {
  if (!path) return null;
  return `${API_BASE_URL}${path}`;
}
