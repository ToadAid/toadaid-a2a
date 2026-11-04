import React from "react";
import type { RegistrationStatus, EvidenceClass, ParticipationScope } from "../../types/observatory";
import { CheckCircleIcon, AlertTriangleIcon, AlertOctagonIcon, InfoIcon, ShieldIcon } from "./Icons";

interface BadgeProps {
  label?: string;
  size?: "sm" | "md";
  className?: string;
}

export const StatusBadge: React.FC<BadgeProps & { status: RegistrationStatus }> = ({
  status,
  size = "md",
  className = "",
}) => {
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  switch (status) {
    case "registered":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium ${sizeClasses} ${className}`}
          style={{
            background: "var(--color-success-bg)",
            color: "var(--color-success)",
            border: "1px solid var(--color-success-border)",
          }}
          role="status"
          aria-label={`Registration Status: ${status}`}
        >
          <CheckCircleIcon size={12} />
          <span className="capitalize">{status}</span>
        </span>
      );
    case "suspended":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium ${sizeClasses} ${className}`}
          style={{
            background: "var(--color-warning-bg)",
            color: "var(--color-warning)",
            border: "1px solid var(--color-warning-border)",
          }}
          role="status"
          aria-label={`Registration Status: ${status}`}
        >
          <AlertTriangleIcon size={12} />
          <span className="capitalize">{status}</span>
        </span>
      );
    case "revoked":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium ${sizeClasses} ${className}`}
          style={{
            background: "var(--color-danger-bg)",
            color: "var(--color-danger)",
            border: "1px solid var(--color-danger-border)",
          }}
          role="status"
          aria-label={`Registration Status: ${status}`}
        >
          <AlertOctagonIcon size={12} />
          <span className="capitalize">{status}</span>
        </span>
      );
    case "unknown":
    case "unregistered":
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium ${sizeClasses} ${className}`}
          style={{
            background: "var(--color-border-subtle)",
            color: "var(--color-text-dim)",
            border: "1px solid var(--color-border)",
          }}
          role="status"
          aria-label={`Registration Status: ${status}`}
        >
          <InfoIcon size={12} />
          <span className="capitalize">{status} (Honest Projection)</span>
        </span>
      );
  }
};

export const EvidenceBadge: React.FC<BadgeProps & { evidenceClass: EvidenceClass; claimed?: boolean }> = ({
  evidenceClass,
  claimed,
  size = "md",
  className = "",
}) => {
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  switch (evidenceClass) {
    case "infrastructure_observed":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-md font-mono font-medium ${sizeClasses} ${className}`}
          style={{
            background: "var(--color-success-bg)",
            color: "var(--color-success)",
            border: "1px solid var(--color-success-border)",
          }}
          title="Observed directly by trusted runtime infrastructure seam"
        >
          <CheckCircleIcon size={12} />
          <span>infrastructure_observed</span>
        </span>
      );
    case "human_authorized":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-md font-mono font-medium ${sizeClasses} ${className}`}
          style={{
            background: "var(--color-info-bg)",
            color: "var(--color-info)",
            border: "1px solid var(--color-info-border)",
          }}
          title="Independently recorded human decision off-chat"
        >
          <ShieldIcon size={12} />
          <span>human_authorized</span>
        </span>
      );
    case "agent_reported":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-md font-mono font-medium ${sizeClasses} ${className}`}
          style={{
            background: "var(--color-warning-bg)",
            color: "var(--color-warning)",
            border: "1px solid var(--color-warning-border)",
          }}
          title="Claimed by agent — unverified and never silently trusted"
        >
          <AlertTriangleIcon size={12} />
          <span>agent_reported {claimed ? "(claimed: true)" : ""}</span>
        </span>
      );
    case "unverified":
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-md font-mono font-medium ${sizeClasses} ${className}`}
          style={{
            background: "var(--color-danger-bg)",
            color: "var(--color-danger)",
            border: "1px solid var(--color-danger-border)",
          }}
          title="Unverified claim — no trust assumed"
        >
          <AlertOctagonIcon size={12} />
          <span>unverified</span>
        </span>
      );
  }
};

export const ScopeBadge: React.FC<{ scope: ParticipationScope }> = ({ scope }) => (
  <span
    className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono"
    style={{
      background: "rgba(45, 212, 191, 0.1)",
      color: "var(--color-jade)",
      border: "1px solid rgba(45, 212, 191, 0.25)",
    }}
  >
    {scope}
  </span>
);

export const AuthorityFlagBadge: React.FC<{ flagName: string; active?: boolean }> = ({
  flagName,
  active = false,
}) => (
  <span
    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono"
    style={{
      background: active ? "var(--color-danger-bg)" : "rgba(255, 255, 255, 0.04)",
      color: active ? "var(--color-danger)" : "var(--color-text-dim)",
      border: "1px solid var(--color-border)",
    }}
    title={active ? "Warning: Active authority flag" : "Zero Execution Authority preserved: False"}
  >
    <ShieldIcon size={12} />
    <span>{flagName}: <strong>{active ? "TRUE (UNAUTHORIZED)" : "false"}</strong></span>
  </span>
);
