import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './useAuth';

export default function LoginPage() {
  const { login, isLoading, error } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async () => {
    const success = await login(email, password);
    if (success) navigate('/');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSubmit();
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: '#f0fdf4'
    }}>
      <div style={{
        background: '#ffffff', padding: '2.5rem', borderRadius: '12px',
        width: '100%', maxWidth: '400px',
        boxShadow: '0 25px 50px rgba(22,101,52,0.15)',
        border: '1px solid #bbf7d0'
      }}>
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ color: '#14532d', fontSize: '1.5rem', fontWeight: '700', margin: '0 0 0.25rem' }}>
            Searchily Analytics
          </h1>
          <p style={{ color: '#4b7c59', fontSize: '0.875rem', margin: 0 }}>
            Admin access only
          </p>
        </div>

        {error && (
          <div style={{
            background: '#fef2f2', border: '1px solid #dc2626',
            color: '#dc2626', padding: '0.75rem 1rem', borderRadius: '6px',
            marginBottom: '1.25rem', fontSize: '0.875rem'
          }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{
              color: '#4b7c59', fontSize: '0.8rem',
              display: 'block', marginBottom: '0.4rem', fontWeight: '500'
            }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="admin@example.com"
              style={{
                width: '100%', padding: '0.7rem 0.875rem',
                background: '#f0fdf4', border: '1px solid #bbf7d0',
                borderRadius: '6px', color: '#14532d',
                fontSize: '0.875rem', boxSizing: 'border-box',
                outline: 'none'
              }}
            />
          </div>

          <div>
            <label style={{
              color: '#4b7c59', fontSize: '0.8rem',
              display: 'block', marginBottom: '0.4rem', fontWeight: '500'
            }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="••••••••"
              style={{
                width: '100%', padding: '0.7rem 0.875rem',
                background: '#f0fdf4', border: '1px solid #bbf7d0',
                borderRadius: '6px', color: '#14532d',
                fontSize: '0.875rem', boxSizing: 'border-box',
                outline: 'none'
              }}
            />
          </div>

          <button
            onClick={handleSubmit}
            disabled={isLoading || !email || !password}
            style={{
              width: '100%', padding: '0.75rem',
              background: isLoading ? '#15803d' : '#16a34a',
              border: 'none', borderRadius: '6px',
              color: '#f0fdf4', fontSize: '0.875rem',
              fontWeight: '600', cursor: isLoading || !email || !password ? 'not-allowed' : 'pointer',
              opacity: isLoading || !email || !password ? 0.7 : 1,
              marginTop: '0.5rem', transition: 'all 0.15s'
            }}
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </div>
      </div>
    </div>
  );
}
