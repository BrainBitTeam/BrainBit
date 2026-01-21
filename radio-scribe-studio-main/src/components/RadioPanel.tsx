import { ReactNode } from "react";

interface RadioPanelProps {
  label: string;
  children: ReactNode;
  className?: string;
}

export function RadioPanel({ label, children, className = "" }: RadioPanelProps) {
  return (
    <div className={`panel-card ${className}`}>
      <div className="panel-label">{label}</div>
      {children}
    </div>
  );
}

interface DisplayValueProps {
  value: string | number;
  unit?: string;
  size?: "sm" | "md" | "lg";
}

export function DisplayValue({ value, unit, size = "md" }: DisplayValueProps) {
  const sizeClasses = {
    sm: "text-lg",
    md: "text-2xl",
    lg: "text-3xl",
  };

  return (
    <div className="panel-display flex items-baseline gap-2">
      <span className={`panel-value ${sizeClasses[size]}`}>{value}</span>
      {unit && <span className="text-muted-foreground text-sm">{unit}</span>}
    </div>
  );
}

interface IndicatorProps {
  label: string;
  active: boolean;
  variant?: "success" | "warning" | "error";
  icon?: ReactNode;
}

export function Indicator({ label, active, variant = "success", icon }: IndicatorProps) {
  const variantClasses = {
    success: active ? "indicator-active" : "indicator-inactive",
    warning: active ? "indicator-warning" : "indicator-inactive",
    error: active ? "bg-destructive" : "indicator-inactive",
  };

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-secondary/50 border border-border">
      {icon && <span className={active ? "text-primary" : "text-muted-foreground"}>{icon}</span>}
      <div className={`indicator-light ${variantClasses[variant]}`} />
      <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className={`text-xs font-medium ${active ? "text-primary" : "text-muted-foreground"}`}>
        {active ? "ON" : "OFF"}
      </span>
    </div>
  );
}
