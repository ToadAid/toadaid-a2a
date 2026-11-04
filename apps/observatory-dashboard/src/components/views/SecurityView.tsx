import React from "react";
import type { AuthorityFlags } from "../../types/observatory";
import { Card } from "../common/Card";
import { SecurityNoticeBanner } from "../common/Banner";
import { AuthorityFlagBadge } from "../common/Badge";
import { ShieldIcon, AlertTriangleIcon } from "../common/Icons";
import { ObservatoryAdapter } from "../../services/observatoryAdapter";

interface SecurityViewProps {
  authorityFlags: AuthorityFlags;
}

export const SecurityView: React.FC<SecurityViewProps> = ({ authorityFlags }) => {
  // R3-B: strict runtime validation, fail-closed. "ENFORCED FALSE" is only a
  // claim the interface may make for data that strictly conforms to the
  // five-flag, strictly-boolean-false schema; invalid data must never be
  // rendered that way.
  const flagValidation = ObservatoryAdapter.validateAuthorityFlags(authorityFlags);

  return (
    <div className="space-y-6">
      {/* Security Governance Notice */}
      <SecurityNoticeBanner />

      {/* Constitutional Invariants Display */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] space-y-2">
          <div className="flex items-center gap-2 text-[var(--color-gold)] font-mono font-bold text-xs uppercase tracking-wider">
            <ShieldIcon size={16} />
            <span>Constitutional Invariant 1</span>
          </div>
          <h3 className="font-mono text-sm font-bold text-[var(--color-text-primary)]">
            REVOCATION_OVERRIDES_PRIOR_APPROVAL
          </h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            A registration decision minted before a credential rotation, suspension, revocation, or emergency
            disablement can never authorize delivery afterwards. Every admission check consults current state.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] space-y-2">
          <div className="flex items-center gap-2 text-[var(--color-gold)] font-mono font-bold text-xs uppercase tracking-wider">
            <ShieldIcon size={16} />
            <span>Constitutional Invariant 2</span>
          </div>
          <h3 className="font-mono text-sm font-bold text-[var(--color-text-primary)]">
            A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY
          </h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Participation permits message exchange metadata only. It confers no execution permission,
            no wallet signing, no MCP tool authorization, no deployment rights, and no production privileges.
          </p>
        </div>
      </div>

      {/* Fixed All-False Authority Flags — rendered only for validated-conforming data */}
      {flagValidation.valid ? (
        <Card
          title="Immutable Authority Flag Block"
          subtitle="Fixed schema constraint: All five flags must remain false by construction"
          highlight="jade"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(authorityFlags).map(([flag, val]) => (
              <div
                key={flag}
                className="p-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card-hover)] flex items-center justify-between"
              >
                <AuthorityFlagBadge flagName={flag} active={val} />
                <span className="text-[11px] font-mono text-[var(--color-success)] font-bold">
                  ENFORCED FALSE
                </span>
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <Card
          title="Immutable Authority Flag Block"
          subtitle="Runtime authority-flag data failed strict validation — display is withheld"
          highlight="jade"
        >
          <div
            className="p-4 rounded-lg space-y-2 text-xs"
            style={{
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.35)",
            }}
            role="alert"
            aria-label="Invalid authority flag state"
          >
            <div className="flex items-center gap-2 font-mono font-bold text-[var(--color-danger)] uppercase tracking-wider">
              <AlertTriangleIcon size={16} />
              <span>AUTHORITY FLAG DATA INVALID — DISPLAY WITHHELD (FAIL CLOSED)</span>
            </div>
            <p className="text-[var(--color-text-muted)] leading-relaxed">
              The runtime authority-flag data did not conform to the strict five-flag,
              strictly-boolean-false schema. Rendering "ENFORCED FALSE" for invalid data would be a
              false safety claim, so NO flags are displayed. Treat this as an invalid-state warning,
              not an enforcement result.
            </p>
            <ul className="list-disc pl-5 font-mono text-[var(--color-text-dim)] space-y-0.5">
              {flagValidation.problems.map((problem, index) => (
                <li key={index}>{problem}</li>
              ))}
            </ul>
          </div>
        </Card>
      )}

      {/* Four Trust Seams Architecture Card */}
      <Card
        title="The Four Fail-Closed Seams"
        subtitle="Admission gate operates only when all four seams are independently injected"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card-hover)] space-y-1.5">
            <span className="text-[var(--color-jade)] font-bold text-xs block">1. Caller Identity Seam (WHO)</span>
            <p className="text-[var(--color-text-dim)] font-sans">
              Opaque caller credential bound to verified principal. Self-asserted strings authenticate no one.
            </p>
          </div>
          <div className="p-3.5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card-hover)] space-y-1.5">
            <span className="text-[var(--color-jade)] font-bold text-xs block">2. Registration Adapter Seam (WHAT)</span>
            <p className="text-[var(--color-text-dim)] font-sans">
              Point-in-time adapter decision defining participation scopes (send/receive) and evidence expiry.
            </p>
          </div>
          <div className="p-3.5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card-hover)] space-y-1.5">
            <span className="text-[var(--color-gold)] font-bold text-xs block">3. Credential Lifecycle Source (WHICH)</span>
            <p className="text-[var(--color-text-dim)] font-sans">
              Reports current generation and epoch. In-memory high-watermark prevents rollback within process lifetime.
            </p>
          </div>
          <div className="p-3.5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card-hover)] space-y-1.5">
            <span className="text-[var(--color-jade)] font-bold text-xs block">4. Trusted Clock Seam (WHEN)</span>
            <p className="text-[var(--color-text-dim)] font-sans">
              Enforces evidence freshness with calendar-real ISO-8601 UTC validation and aware-clock offsets.
            </p>
          </div>
        </div>
      </Card>

      {/* Disabled Future Administrative Controls */}
      <Card
        title="Administrative Controls Console"
        subtitle="Future privileged operational controls — Gated by Director authorization"
      >
        <div className="space-y-3">
          <div className="p-4 rounded-xl border border-[var(--color-border-subtle)] bg-[rgba(0,0,0,0.2)] opacity-60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-xs font-mono font-bold text-[var(--color-text-primary)]">
                Emergency Agent Disablement
              </h4>
              <p className="text-[11px] text-[var(--color-text-muted)]">
                Broadcast instant emergency revocation across all pond message queues.
              </p>
            </div>
            <button
              disabled
              type="button"
              className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[var(--color-surface-elevated)] text-[var(--color-text-dim)] border border-[var(--color-border)] cursor-not-allowed shrink-0"
              >
              NOT IMPLEMENTED — DIRECTOR AUTHORIZATION REQUIRED
            </button>
          </div>

          <div className="p-4 rounded-xl border border-[var(--color-border-subtle)] bg-[rgba(0,0,0,0.2)] opacity-60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-xs font-mono font-bold text-[var(--color-text-primary)]">
                Rotate Credential Generation Epoch
              </h4>
              <p className="text-[11px] text-[var(--color-text-muted)]">
                Advance tenant revocation epoch and invalidate older point-in-time adapter tokens.
              </p>
            </div>
            <button
              disabled
              type="button"
              className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[var(--color-surface-elevated)] text-[var(--color-text-dim)] border border-[var(--color-border)] cursor-not-allowed shrink-0"
              >
              NOT IMPLEMENTED — DIRECTOR AUTHORIZATION REQUIRED
            </button>
          </div>

          <div className="p-4 rounded-xl border border-[var(--color-border-subtle)] bg-[rgba(0,0,0,0.2)] opacity-60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-xs font-mono font-bold text-[var(--color-text-primary)]">
                Deploy Public Directory Profile
              </h4>
              <p className="text-[11px] text-[var(--color-text-muted)]">
                Expose registered agent cards to search indexers and public A2A endpoints.
              </p>
            </div>
            <button
              disabled
              type="button"
              className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[var(--color-surface-elevated)] text-[var(--color-text-dim)] border border-[var(--color-border)] cursor-not-allowed shrink-0"
              >
              NOT IMPLEMENTED — DIRECTOR AUTHORIZATION REQUIRED
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
};
