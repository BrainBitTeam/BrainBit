import { useState, useEffect } from "react";
import { RadioPanel, DisplayValue, Indicator } from "./RadioPanel";
import { WaveformDisplay } from "./AudioMeter";
import { BatteryIndicator } from "./BatteryIndicator";
import { StatusIndicators } from "./StatusIndicators";
import { VoiceTranscriptDisplay } from "./VoiceTranscriptDisplay";
import { useRadioStatus } from "@/hooks/useRadioStatus";
import { useVoiceActivity } from "@/hooks/useVoiceActivity";
import { formatFrequency, formatBandwidth } from "@/types/radio";
import { DASHBOARD_CONFIG } from "@/config/dashboard";
import { Radio, Activity, Volume2, Zap, MapPin, Lightbulb, Radio as RadioIcon, Edit2 } from "lucide-react";

export function SpeechToTextRadio() {
  // Connect to ZCU102 JSON endpoints using config
  const { status, isConnected, lastUpdate, updateStatus } = useRadioStatus({
    endpoint: DASHBOARD_CONFIG.radioStatusEndpoint,
    pollInterval: DASHBOARD_CONFIG.radioStatusPollInterval
  });

  const { activity, waveformBars, isSpeaking } = useVoiceActivity({
    endpoint: DASHBOARD_CONFIG.voiceActivityEndpoint,
    pollInterval: DASHBOARD_CONFIG.voiceActivityPollInterval
  });

  // Demo mode simulation when not connected
  const [demoWaveform, setDemoWaveform] = useState<number[]>(Array(32).fill(10));

  useEffect(() => {
    if (isConnected) return;

    // Simulate periodic activity in demo mode
    const interval = setInterval(() => {
      const shouldAnimate = Math.random() > 0.7;
      if (shouldAnimate) {
        setDemoWaveform(prev => prev.map(() => Math.random() * 80 + 10));
      } else {
        setDemoWaveform(prev => prev.map(v => Math.max(10, v * 0.9)));
      }
    }, 150);

    return () => clearInterval(interval);
  }, [isConnected]);

  const displayWaveform = isConnected ? waveformBars : demoWaveform;
  const displayIsSpeaking = isConnected ? isSpeaking : demoWaveform.some(v => v > 40);

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <header className="text-center space-y-2">
          <div className="flex items-center justify-center gap-3">
            <Radio className="w-8 h-8 text-primary" />
            <h1 className="text-3xl md:text-4xl font-bold font-display tracking-wide text-foreground">
              ZCU102 RADIO CONTROL
            </h1>
          </div>
          <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
            Voice-Controlled Radio Dashboard
          </p>
          {lastUpdate && (
            <p className="text-xs text-muted-foreground">
              Last update: {lastUpdate.toLocaleTimeString()}
            </p>
          )}
        </header>

        {/* Main Status Panel */}
        <div className="panel-card">
          <div className="flex items-center justify-between mb-6">
            <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
              Radio Parameters
            </span>
            <StatusIndicators
              isConnected={isConnected}
              membersCount={status.members_count}
              errors={status.errors}
              isUserSpeaking={activity.isUserSpeaking}
              isModelSpeaking={activity.isModelSpeaking}
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {/* Waveform Type - First so bandwidth/freq options update accordingly */}
            <RadioPanel label="Waveform">
              <select
                value={status.waveform}
                onChange={(e) => updateStatus({ waveform: e.target.value })}
                className="w-full bg-secondary border border-border rounded px-3 py-2 text-lg font-mono text-primary focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="WB">WB (Wideband)</option>
                <option value="NB">NB (Narrowband)</option>
              </select>
            </RadioPanel>

            {/* Frequency */}
            <RadioPanel label={`Frequency (MHz) ${status.waveform === 'NB' ? '[30-100, 200-600]' : '[200-600]'}`}>
              <input
                type="number"
                value={status.frequency_hz / 1000000}
                onChange={(e) => updateStatus({ frequency_hz: parseFloat(e.target.value) * 1000000 })}
                className="w-full bg-secondary border border-border rounded px-3 py-2 text-2xl font-mono text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                step="1"
                min={status.waveform === 'NB' ? 30 : 200}
                max="600"
              />
            </RadioPanel>

            {/* Bandwidth - options depend on waveform */}
            <RadioPanel label="Bandwidth">
              <select
                value={status.bandwidth_hz}
                onChange={(e) => updateStatus({ bandwidth_hz: parseFloat(e.target.value) })}
                className="w-full bg-secondary border border-border rounded px-3 py-2 text-lg font-mono text-primary focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {status.waveform === 'NB' ? (
                  <>
                    <option value="25000">25 kHz</option>
                    <option value="50000">50 kHz</option>
                  </>
                ) : (
                  <>
                    <option value="500000">0.5 MHz</option>
                    <option value="1000000">1 MHz</option>
                    <option value="2000000">2 MHz</option>
                    <option value="4000000">4 MHz</option>
                  </>
                )}
              </select>
            </RadioPanel>

            {/* Channel */}
            <RadioPanel label="Channel">
              <input
                type="number"
                value={status.channel}
                onChange={(e) => updateStatus({ channel: parseInt(e.target.value) })}
                className="w-full bg-secondary border border-border rounded px-3 py-2 text-2xl font-mono text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                min="1"
                max="200"
              />
            </RadioPanel>

            {/* Power Level */}
            <RadioPanel label="Power Level">
              <div className="flex items-center gap-2">
                <Zap className={`w-4 h-4 ${status.power_level === 'high' ? 'text-primary' : 'text-muted-foreground'}`} />
                <select
                  value={status.power_level}
                  onChange={(e) => updateStatus({ power_level: e.target.value })}
                  className="flex-1 bg-secondary border border-border rounded px-3 py-2 text-lg font-mono text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="low">LOW</option>
                  <option value="medium">MEDIUM</option>
                  <option value="high">HIGH</option>
                </select>
              </div>
            </RadioPanel>

            {/* Volume */}
            <RadioPanel label="Volume">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-primary" />
                <input
                  type="range"
                  value={status.volume}
                  onChange={(e) => updateStatus({ volume: parseInt(e.target.value) })}
                  className="flex-1 accent-primary"
                  min="1"
                  max="10"
                />
                <span className="text-lg font-mono text-primary w-10 text-right">{status.volume}</span>
              </div>
            </RadioPanel>

            {/* Battery */}
            <RadioPanel label="Battery">
              <BatteryIndicator
                percent={status.battery_percent}
                voltage={status.battery_voltage}
              />
            </RadioPanel>
          </div>
        </div>

        {/* Status Toggles Panel */}
        <div className="panel-card">
          <div className="panel-label mb-4">System Status (click to toggle)</div>
          <div className="flex flex-wrap items-center gap-4">
            <button
              onClick={() => updateStatus({ rx_only: !status.rx_only })}
              className="focus:outline-none focus:ring-2 focus:ring-primary rounded transition-transform hover:scale-105"
            >
              <Indicator
                label="RX Only"
                active={status.rx_only}
                icon={<RadioIcon className="w-3 h-3" />}
              />
            </button>
            <button
              onClick={() => updateStatus({ led_on: !status.led_on })}
              className="focus:outline-none focus:ring-2 focus:ring-primary rounded transition-transform hover:scale-105"
            >
              <Indicator
                label="LED"
                active={status.led_on}
                icon={<Lightbulb className="w-3 h-3" />}
              />
            </button>
            <button
              onClick={() => updateStatus({ gps_on: !status.gps_on })}
              className="focus:outline-none focus:ring-2 focus:ring-primary rounded transition-transform hover:scale-105"
            >
              <Indicator
                label="GPS"
                active={status.gps_on}
                icon={<MapPin className="w-3 h-3" />}
              />
            </button>
          </div>
        </div>

        {/* Waveform Display */}
        <div className="panel-card">
          <div className="flex items-center gap-2 mb-2">
            <Activity className={`w-4 h-4 ${displayIsSpeaking ? 'text-primary blink' : 'text-muted-foreground'}`} />
            <div className="panel-label">Audio Waveform</div>
          </div>
          <div className="panel-display">
            <WaveformDisplay bars={displayWaveform} isActive={displayIsSpeaking} />
          </div>
        </div>

        {/* Voice Transcript Display */}
        <div className="panel-card">
          <div className="panel-label mb-4">Voice Interaction</div>
          <VoiceTranscriptDisplay
            userTranscript={activity.userTranscript}
            modelResponse={activity.modelResponse}
            isUserSpeaking={activity.isUserSpeaking}
            isModelSpeaking={activity.isModelSpeaking}
          />
        </div>

        {/* Quick Status Bar */}
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary border border-border">
            <span className="text-xs uppercase tracking-wider text-muted-foreground">CH:</span>
            <span className="panel-value text-sm">{status.channel}</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary border border-border">
            <span className="text-xs uppercase tracking-wider text-muted-foreground">Freq:</span>
            <span className="panel-value text-sm">{formatFrequency(status.frequency_hz)} MHz</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary border border-border">
            <span className="text-xs uppercase tracking-wider text-muted-foreground">BW:</span>
            <span className="panel-value text-sm">{formatBandwidth(status.bandwidth_hz)}</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary border border-border">
            <span className="text-xs uppercase tracking-wider text-muted-foreground">WF:</span>
            <span className="panel-value text-sm">{status.waveform}</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary border border-border">
            <span className="text-xs uppercase tracking-wider text-muted-foreground">PWR:</span>
            <span className="panel-value text-sm">{status.power_level.toUpperCase()}</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary border border-border">
            <span className="text-xs uppercase tracking-wider text-muted-foreground">VOL:</span>
            <span className="panel-value text-sm">{status.volume}</span>
          </div>
        </div>

      </div>
    </div>
  );
}
