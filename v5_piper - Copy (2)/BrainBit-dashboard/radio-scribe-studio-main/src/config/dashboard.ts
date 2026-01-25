/**
 * Dashboard Configuration
 * 
 * Modify these paths to match your ZCU102 JSON endpoints.
 * The dashboard will poll these endpoints for real-time updates.
 */

export const DASHBOARD_CONFIG = {
  // Path to the radio status JSON file (served by Vite plugin from local file)
  // This file should contain: frequency_hz, bandwidth_hz, waveform, modulation, battery_percent, battery_voltage, members_count, errors
  radioStatusEndpoint: '/radio-status.json',

  // How often to poll the radio status (in milliseconds)
  radioStatusPollInterval: 500,

  // Path to the voice activity JSON file
  // This file should contain: isUserSpeaking, isModelSpeaking, userTranscript, modelResponse
  voiceActivityEndpoint: '/voice-activity.json',

  // How often to poll the voice activity (in milliseconds)
  voiceActivityPollInterval: 100,
};
