import { Wifi, WifiOff, AlertTriangle } from 'lucide-react';

interface StatusIndicatorsProps {
  isConnected: boolean;
  errors: string[];
}

export function StatusIndicators({
  isConnected,
  errors
}: StatusIndicatorsProps) {
  return (
    <div className="space-y-4">
      {/* Connection Status */}
      <div className="flex items-center gap-2">
        {isConnected ? (
          <Wifi className="w-4 h-4 text-indicator-active" />
        ) : (
          <WifiOff className="w-4 h-4 text-muted-foreground" />
        )}
        <span className="text-xs uppercase tracking-wider text-muted-foreground">
          {isConnected ? 'Connected' : 'Demo Mode'}
        </span>
      </div>


      {/* Error Display */}
      {errors.length > 0 && (
        <div className="mt-2 p-2 bg-destructive/10 border border-destructive/30 rounded">
          <div className="flex items-center gap-2 text-destructive text-xs">
            <AlertTriangle className="w-4 h-4" />
            <span>{errors.join(', ')}</span>
          </div>
        </div>
      )}
    </div>
  );
}
