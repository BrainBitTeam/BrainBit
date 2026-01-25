import { Battery, BatteryLow, BatteryMedium, BatteryFull, BatteryWarning } from 'lucide-react';

interface BatteryIndicatorProps {
  percent: number;
  voltage?: number;
}

export function BatteryIndicator({ percent }: BatteryIndicatorProps) {
  const getBatteryIcon = () => {
    if (percent <= 10) return <BatteryWarning className="w-6 h-6 text-destructive" />;
    if (percent <= 25) return <BatteryLow className="w-6 h-6 text-indicator-warning" />;
    if (percent <= 60) return <BatteryMedium className="w-6 h-6 text-indicator-active" />;
    return <BatteryFull className="w-6 h-6 text-indicator-active" />;
  };

  const getBarColor = () => {
    if (percent <= 10) return 'bg-destructive';
    if (percent <= 25) return 'bg-indicator-warning';
    return 'bg-indicator-active';
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        {getBatteryIcon()}
        <div className="text-right">
          <span className="panel-value text-lg">{percent}%</span>
        </div>
      </div>
      <div className="h-3 bg-muted rounded-sm overflow-hidden">
        <div
          className={`h-full ${getBarColor()} transition-all duration-300`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
