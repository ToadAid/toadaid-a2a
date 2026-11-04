import React from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  tone?: "primary" | "success" | "warning" | "danger" | "gold";
  trend?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  icon,
  tone = "primary",
  trend,
}) => {
  let accentColor = "var(--color-jade)";
  let bgGlow = "rgba(20, 184, 166, 0.08)";
  if (tone === "gold") {
    accentColor = "var(--color-gold)";
    bgGlow = "var(--color-gold-bg)";
  } else if (tone === "warning") {
    accentColor = "var(--color-warning)";
    bgGlow = "var(--color-warning-bg)";
  } else if (tone === "danger") {
    accentColor = "var(--color-danger)";
    bgGlow = "var(--color-danger-bg)";
  }

  return (
    <div
      className="rounded-xl p-5 transition-all relative overflow-hidden"
      style={{
        background: "var(--color-surface-card)",
        border: "1px solid var(--color-border)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-dim)]">
          {label}
        </span>
        {icon && (
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: bgGlow, color: accentColor }}
            aria-hidden="true"
          >
            {icon}
          </div>
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold font-mono text-[var(--color-text-primary)]">
          {value}
        </span>
        {trend && (
          <span className="text-xs font-medium text-[var(--color-jade)]">
            {trend}
          </span>
        )}
      </div>
      {subtext && (
        <p className="text-xs text-[var(--color-text-muted)] mt-1.5 leading-normal">
          {subtext}
        </p>
      )}
    </div>
  );
};
