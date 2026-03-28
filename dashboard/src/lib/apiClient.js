const API_BASE = import.meta.env.VITE_API_URL || '';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  // Health
  health: () => request('/api/health'),

  // Patients
  getPatients: (params = '') => request(`/api/patients${params ? '?' + params : ''}`),
  getPatient: (id) => request(`/api/patients/${id}`),
  createPatient: (data) => request('/api/patients', { method: 'POST', body: JSON.stringify(data) }),
  updatePatient: (id, data) => request(`/api/patients/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Slide analysis
  analyzeSlide: (formData) => request('/api/analysis/upload', { method: 'POST', body: formData, headers: {} }),
  getAnalysis: (id) => request(`/api/analysis/${id}`),

  // Predictions
  predict: (patientId) => request(`/api/predictions/${patientId}`),
  predictSubtype: (data) => request('/api/predictions/subtype', { method: 'POST', body: JSON.stringify(data) }),

  // Digital Twin
  getTwin: (patientId) => request(`/api/digital-twin/${patientId}`),
  forecastTwin: (patientId, data) => request(`/api/digital-twin/${patientId}/forecast`, { method: 'POST', body: JSON.stringify(data) }),
  compareTreatments: (patientId, data) => request(`/api/digital-twin/${patientId}/compare-treatments`, { method: 'POST', body: JSON.stringify(data) }),

  // Reports
  generateReport: (patientId, format = 'json') => request(`/api/reports/${patientId}?format=${format}`),

  // Cohort
  getCohortStats: () => request('/api/cohort/stats'),
  getCohortSubtypes: () => request('/api/cohort/subtypes'),
  getCohortSurvival: () => request('/api/cohort/survival'),

  // Knowledge Graph
  getKGNodes: (query = '') => request(`/api/knowledge-graph/nodes${query ? '?q=' + query : ''}`),
  getKGPathways: (gene) => request(`/api/knowledge-graph/pathways/${gene}`),

  // Federated
  getFederatedStatus: () => request('/api/federated/status'),
  getFederatedHistory: () => request('/api/federated/history'),
};

export default api;
