import { useRef, useEffect } from "react";

interface TranscriptionDisplayProps {
  text: string;
  isRecording: boolean;
}

export function TranscriptionDisplay({ text, isRecording }: TranscriptionDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [text]);

  return (
    <div className="panel-card h-64 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <span className="panel-label mb-0">Transcription Output</span>
        {isRecording && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-destructive blink" />
            <span className="text-xs uppercase tracking-wider text-destructive">Live</span>
          </div>
        )}
      </div>
      
      <div
        ref={containerRef}
        className="panel-display flex-1 overflow-y-auto"
      >
        {text ? (
          <p className="transcription-text text-foreground">{text}</p>
        ) : (
          <p className="text-muted-foreground italic">
            {isRecording ? "Listening..." : "Press REC to start transcription"}
          </p>
        )}
      </div>
    </div>
  );
}
