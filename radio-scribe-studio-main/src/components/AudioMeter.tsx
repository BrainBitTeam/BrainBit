interface AudioMeterProps {
  level: number; // 0-100
  label?: string;
}

export function AudioMeter({ level, label }: AudioMeterProps) {
  const segments = 20;
  const activeSegments = Math.floor((level / 100) * segments);

  return (
    <div className="space-y-2">
      {label && (
        <div className="flex justify-between items-center">
          <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
          <span className="text-xs font-mono text-primary">{level}%</span>
        </div>
      )}
      <div className="flex gap-0.5 h-5 items-end">
        {Array.from({ length: segments }).map((_, i) => {
          const isActive = i < activeSegments;
          const isWarning = i >= segments * 0.7;
          const isDanger = i >= segments * 0.9;
          
          return (
            <div
              key={i}
              className={`flex-1 rounded-sm transition-all duration-75 ${
                isActive
                  ? isDanger
                    ? "bg-destructive shadow-[0_0_6px_hsl(var(--destructive))]"
                    : isWarning
                    ? "bg-indicator-warning shadow-[0_0_6px_hsl(var(--indicator-warning))]"
                    : "bg-indicator-active shadow-[0_0_6px_hsl(var(--indicator-active))]"
                  : "bg-muted"
              }`}
              style={{ height: isActive ? "100%" : "40%" }}
            />
          );
        })}
      </div>
    </div>
  );
}

interface WaveformDisplayProps {
  bars: number[];
  isActive: boolean;
}

export function WaveformDisplay({ bars, isActive }: WaveformDisplayProps) {
  return (
    <div className="flex items-center justify-center gap-1 h-24 px-4">
      {bars.map((height, i) => (
        <div
          key={i}
          className={`waveform-bar w-1.5 transition-all duration-75 ${
            isActive ? "opacity-100" : "opacity-30"
          }`}
          style={{ height: `${isActive ? height : 10}%` }}
        />
      ))}
    </div>
  );
}
