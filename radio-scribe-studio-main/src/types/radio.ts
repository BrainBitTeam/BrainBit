export interface WaveformParams {
  frequency_hz: number;
  bandwidth_hz: number;
  modulation?: string;
}

export interface RadioStatus {
  frequency_hz: number;
  bandwidth_hz: number;
  waveform: string;
  modulation: string;
  power_level: string;
  battery_percent: number;
  battery_voltage: number;
  members_count: number;
  errors: string[];
  last_wf_params: {
    WB: WaveformParams;
    NB: WaveformParams;
  };
  channel: number;
  volume: number;
  rx_only: boolean;
  led_on: boolean;
  gps_on: boolean;
}

export interface VoiceActivity {
  isUserSpeaking: boolean;
  isModelSpeaking: boolean;
  userTranscript: string;
  modelResponse: string;
}

export const DEFAULT_RADIO_STATUS: RadioStatus = {
  frequency_hz: 427e6,
  bandwidth_hz: 1e6,
  waveform: "WB",
  modulation: "QAM16",
  power_level: "high",
  battery_percent: 78,
  battery_voltage: 12.60,
  members_count: 5,
  errors: [],
  last_wf_params: {
    WB: { frequency_hz: 500e6, bandwidth_hz: 1e6, modulation: "QAM16" },
    NB: { frequency_hz: 50e6, bandwidth_hz: 25000 }
  },
  channel: 1,
  volume: 10,
  rx_only: true,
  led_on: false,
  gps_on: false
};

// Format helpers
export function formatFrequency(hz: number): string {
  return (hz / 1e6).toFixed(3);
}

export function formatBandwidth(hz: number): string {
  if (hz >= 1e6) {
    return (hz / 1e6).toFixed(1) + " MHz";
  }
  return (hz / 1e3).toFixed(1) + " kHz";
}

export function formatVoltage(v: number): string {
  return v.toFixed(2);
}
