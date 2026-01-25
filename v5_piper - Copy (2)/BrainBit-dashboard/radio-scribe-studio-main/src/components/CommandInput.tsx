import { useState, KeyboardEvent } from "react";
import { Terminal } from "lucide-react";

interface CommandInputProps {
  onCommand: (command: string) => void;
  lastResult?: string;
}

export function CommandInput({ onCommand, lastResult }: CommandInputProps) {
  const [command, setCommand] = useState("");

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && command.trim()) {
      onCommand(command.trim());
      setCommand("");
    }
  };

  return (
    <div className="panel-card">
      <div className="panel-label flex items-center gap-2">
        <Terminal className="w-4 h-4" />
        Command Input
      </div>
      <div className="space-y-2">
        <input
          type="text"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter command (e.g., set frequency to 500)"
          className="w-full bg-background border border-border rounded px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        {lastResult && (
          <p className={`text-xs font-mono ${lastResult.startsWith("Error") ? "text-destructive" : "text-primary"}`}>
            → {lastResult}
          </p>
        )}
        <p className="text-xs text-muted-foreground">
          Commands: set [field] to [value] | what's/show/get [field] | Fields: frequency, channel, sensitivity
        </p>
      </div>
    </div>
  );
}
