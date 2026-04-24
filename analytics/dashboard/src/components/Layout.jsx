import { useAuth } from '../auth/useAuth';

export default function Layout({ children }) {
  const { logout } = useAuth();
  return (
    <div style={{ minHeight: '100vh', background: '#f0fdf4', color: '#14532d' }}>
      <header style={{
        background: '#166534',
        borderBottom: '1px solid #bbf7d0',
        padding: '0.875rem 2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 8px rgba(22,101,52,0.15)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '32px', height: '32px', background: '#4ade80',
            borderRadius: '8px', display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontWeight: '800', color: '#14532d',
            fontSize: '1rem'
          }}>S</div>
          <div>
            <h1 style={{ margin: 0, fontSize: '1rem', fontWeight: '700', color: '#ffffff', letterSpacing: '0.02em' }}>
              Searchily Analytics
            </h1>
            <p style={{ margin: 0, fontSize: '0.7rem', color: '#bbf7d0', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Product Intelligence
            </p>
          </div>
        </div>
        <button
          onClick={logout}
          style={{
            background: 'transparent', border: '1px solid rgba(187,247,208,0.4)',
            color: '#bbf7d0', padding: '0.4rem 1rem',
            borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem',
            letterSpacing: '0.03em', transition: 'all 0.15s',
          }}
        >
          Sign Out
        </button>
      </header>
      <main style={{
        maxWidth: '960px',
        margin: '0 auto',
        padding: '2rem 1.5rem',
      }}>
        {children}
      </main>
    </div>
  );
}
