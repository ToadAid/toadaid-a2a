import React from "react";
import type { RegistrationStatus } from "../../types/observatory";

interface StatusDonutChartProps {
  data: Record<RegistrationStatus, number>;
  total: number;
}

export const StatusDonutChart: React.FC<StatusDonutChartProps> = ({ data, total }) => {
  const segments: { key: RegistrationStatus; label: string; count: number; color: string }[] = [
    { key: "registered", label: "Registered", count: data.registered || 0, color: "var(--color-success)" },
    { key: "suspended", label: "Suspended", count: data.suspended || 0, color: "var(--color-warning)" },
    { key: "revoked", label: "Revoked", count: data.revoked || 0, color: "var(--color-danger)" },
    { key: "unknown", label: "Unknown / Unverified", count: (data.unknown || 0) + (data.unregistered || 0), color: "var(--color-text-dim)" },
  ];

  // Calculate SVG stroke dashes
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  let accumulatedAngle = 0;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6" role="region" aria-label="Registration Status Breakdown">
      {/* Donut graphic */}
      <div className="relative w-36 h-36 shrink-0 flex items-center justify-center">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90 transform" aria-hidden="true">
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth="12"
          />
          {segments.map((seg) => {
            if (seg.count === 0 || total === 0) return null;
            const strokeDasharray = `${(seg.count / total) * circumference} ${circumference}`;
            const strokeDashoffset = -accumulatedAngle;
            accumulatedAngle += (seg.count / total) * circumference;

            return (
              <circle
                key={seg.key}
                cx="50"
                cy="50"
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth="12"
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                className="transition-all duration-500 ease-out"
              />
            );
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
          <span className="text-xl font-bold font-mono text-[var(--color-text-primary)]">
            {total}
          </span>
          <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-dim)]">
            Agents
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex-1 grid grid-cols-2 gap-3 w-full">
        {segments.map((seg) => {
          const pct = total > 0 ? Math.round((seg.count / total) * 100) : 0;
          return (
            <div key={seg.key} className="flex items-center gap-2 p-2 rounded-lg bg-[var(--color-surface-card-hover)] border border-[var(--color-border-subtle)]">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ background: seg.color }}
                aria-hidden="true"
              />
              <div className="overflow-hidden">
                <div className="text-xs font-semibold text-[var(--color-text-primary)] truncate">
                  {seg.label}
                </div>
                <div className="text-[11px] font-mono text-[var(--color-text-muted)]">
                  {seg.count} ({pct}%)
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
