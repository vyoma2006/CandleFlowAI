// portal/src/hooks/useAuth.js
// ─────────────────────────────────────────────────────────────────────────────
// Manages JWT token, user state, login, logout, register.
// Token is stored in localStorage so it survives page refresh.

import { useState, useEffect, useCallback } from 'react';

const API = 'https://candleflowai.onrender.com';
const TOKEN_KEY = 'candleflow_token';
const USER_KEY  = 'candleflow_user';

export function useAuth() {
  const [token,   setToken]   = useState(() => localStorage.getItem(TOKEN_KEY) ?? null);
  const [user,    setUser]    = useState(() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) ?? 'null'); } catch { return null; }
  });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  // ── Attach token to every fetch automatically ─────────────────────────────
  const authFetch = useCallback(async (url, options = {}) => {
    const headers = { 'Content-Type': 'application/json', ...(options.headers ?? {}) };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(url, { ...options, headers });
  }, [token]);

  // ── Register ──────────────────────────────────────────────────────────────
  const register = async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      const res  = await fetch(`${API}/api/auth/register`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Registration failed');
      // Auto-login after register
      return await login(username, password);
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setLoading(false);
    }
  };

  // ── Login ─────────────────────────────────────────────────────────────────
  const login = async (username, password) => {
  setLoading(true);
  setError(null);

  try {
    const res = await fetch(`${API}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        username,
        password,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail ?? "Login failed");
    }

    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify({ username: data.username }));

    setToken(data.access_token);
    setUser({ username: data.username });

    return true;
  } catch (e) {
    setError(e.message);
    return false;
  } finally {
    setLoading(false);
  }
 };

  // ── Logout ────────────────────────────────────────────────────────────────
  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  };

  // ── Validate stored token on mount ────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => {
      if (!r.ok) logout(); // token expired or invalid
    }).catch(() => logout());
  }, []);  // eslint-disable-line

  return { token, user, loading, error, login, logout, register, authFetch, isAuthed: !!token };
}