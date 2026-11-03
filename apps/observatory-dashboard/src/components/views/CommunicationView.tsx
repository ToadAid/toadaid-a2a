import React, { useState } from "react";
import { SYNTHETIC_FLOW_SCENARIOS } from "../../data/syntheticFlows";
import { Card } from "../common/Card";
import { CheckCircleIcon, AlertOctagonIcon, ShieldIcon, ArrowRightIcon, RadioIcon } from "../common/Icons";

export const CommunicationView: React.FC = () => {
  const [selectedScenarioId, setSelectedScenarioId] = useState(SYNTHETIC_FLOW_SCENARIOS[0].id);

  const scenario = SYNTHETIC_FLOW_SCENARIOS.find((s) => s.id === selectedScenarioId) || SYNTHETIC_FLOW_SCENARIOS[0];

  return (
    <div className="space-y-6">
      {/* Scenario Selector Tabs */}
      <div className="flex flex-wrap gap-2">
        {SYNTHETIC_FLOW_SCENARIOS.map((s) => {
          const isSelected = s.id === scenario.id;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => setSelectedScenarioId(s.id)}
              className={`px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer border ${
                isSelected
                  ? "bg-[var(--color-surface-elevated)] border-[var(--color-jade)] text-[var(--color-text-primary)] font-bold shadow-sm"
                  : "bg-[var(--color-surface-card)] border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-focus)]"
              }`}
            >
              {s.title}
            </button>
          );
        })}
      </div>

      {/* Scenario Description Card */}
      <Card
        title={scenario.title}
        subtitle="A2A Multi-Agent Admission Pipeline (Simulated Flow — Illustrative Only)"
        highlight={scenario.outcome === "admitted" ? "jade" : "danger"}
        action={
          <span
            className={`px-3 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-wider inline-flex items-center gap-1.5 ${
              scenario.outcome === "admitted"
                ? "bg-[var(--color-success-bg)] text-[var(--color-success)] border border-[var(--color-success-border)]"
                : "bg-[var(--color-danger-bg)] text-[var(--color-danger)] border border-[var(--color-danger-border)]"
            }`}
          >
            {scenario.outcome === "admitted" ? <CheckCircleIcon size={14} /> : <AlertOctagonIcon size={14} />}
            {scenario.outcome === "admitted" ? "DELIVERY ADMITTED" : `REFUSED: ${scenario.refusalCode}`}
          </span>
        }
      >
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed mb-6">
          {scenario.description}
        </p>

        {/* Visual Flow Representation */}
        <div className="p-6 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-subtle)] space-y-6">
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">

            {/* 1. SENDER AGENT */}
            <div className="flex-1 p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] space-y-2">
              <div className="flex items-center gap-2 text-[var(--color-jade)] font-mono text-xs font-bold">
                <RadioIcon size={16} />
                <span>SENDER: {scenario.sender.agentRef}</span>
              </div>
              <div className="text-[11px] font-mono text-[var(--color-text-dim)] space-y-1">
                <div>Tenant: <span className="text-[var(--color-text-primary)]">{scenario.sender.tenantRef}</span></div>
                <div>Owner: <span className="text-[var(--color-text-primary)]">{scenario.sender.ownerRef}</span></div>
                <div>Generation: <span className="text-[var(--color-gold)]">Gen {scenario.sender.claimedGeneration}</span></div>
                <div>Epoch: <span className="text-[var(--color-gold)]">Epoch {scenario.sender.claimedEpoch}</span></div>
              </div>
            </div>

            {/* ARROW 1 */}
            <div className="flex items-center justify-center text-[var(--color-text-dim)]">
              <ArrowRightIcon size={24} className="rotate-90 lg:rotate-0" />
            </div>

            {/* 2. ADMISSION GATE SEAM EVALUATOR */}
            <div className="flex-1 p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] space-y-2 text-center relative overflow-hidden">
              <div
                className="absolute top-0 left-0 right-0 h-1"
                style={{
                  background: scenario.outcome === "admitted" ? "var(--color-success)" : "var(--color-danger)",
                }}
              />
              <div className="inline-flex items-center gap-1.5 text-xs font-bold font-mono text-[var(--color-text-primary)]">
                <ShieldIcon size={16} className="text-[var(--color-gold)]" />
                <span>RegisteredAgentGate</span>
              </div>
              <p className="text-[11px] text-[var(--color-text-dim)]">
                4-Seam Fail-Closed Verification & Tenant Matching
              </p>
              <div className="text-[10px] font-mono p-1.5 rounded bg-[var(--color-surface-card-hover)] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]">
                {scenario.outcome === "admitted" ? "All Invariants Satisfied" : `Refusal: ${scenario.refusalCode}`}
              </div>
            </div>

            {/* ARROW 2 */}
            <div className="flex items-center justify-center text-[var(--color-text-dim)]">
              <ArrowRightIcon size={24} className="rotate-90 lg:rotate-0" />
            </div>

            {/* 3. RECIPIENT AGENT */}
            <div className="flex-1 p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] space-y-2">
              <div className="flex items-center gap-2 text-[var(--color-jade)] font-mono text-xs font-bold">
                <RadioIcon size={16} />
                <span>RECIPIENT: {scenario.recipient.agentRef}</span>
              </div>
              <div className="text-[11px] font-mono text-[var(--color-text-dim)] space-y-1">
                <div>Tenant: <span className="text-[var(--color-text-primary)]">{scenario.recipient.tenantRef}</span></div>
                <div>Owner: <span className="text-[var(--color-text-primary)]">{scenario.recipient.ownerRef}</span></div>
                <div>Generation: <span className="text-[var(--color-gold)]">Gen {scenario.recipient.claimedGeneration}</span></div>
                <div>Epoch: <span className="text-[var(--color-gold)]">Epoch {scenario.recipient.claimedEpoch}</span></div>
              </div>
            </div>
          </div>

          {/* Sequential Step Verification Results */}
          <div className="space-y-2 pt-2">
            <h4 className="text-xs font-bold font-mono text-[var(--color-text-primary)] uppercase tracking-wider">
              Admission Pipeline Invariant Checks:
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {scenario.steps.map((st, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg border bg-[var(--color-surface-card)] flex items-start gap-2.5 text-xs font-mono"
                  style={{
                    borderColor: st.status === "passed" ? "var(--color-border-subtle)" : "var(--color-danger)",
                  }}
                >
                  {st.status === "passed" ? (
                    <CheckCircleIcon size={16} className="text-[var(--color-success)] shrink-0 mt-0.5" />
                  ) : (
                    <AlertOctagonIcon size={16} className="text-[var(--color-danger)] shrink-0 mt-0.5" />
                  )}
                  <div>
                    <span className="font-bold text-[var(--color-text-primary)] block">
                      {st.name}
                    </span>
                    <span className="text-[var(--color-text-muted)] text-[11px] block mt-0.5">
                      {st.detail}
                    </span>
                    <span className="text-[10px] text-[var(--color-text-dim)] italic block mt-1">
                      Rule: {st.failClosedRule}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Admitted Receipt Preview (If Admitted) */}
          {scenario.receiptPreview && (
            <div className="p-4 rounded-xl border border-[var(--color-success-border)] bg-[var(--color-success-bg)] space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between">
                <span className="font-bold text-[var(--color-success)] flex items-center gap-1.5">
                  <ShieldIcon size={14} /> Admitted Delivery Receipt (Metadata Only)
                </span>
                <span className="text-[var(--color-text-dim)]">{scenario.receiptPreview.timestamp}</span>
              </div>
              <div className="text-[11px] text-[var(--color-text-primary)]">
                Journal Digest: <span className="font-bold text-[var(--color-jade)]">{scenario.receiptPreview.journalHash}</span>
              </div>
              <div className="text-[10px] text-[var(--color-text-muted)]">
                Constitutional Proof: A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY — Authority flags are all false by construction.
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};
