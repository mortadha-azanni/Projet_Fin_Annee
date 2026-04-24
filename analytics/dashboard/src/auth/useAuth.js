import { useState, useEffect } from 'react';

const AUTH_KEY = 'searchily_analytics_auth';
const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || '';

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const stored = localStorage.getItem(AUTH_KEY);
    if (stored) {
      try {
        const { expiry } = JSON.parse(stored);
        if (Date.now() < expiry) {
          setIsAuthenticated(true);
        } else {
          localStorage.removeItem(AUTH_KEY);
        }
      } catch {
        localStorage.removeItem(AUTH_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email, password) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${GATEWAY_URL}/auth/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Invalid credentials');
      }
      const data = await res.json();
      if (data.role !== 'admin') {
        throw new Error('Access restricted to admins only');
      }
      localStorage.setItem(AUTH_KEY, JSON.stringify({
        token: data.access_token || data.token,
        role: data.role,
        expiry: Date.now() + 8 * 60 * 60 * 1000,
      }));
      setIsAuthenticated(true);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem(AUTH_KEY);
    setIsAuthenticated(false);
  };

  const getToken = () => {
    try {
      const stored = localStorage.getItem(AUTH_KEY);
      if (stored) {
        const { token } = JSON.parse(stored);
        return token || '';
      }
    } catch { /* ignore */ }
    return '';
  };

  return { isAuthenticated, isLoading, error, login, logout, getToken };
}
