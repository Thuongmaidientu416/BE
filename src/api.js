/**
 * WanderHUB Frontend — API Client
 * Centralized fetch wrapper for backend communication.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : 'https://wanderhun.onrender.com');

/**
 * Get the stored JWT token.
 */
function getToken() {
  return localStorage.getItem('wanderhub_token');
}

/**
 * Store the JWT token.
 */
export function setToken(token) {
  localStorage.setItem('wanderhub_token', token);
}

/**
 * Remove the stored token (logout).
 */
export function clearToken() {
  localStorage.removeItem('wanderhub_token');
}

/**
 * Make an API request with automatic auth headers and error handling.
 */
async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API error ${response.status}`);
  }

  return response.json();
}

// ── Auth ──────────────────────────────────────────────────────────

export async function apiLogin(email, password) {
  const data = await request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setToken(data.token);
  return data;
}

export async function apiRegister(name, email, password) {
  const data = await request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  });
  setToken(data.token);
  return data;
}

export async function apiGetMe() {
  return request('/api/auth/me');
}

// ── Landing ──────────────────────────────────────────────────────

export async function apiGetLanding() {
  return request('/api/landing');
}

// ── Providers ────────────────────────────────────────────────────

export async function apiGetProviders(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      query.append(key, value);
    }
  });
  return request(`/api/providers?${query.toString()}`);
}

export async function apiGetFeaturedProviders() {
  return request('/api/providers/featured');
}

export async function apiGetProvider(id) {
  return request(`/api/providers/${id}`);
}

// ── Itinerary (AI Custom Tour) ───────────────────────────────────

export async function apiGenerateItinerary(params) {
  return request('/api/itinerary/generate', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function apiRerouteItinerary(params) {
  return request('/api/itinerary/reroute', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function apiGetItinerary(id) {
  return request(`/api/itinerary/${id}`);
}

export async function apiSubmitFeedback(itineraryId, rating, comment) {
  return request(`/api/itinerary/${itineraryId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ rating, comment }),
  });
}

export async function apiTrackInteraction(payload) {
  return request('/api/interactions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ── Chat ─────────────────────────────────────────────────────────

export async function apiChat(message, history = [], groqKey = null) {
  return request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message, history, groq_key: groqKey }),
  });
}

// ── Plans ────────────────────────────────────────────────────────

export async function apiSelectPlan(planName, planKey) {
  return request('/api/plans/select', {
    method: 'POST',
    body: JSON.stringify({ plan_name: planName, plan_key: planKey }),
  });
}

export async function apiGetMyPlan() {
  return request('/api/plans/me');
}

// ── Contact ──────────────────────────────────────────────────────

export async function apiSubmitContact(name, email, subject, message) {
  return request('/api/contact', {
    method: 'POST',
    body: JSON.stringify({ name, email, subject, message }),
  });
}
