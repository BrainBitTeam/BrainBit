import { useState, useEffect, useCallback } from 'react';
import { RadioStatus, DEFAULT_RADIO_STATUS } from '@/types/radio';

interface UseRadioStatusOptions {
  endpoint?: string;
  pollInterval?: number;
}

export function useRadioStatus(options: UseRadioStatusOptions = {}) {
  const {
    endpoint = '/api/radio-status.json',
    pollInterval = 500
  } = options;

  const [status, setStatus] = useState<RadioStatus>(DEFAULT_RADIO_STATUS);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(endpoint, {
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache' }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: RadioStatus = await response.json();
      setStatus(data);
      setIsConnected(true);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      // If fetch fails, we're in demo mode or disconnected
      setIsConnected(false);
      setError(err instanceof Error ? err.message : 'Connection failed');
    }
  }, [endpoint]);

  const updateStatus = useCallback(async (updates: Partial<RadioStatus>) => {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Immediately update local state
      setStatus(prev => ({ ...prev, ...updates }));
      setLastUpdate(new Date());
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
      return false;
    }
  }, [endpoint]);

  useEffect(() => {
    // Initial fetch
    fetchStatus();

    // Poll for updates
    const interval = setInterval(fetchStatus, pollInterval);

    return () => clearInterval(interval);
  }, [fetchStatus, pollInterval]);

  return {
    status,
    isConnected,
    lastUpdate,
    error,
    refresh: fetchStatus,
    updateStatus
  };
}
