import { Wifi, WifiOff, Users, AlertTriangle } from 'lucide-react';
import { Indicator } from './RadioPanel';

interface StatusIndicatorsProps {
  isConnected: boolean;
  membersCount: number;
  errors: string[];
  isUserSpeaking: boolean;
  isModelSpeaking: boolean;
}

export function StatusIndicators({ 
  isConnected, 
  membersCount, 
  errors,
  isUserSpeaking,
  isModelSpeaking
}: StatusIndicatorsProps) {
  return (
    <div className="space-y-4">
      {/* Connection Status */}
      <div className="flex items-center justify-between">
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
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-muted-foreground" />
          <span className="panel-value text-sm">{membersCount}</span>
        </div>
      </div>

      {/* Activity Indicators */}
      <div className="flex flex-wrap gap-4">
        <Indicator label="RX" active={isUserSpeaking} variant="success" />
        <Indicator label="TX" active={isModelSpeaking} variant="success" />
        <Indicator label="ERR" active={errors.length > 0} variant="error" />
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
