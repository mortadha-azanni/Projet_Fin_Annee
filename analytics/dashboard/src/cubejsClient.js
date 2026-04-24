import cubejs from '@cubejs-client/core';

const AUTH_KEY = 'searchily_analytics_auth';

function getToken() {
  try {
    const stored = localStorage.getItem(AUTH_KEY);
    if (stored) {
      const { token } = JSON.parse(stored);
      return token || '';
    }
  } catch {
    return '';
  }
  return import.meta.env.VITE_CUBEJS_TOKEN || '';
}

const cubejsApi = cubejs(
  () => getToken(),
  { apiUrl: import.meta.env.VITE_CUBEJS_API_URL || '/cubejs-api/v1' }
);

export default cubejsApi;
