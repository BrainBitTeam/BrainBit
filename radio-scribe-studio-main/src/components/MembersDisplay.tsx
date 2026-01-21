import { Wifi } from 'lucide-react';
import { Member } from '@/types/radio';

interface MembersDisplayProps {
  members: Member[];
}

function getRssiColor(rssi: number): string {
  // RSSI ranges from -105 (very weak) to +30 (excellent)
  if (rssi >= 0) return 'text-indicator-active';
  if (rssi >= -40) return 'text-primary';
  if (rssi >= -70) return 'text-indicator-warning';
  return 'text-destructive';
}

function getRssiBarWidth(rssi: number): number {
  // Map RSSI from -105..+30 to 0..100%
  const minRssi = -105;
  const maxRssi = 30;
  const clamped = Math.max(minRssi, Math.min(maxRssi, rssi));
  return ((clamped - minRssi) / (maxRssi - minRssi)) * 100;
}

function getRssiBarColor(rssi: number): string {
  // RSSI ranges from -105 (very weak) to +30 (excellent)
  if (rssi >= 0) return 'bg-indicator-active';
  if (rssi >= -40) return 'bg-primary';
  if (rssi >= -70) return 'bg-indicator-warning';
  return 'bg-destructive';
}

export function MembersDisplay({ members }: MembersDisplayProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {members.map((member) => {
        const iconColor = getRssiColor(member.rssi);
        const barWidth = getRssiBarWidth(member.rssi);
        const barColor = getRssiBarColor(member.rssi);

        return (
          <div
            key={member.id}
            className="flex items-center gap-3 p-3 rounded bg-secondary/50 border border-border"
          >
            <div className={iconColor}>
              <Wifi className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-sm text-primary">ID: {member.id}</span>
                <span className="text-xs text-muted-foreground">{member.rssi} dBm</span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full ${barColor} transition-all duration-300`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
