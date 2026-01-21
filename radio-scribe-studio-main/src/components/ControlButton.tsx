import { ReactNode } from "react";

interface ControlButtonProps {
  children: ReactNode;
  active?: boolean;
  onClick?: () => void;
  variant?: "default" | "primary" | "danger";
  disabled?: boolean;
}

export function ControlButton({
  children,
  active = false,
  onClick,
  variant = "default",
  disabled = false,
}: ControlButtonProps) {
  const variantClasses = {
    default: active ? "active" : "",
    primary: "bg-primary text-primary-foreground hover:bg-primary/90",
    danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`control-button ${variantClasses[variant]} ${
        disabled ? "opacity-50 cursor-not-allowed" : ""
      }`}
    >
      {children}
    </button>
  );
}

interface RecordButtonProps {
  isRecording: boolean;
  onClick: () => void;
}

export function RecordButton({ isRecording, onClick }: RecordButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`record-button ${isRecording ? "recording" : ""}`}
      aria-label={isRecording ? "Stop recording" : "Start recording"}
    >
      {isRecording ? (
        <div className="w-6 h-6 bg-destructive-foreground rounded-sm" />
      ) : (
        <div className="w-6 h-6 bg-destructive-foreground rounded-full" />
      )}
    </button>
  );
}
