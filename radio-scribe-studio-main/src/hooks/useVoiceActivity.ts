import { useState, useEffect, useCallback } from 'react';
import { VoiceActivity } from '@/types/radio';

interface UseVoiceActivityOptions {
  endpoint?: string;
  pollInterval?: number;
}

export function useVoiceActivity(options: UseVoiceActivityOptions = {}) {
  const { 
    endpoint = '/api/voice-activity.json', 
    pollInterval = 100 
  } = options;

  const [activity, setActivity] = useState<VoiceActivity>({
    isUserSpeaking: false,
    isModelSpeaking: false,
    userTranscript: '',
    modelResponse: ''
  });

  const [waveformBars, setWaveformBars] = useState<number[]>(Array(32).fill(10));
  const [audioLevel, setAudioLevel] = useState(0);

  const fetchActivity = useCallback(async () => {
    try {
      const response = await fetch(endpoint, {
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache' }
      });
      
      if (!response.ok) return;
      
      const data: VoiceActivity = await response.json();
      setActivity(data);
    } catch {
      // Silent fail - simulated mode
    }
  }, [endpoint]);

  // Simulate waveform when speaking
  useEffect(() => {
    const isSpeaking = activity.isUserSpeaking || activity.isModelSpeaking;
    
    if (!isSpeaking) {
      setAudioLevel(0);
      setWaveformBars(Array(32).fill(10));
      return;
    }

    const interval = setInterval(() => {
      const baseLevel = activity.isUserSpeaking ? 60 : 45;
      const variation = Math.random() * 40;
      setAudioLevel(Math.min(100, Math.floor(baseLevel + variation)));
      
      setWaveformBars(prev => 
        prev.map(() => Math.random() * 80 + 10)
      );
    }, 100);

    return () => clearInterval(interval);
  }, [activity.isUserSpeaking, activity.isModelSpeaking]);

  useEffect(() => {
    fetchActivity();
    const interval = setInterval(fetchActivity, pollInterval);
    return () => clearInterval(interval);
  }, [fetchActivity, pollInterval]);

  return {
    activity,
    waveformBars,
    isSpeaking: activity.isUserSpeaking || activity.isModelSpeaking
  };
}
