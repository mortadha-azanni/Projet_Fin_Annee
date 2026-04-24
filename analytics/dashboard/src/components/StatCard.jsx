export default function StatCard({ title, value, subtitle, color = '#16a34a' }) {
  return (
    <div style={{
      background: '#ffffff', borderRadius: '12px', padding: '1.5rem',
      border: '1px solid #bbf7d0', borderLeft: `4px solid ${color}`
    }}>
      <p style={{ margin: '0 0 0.5rem', color: '#4b7c59', fontSize: '0.875rem' }}>{title}</p>
      <p style={{ margin: '0 0 0.25rem', color: '#14532d', fontSize: '2rem', fontWeight: '700' }}>
        {value ?? '...'}
      </p>
      {subtitle && (
        <p style={{ margin: 0, color: '#4b7c59', fontSize: '0.75rem' }}>{subtitle}</p>
      )}
    </div>
  );
}
