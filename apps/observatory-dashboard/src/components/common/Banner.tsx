import React from "react";
import { ShieldIcon, AlertTriangleIcon, InfoIcon } from "./Icons";

export const SyntheticNoticeBanner: React.FC<{ className?: string }> = ({ className = "" }) => (
  <div
    className={`rounded-xl p-3.5 sm:px-4 sm:py-3 border flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono transition-colors ${className}`}
    style={{
      background: "rgba(13, 148, 136, 0.12)",
      borderColor: "rgba(45, 212, 191, 0.35)",
      color: "var(--color-text-primary)",
      boxShadow: "var(--shadow-sm)",
    }}
    role="region"
    aria-label="Synthetic Security Environment Invariants"
  >
    {/* Left Column: Status + Boundary Badges */}
    <div className="flex flex-col sm:flex-row sm:items-center gap-2.5">
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-jade)] animate-pulse shrink-0" aria-hidden="true" />
        <span className="font-bold text-[var(--color-jade)] tracking-wide">
          STATUS: LOCAL SYNTHETIC FOUNDATION
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 text-[11px] sm:text-xs">
        <span
          className="px-2 py-0.5 rounded font-bold uppercase tracking-wider"
          style={{
            background: "rgba(239, 68, 68, 0.15)",
            color: "var(--color-danger)",
            border: "1px solid rgba(239, 68, 68, 0.35)",
          }}
        >
          NOT DEPLOYED
        </span>
        <span
          className="px-2 py-0.5 rounded text-[var(--color-text-primary)]"
          style={{
            background: "rgba(255, 255, 255, 0.06)",
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          A2A CHAT HAS ZERO EXECUTION AUTHORITY
        </span>
      </div>
    </div>

    {/* Right Column: Invariant Seal */}
    <div
      className="flex items-center gap-2 font-bold text-xs shrink-0 pt-2 md:pt-0 border-t md:border-t-0"
      style={{
        color: "var(--color-gold)",
        borderColor: "rgba(255, 255, 255, 0.08)",
      }}
    >
      <ShieldIcon size={16} className="text-[var(--color-gold)] shrink-0" />
      <span>AUTHORITY IS NEVER ASSUMED</span>
    </div>
  </div>
);

export const DirectoryNoticeBanner: React.FC = () => (
  <div
    className="rounded-xl p-4 mb-6 flex flex-col sm:flex-row items-start gap-3 text-xs"
    style={{
      background: "var(--color-gold-bg)",
      border: "1px solid rgba(245, 158, 11, 0.35)",
      color: "var(--color-text-primary)",
      boxShadow: "var(--shadow-sm)",
    }}
    role="alert"
    aria-label="Synthetic Directory Notice"
  >
    <AlertTriangleIcon size={20} className="text-[var(--color-gold)] shrink-0 mt-0.5" />
    <div className="space-y-1">
      <h4 className="font-bold tracking-wide uppercase text-[var(--color-gold)] font-mono text-xs">
        SYNTHETIC DIRECTORY PREVIEW — NOT PUBLIC
      </h4>
      <p className="text-[var(--color-text-muted)] leading-relaxed text-xs">
        This is a private owner preview of synthetic agent cards generated for local testing. It confers zero public search indexing,
        no publication consent assumptions, and contains no real owner data. Live public discovery remains
        gated until formal community rights qualification.
      </p>
    </div>
  </div>
);

export const SecurityNoticeBanner: React.FC = () => (
  <div
    className="rounded-xl p-4 mb-6 flex flex-col sm:flex-row items-start gap-3 text-xs"
    style={{
      background: "rgba(239, 68, 68, 0.1)",
      border: "1px solid rgba(239, 68, 68, 0.35)",
      color: "var(--color-text-primary)",
      boxShadow: "var(--shadow-sm)",
    }}
    role="alert"
    aria-label="Security Governance Notice"
  >
    <InfoIcon size={20} className="text-[var(--color-danger)] shrink-0 mt-0.5" />
    <div className="space-y-1">
      <h4 className="font-bold tracking-wide uppercase text-[var(--color-danger)] font-mono text-xs">
        READ-ONLY GOVERNANCE CONSOLE — SYNTHETIC SEAMS
      </h4>
      <p className="text-[var(--color-text-muted)] leading-relaxed text-xs">
        The P0D-A2 credential lifecycle and revocation controls (PR #20) are currently undergoing independent
        Director review. All active management functions below are simulated, disabled, and marked:
        <span className="font-mono font-bold text-[var(--color-text-contrast)] ml-1">
          NOT IMPLEMENTED — DIRECTOR AUTHORIZATION REQUIRED
        </span>.
      </p>
    </div>
  </div>
);
