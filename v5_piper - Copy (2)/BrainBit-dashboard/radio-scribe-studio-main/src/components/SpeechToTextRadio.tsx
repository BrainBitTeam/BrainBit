import { RadioPanel, DisplayValue, Indicator } from "./RadioPanel";
import { BatteryIndicator } from "./BatteryIndicator";
import { StatusIndicators } from "./StatusIndicators";
import { MembersDisplay } from "./MembersDisplay";
import { useRadioStatus } from "@/hooks/useRadioStatus";
import { useVoiceActivity } from "@/hooks/useVoiceActivity";
import { formatFrequency, formatBandwidth } from "@/types/radio";
import { DASHBOARD_CONFIG } from "@/config/dashboard";
import { Radio, Volume2, Zap, MapPin, Lightbulb, Radio as RadioIcon, Users } from "lucide-react";

export function SpeechToTextRadio() {
  // Connect to ZCU102 JSON endpoints using config
  const { status, isConnected, lastUpdate } = useRadioStatus({
    endpoint: DASHBOARD_CONFIG.radioStatusEndpoint,
    pollInterval: DASHBOARD_CONFIG.radioStatusPollInterval
  });

  const { activity } = useVoiceActivity({
    endpoint: DASHBOARD_CONFIG.voiceActivityEndpoint,
    pollInterval: DASHBOARD_CONFIG.voiceActivityPollInterval
  });

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
              errors={status.errors}
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {/* Waveform Type */}
            <RadioPanel label="Waveform">
              <div className="panel-display">
                <span className="panel-value text-lg">
                  {status.waveform === 'WB' ? 'WB (Wideband)' : 'NB (Narrowband)'}
                </span>
              </div>
            </RadioPanel>

            {/* Frequency */}
            <RadioPanel label="Frequency (MHz)">
              <DisplayValue value={formatFrequency(status.frequency_hz)} unit="MHz" size="lg" />
            </RadioPanel>

            {/* Bandwidth */}
            <RadioPanel label="Bandwidth">
              <div className="panel-display">
                <span className="panel-value text-lg">{formatBandwidth(status.bandwidth_hz)}</span>
              </div>
            </RadioPanel>

            {/* Channel */}
            <RadioPanel label="Channel">
              <DisplayValue value={status.channel} size="lg" />
            </RadioPanel>

            {/* Power Level */}
            <RadioPanel label="Power Level">
              <div className="flex items-center gap-2">
                <Zap className={`w-4 h-4 ${status.power_level === 'high' ? 'text-primary' : 'text-muted-foreground'}`} />
                <div className="panel-display flex-1">
                  <span className="panel-value text-lg">{status.power_level.toUpperCase()}</span>
                </div>
              </div>
            </RadioPanel>

            {/* Volume */}
            <RadioPanel label="Volume">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-primary" />
                <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${(status.volume / 10) * 100}%` }}
                  />
                </div>
                <span className="text-lg font-mono text-primary w-10 text-right">{status.volume}</span>
              </div>
            </RadioPanel>

            {/* Battery */}
            <RadioPanel label="Battery">
              <BatteryIndicator
                percent={status.battery_percent}
              />
            </RadioPanel>
          </div>
        </div>

        {/* Status Indicators Panel */}
        <div className="panel-card">
          <div className="panel-label mb-4">System Status</div>
          <div className="flex flex-wrap items-center gap-4">
            <Indicator
              label="RX Only"
              active={status.rx_only}
              icon={<RadioIcon className="w-3 h-3" />}
            />
            <Indicator
              label="LED"
              active={status.led_on}
              icon={<Lightbulb className="w-3 h-3" />}
            />
            <Indicator
              label="GPS"
              active={status.gps_on}
              icon={<MapPin className="w-3 h-3" />}
            />
          </div>
        </div>

        {/* Members Panel */}
        <div className="panel-card">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-4 h-4 text-muted-foreground" />
            <span className="panel-label mb-0">Network Members ({status.members?.length || 0})</span>
          </div>
          {status.members && status.members.length > 0 ? (
            <MembersDisplay members={status.members} />
          ) : (
            <p className="text-muted-foreground text-sm">No members connected</p>
          )}
        </div>


      </div>
    </div>
  );
}
