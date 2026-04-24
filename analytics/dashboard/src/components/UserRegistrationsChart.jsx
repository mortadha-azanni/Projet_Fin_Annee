import { useState } from 'react';
import { useCubeQuery } from '../hooks/useCubeQuery';
import { ChartWrapper } from './ChartHelpers';

function ProfileCard({ user }) {
  const avatarUrl = user['UserProfile.avatar_url'];
  const fullName = user['UserProfile.full_name'] || 'No name set';
  const email = user['UserProfile.email'];
  const createdAt = user['UserProfile.created_at'];
  const verified = user['UserProfile.email_verified'];
  const googleId = user['UserProfile.google_id'];

  const initials = fullName
    .split(' ')
    .map(n => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();

  const formattedDate = createdAt
    ? new Date(createdAt).toLocaleDateString('en-GB', {
        day: 'numeric', month: 'long', year: 'numeric'
      })
    : '—';

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      gap: '1.25rem', padding: '1.5rem 1rem',
    }}>
      <div style={{ position: 'relative' }}>
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt={fullName}
            style={{
              width: '80px', height: '80px', borderRadius: '50%',
              objectFit: 'cover', border: '3px solid #bbf7d0',
              boxShadow: '0 2px 8px rgba(22,101,52,0.12)',
            }}
            onError={e => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
          />
        ) : null}
        <div style={{
          width: '80px', height: '80px', borderRadius: '50%',
          background: '#166534', border: '3px solid #bbf7d0',
          display: avatarUrl ? 'none' : 'flex',
          alignItems: 'center', justifyContent: 'center',
          fontSize: '1.5rem', fontWeight: '800', color: '#ffffff',
          boxShadow: '0 2px 8px rgba(22,101,52,0.12)',
        }}>
          {initials}
        </div>
        <div style={{
          position: 'absolute', bottom: '2px', right: '2px',
          width: '16px', height: '16px', borderRadius: '50%',
          background: verified === 'Verified' ? '#16a34a' : '#94a3b8',
          border: '2px solid #ffffff',
          title: verified,
        }} />
      </div>

      <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '0.25rem' }}>
          <p style={{ margin: 0, color: '#14532d', fontSize: '1.1rem', fontWeight: '700' }}>
            {fullName}
          </p>
          <p style={{ margin: '0.2rem 0 0', color: '#4b7c59', fontSize: '0.8rem' }}>
            {email}
          </p>
        </div>

        <div style={{ height: '1px', background: '#bbf7d0' }} />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div style={{
            background: '#f0fdf4', borderRadius: '8px',
            padding: '0.75rem', border: '1px solid #bbf7d0'
          }}>
            <p style={{ margin: '0 0 0.2rem', color: '#4b7c59', fontSize: '0.65rem',
              fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Member Since
            </p>
            <p style={{ margin: 0, color: '#14532d', fontSize: '0.8rem', fontWeight: '600' }}>
              {formattedDate}
            </p>
          </div>

          <div style={{
            background: '#f0fdf4', borderRadius: '8px',
            padding: '0.75rem', border: '1px solid #bbf7d0'
          }}>
            <p style={{ margin: '0 0 0.2rem', color: '#4b7c59', fontSize: '0.65rem',
              fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Email Status
            </p>
            <p style={{ margin: 0, fontSize: '0.8rem', fontWeight: '600',
              color: verified === 'Verified' ? '#16a34a' : '#94a3b8' }}>
              {verified}
            </p>
          </div>

          <div style={{
            background: '#f0fdf4', borderRadius: '8px',
            padding: '0.75rem', border: '1px solid #bbf7d0',
            gridColumn: '1 / -1'
          }}>
            <p style={{ margin: '0 0 0.2rem', color: '#4b7c59', fontSize: '0.65rem',
              fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Auth Provider
            </p>
            <p style={{ margin: 0, color: '#14532d', fontSize: '0.8rem', fontWeight: '600' }}>
              {googleId ? '🔗 Google OAuth' : '🔑 Email & Password'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function UserSearch({ searchInput, onSearch, onChange }) {
  return (
    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
      <input
        type="text"
        value={searchInput}
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && onSearch()}
        placeholder="Enter user email or ID..."
        style={{
          flex: 1, padding: '0.6rem 0.875rem',
          background: '#f0fdf4', border: '1px solid #bbf7d0',
          borderRadius: '6px', color: '#14532d',
          fontSize: '0.875rem', outline: 'none',
        }}
      />
      <button
        onClick={onSearch}
        disabled={!searchInput.trim()}
        style={{
          padding: '0.6rem 1.25rem',
          background: searchInput.trim() ? '#166534' : '#bbf7d0',
          border: 'none', borderRadius: '6px',
          color: searchInput.trim() ? '#ffffff' : '#4b7c59',
          fontSize: '0.875rem', fontWeight: '600',
          cursor: searchInput.trim() ? 'pointer' : 'not-allowed',
          transition: 'all 0.15s',
        }}
      >
        Search
      </button>
    </div>
  );
}

export default function UserProfileSearch() {
  const [searchInput, setSearchInput] = useState('');
  const [activeQuery, setActiveQuery] = useState(null);

  const isEmail = val => val.includes('@');

  const handleSearch = () => {
    if (!searchInput.trim()) return;
    const val = searchInput.trim();
    setActiveQuery({
      dimensions: [
        'UserProfile.id',
        'UserProfile.email',
        'UserProfile.full_name',
        'UserProfile.avatar_url',
        'UserProfile.email_verified',
        'UserProfile.google_id',
        'UserProfile.created_at',
      ],
      filters: [{
        member: isEmail(val) ? 'UserProfile.email' : 'UserProfile.id',
        operator: 'equals',
        values: [val],
      }],
      limit: 1,
    });
  };

  const { data, isLoading, error } = useCubeQuery(activeQuery);

  const user = data?.[0] || null;
  const notFound = activeQuery && !isLoading && !error && !user;

  return (
    <ChartWrapper title="User Lookup" subtitle="Search by email address or user ID">
      <UserSearch
        searchInput={searchInput}
        onSearch={handleSearch}
        onChange={setSearchInput}
      />

      {!activeQuery && (
        <div style={{
          padding: '3rem 1rem', textAlign: 'center',
          color: '#4b7c59', fontSize: '0.875rem'
        }}>
          Enter an email or user ID to look up a profile
        </div>
      )}

      {isLoading && (
        <div style={{
          padding: '3rem 1rem', textAlign: 'center',
          color: '#4b7c59', fontSize: '0.875rem'
        }}>
          Searching...
        </div>
      )}

      {error && (
        <div style={{
          padding: '1rem', background: '#fef2f2',
          borderRadius: '8px', color: '#dc2626', fontSize: '0.8rem'
        }}>
          {error?.message || 'Search failed'}
        </div>
      )}

      {notFound && (
        <div style={{
          padding: '3rem 1rem', textAlign: 'center',
          color: '#4b7c59', fontSize: '0.875rem'
        }}>
          No user found for <strong style={{ color: '#14532d' }}>{searchInput}</strong>
        </div>
      )}

      {user && <ProfileCard user={user} />}
    </ChartWrapper>
  );
}
