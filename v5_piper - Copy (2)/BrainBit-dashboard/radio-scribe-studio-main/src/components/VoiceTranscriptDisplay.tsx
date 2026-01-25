import { Mic, Bot } from 'lucide-react';

interface VoiceTranscriptDisplayProps {
  userTranscript: string;
  modelResponse: string;
  isUserSpeaking: boolean;
  isModelSpeaking: boolean;
}

export function VoiceTranscriptDisplay({ 
  userTranscript, 
  modelResponse,
  isUserSpeaking,
  isModelSpeaking
}: VoiceTranscriptDisplayProps) {
  return (
    <div className="space-y-3">
      {/* User Input */}
      <div className={`p-3 rounded border transition-all duration-300 ${
        isUserSpeaking 
          ? 'border-primary bg-primary/5' 
          : 'border-border bg-secondary/30'
      }`}>
        <div className="flex items-center gap-2 mb-2">
          <Mic className={`w-4 h-4 ${isUserSpeaking ? 'text-primary blink' : 'text-muted-foreground'}`} />
          <span className="text-xs uppercase tracking-wider text-muted-foreground">User Input</span>
        </div>
        <p className="text-sm text-foreground font-mono min-h-[1.5em]">
          {userTranscript || <span className="text-muted-foreground italic">Waiting for voice input...</span>}
        </p>
      </div>

      {/* Model Response */}
      <div className={`p-3 rounded border transition-all duration-300 ${
        isModelSpeaking 
          ? 'border-indicator-active bg-indicator-active/5' 
          : 'border-border bg-secondary/30'
      }`}>
        <div className="flex items-center gap-2 mb-2">
          <Bot className={`w-4 h-4 ${isModelSpeaking ? 'text-indicator-active blink' : 'text-muted-foreground'}`} />
          <span className="text-xs uppercase tracking-wider text-muted-foreground">System Response</span>
        </div>
        <p className="text-sm text-foreground font-mono min-h-[1.5em]">
          {modelResponse || <span className="text-muted-foreground italic">No response yet...</span>}
        </p>
      </div>
    </div>
  );
}
