export function ChartWrapper({ title, children }) {
  return (
    <div style={{
      background: '#ffffff', borderRadius: '12px',
      padding: '1.5rem', border: '1px solid #bbf7d0'
    }}>
      <h3 style={{ margin: '0 0 1.5rem', color: '#14532d', fontSize: '1rem', fontWeight: '600' }}>
        {title}
      </h3>
      {children}
    </div>
  );
}

export function ChartSkeleton({ title }) {
  return (
    <div style={{
      background: '#ffffff', borderRadius: '12px',
      padding: '1.5rem', border: '1px solid #bbf7d0'
    }}>
      <h3 style={{ margin: '0 0 1.5rem', color: '#14532d', fontSize: '1rem' }}>{title}</h3>
      <div style={{
        height: '300px', background: '#f0fdf4', borderRadius: '8px',
        opacity: 0.6
      }} />
    </div>
  );
}

export function ChartError({ title, error }) {
  return (
    <div style={{
      background: '#fef2f2', borderRadius: '12px',
      padding: '1.5rem', border: '1px solid #dc2626'
    }}>
      <h3 style={{ margin: '0 0 1rem', color: '#14532d', fontSize: '1rem' }}>{title}</h3>
      <p style={{ color: '#dc2626', fontSize: '0.875rem', margin: 0 }}>
        {error?.message || 'Failed to load data'}
      </p>
    </div>
  );
}
