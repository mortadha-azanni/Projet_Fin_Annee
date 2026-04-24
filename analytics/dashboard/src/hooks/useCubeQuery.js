import { useState, useEffect } from 'react';
import cubejsApi from '../cubejsClient';

export function useCubeQuery(query) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!query) return;
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    cubejsApi.load(query)
      .then(result => {
        if (!cancelled) {
          setData(result.tablePivot());
          setIsLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err);
          setIsLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [JSON.stringify(query)]);

  return { data, isLoading, error };
}
