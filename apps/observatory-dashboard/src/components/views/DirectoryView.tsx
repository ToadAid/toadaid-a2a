import React, { useState } from "react";
import type { SyntheticAgentRecord } from "../../types/observatory";
import { StatusBadge, EvidenceBadge, ScopeBadge } from "../common/Badge";
import { DirectoryNoticeBanner } from "../common/Banner";
import { Modal } from "../common/Modal";
import { SearchIcon, FilterIcon, ClockIcon } from "../common/Icons";
import { ObservatoryAdapter } from "../../services/observatoryAdapter";

interface DirectoryViewProps {
  agents: SyntheticAgentRecord[];
}

export const DirectoryView: React.FC<DirectoryViewProps> = ({ agents }) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedAgent, setSelectedAgent] = useState<SyntheticAgentRecord | null>(null);

  const adapter = new ObservatoryAdapter(undefined, agents);
  const filteredAgents = adapter.filterAgents(searchQuery, statusFilter);

  return (
    <div className="space-y-6">
      {/* Directory Notice Banner */}
      <DirectoryNoticeBanner />

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3 justify-between">
        <div className="relative w-full sm:w-80">
          <label htmlFor="agent-search" className="sr-only">Search synthetic agents</label>
          <SearchIcon size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-dim)]" />
          <input
            id="agent-search"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search agents, frameworks, scopes..."
            className="w-full pl-9 pr-4 py-2 rounded-lg text-xs font-mono bg-[var(--color-surface-card)] border border-[var(--color-border)] text-[var(--color-text-primary)] placeholder-[var(--color-text-dim)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] transition-all"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <FilterIcon size={16} className="text-[var(--color-text-dim)] shrink-0" />
          <label htmlFor="status-filter" className="sr-only">Filter by registration status</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full sm:w-auto px-3 py-2 rounded-lg text-xs font-mono bg-[var(--color-surface-card)] border border-[var(--color-border)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] cursor-pointer"
          >
            <option value="all">All Statuses ({agents.length})</option>
            <option value="registered">Registered</option>
            <option value="suspended">Suspended</option>
            <option value="revoked">Revoked</option>
            <option value="unknown">Unknown / Unverified</option>
          </select>
        </div>
      </div>

      {/* Agent Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredAgents.map((agent) => (
          <div
            key={agent.agentRef}
            onClick={() => setSelectedAgent(agent)}
            className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] hover:border-[var(--color-border-focus)] p-5 transition-all cursor-pointer flex flex-col justify-between gap-4"
            style={{ boxShadow: "var(--shadow-sm)" }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") setSelectedAgent(agent);
            }}
            aria-label={`Inspect agent ${agent.agentRef}`}
          >
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-mono font-bold text-sm text-[var(--color-text-primary)] break-all">
                    {agent.agentRef}
                  </h3>
                  <span className="text-xs text-[var(--color-jade)] font-medium">
                    {agent.frameworkLabel}
                  </span>
                </div>
                <StatusBadge status={agent.registrationStatus} size="sm" />
              </div>

              <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                {agent.description}
              </p>

              <div className="flex flex-wrap gap-1.5 pt-1">
                {agent.supportedScopes.length > 0 ? (
                  agent.supportedScopes.map((scope) => (
                    <ScopeBadge key={scope} scope={scope} />
                  ))
                ) : (
                  <span className="text-[11px] font-mono text-[var(--color-text-dim)] italic">
                    No participation scopes granted
                  </span>
                )}
              </div>
            </div>

            <div className="pt-3 border-t border-[var(--color-border-subtle)] flex items-center justify-between text-[11px] font-mono text-[var(--color-text-dim)]">
              <span>Tenant: {agent.tenantRef}</span>
              <span className="text-[var(--color-gold)] font-medium">Gen {agent.credentialGeneration} / Ep {agent.revocationEpoch}</span>
            </div>
          </div>
        ))}

        {filteredAgents.length === 0 && (
          <div className="col-span-full py-12 text-center text-xs text-[var(--color-text-dim)]">
            No agents found matching &quot;{searchQuery}&quot;. Try adjusting your search query or status filter.
          </div>
        )}
      </div>

      {/* Agent Detail Modal */}
      {selectedAgent && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedAgent(null)}
          title={`Agent Identity Card: ${selectedAgent.agentRef}`}
          subtitle="Synthetic telemetry inspection and credential lifecycle state"
        >
          <div className="space-y-4">
            <div className="p-3.5 rounded-lg bg-[var(--color-surface-card-hover)] border border-[var(--color-border-subtle)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--color-text-dim)]">Registration Status</span>
                <StatusBadge status={selectedAgent.registrationStatus} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--color-text-dim)]">Evidence Classification</span>
                <EvidenceBadge evidenceClass={selectedAgent.evidenceClass} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--color-text-dim)]">Framework Flavor</span>
                <span className="text-xs font-mono font-medium text-[var(--color-text-primary)]">{selectedAgent.frameworkLabel}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card)]">
                <span className="text-[var(--color-text-dim)] block text-[10px] uppercase">Tenant Ref</span>
                <span className="text-[var(--color-jade)] font-bold">{selectedAgent.tenantRef}</span>
              </div>
              <div className="p-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card)]">
                <span className="text-[var(--color-text-dim)] block text-[10px] uppercase">Owner Ref</span>
                <span className="text-[var(--color-gold)] font-bold">{selectedAgent.ownerRef}</span>
              </div>
              <div className="p-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card)]">
                <span className="text-[var(--color-text-dim)] block text-[10px] uppercase">Credential Generation</span>
                <span className="text-[var(--color-text-primary)] font-bold">Gen {selectedAgent.credentialGeneration}</span>
              </div>
              <div className="p-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card)]">
                <span className="text-[var(--color-text-dim)] block text-[10px] uppercase">Revocation Epoch</span>
                <span className="text-[var(--color-text-primary)] font-bold">Epoch {selectedAgent.revocationEpoch}</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-[var(--color-text-primary)]">Permitted Participation Scopes</span>
              <div className="flex flex-wrap gap-2">
                {selectedAgent.supportedScopes.map((scope) => (
                  <ScopeBadge key={scope} scope={scope} />
                ))}
              </div>
            </div>

            <div className="p-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card)] text-xs text-[var(--color-text-dim)] flex items-center gap-2">
              <ClockIcon size={14} />
              <span>Observed At: <span className="font-mono text-[var(--color-text-primary)]">{ObservatoryAdapter.formatIsoUtc(selectedAgent.observedAtUtc)}</span></span>
            </div>

            <div className="p-3 rounded-lg bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.25)] text-xs text-[var(--color-danger)] font-mono">
              NOTICE: This card is an offline test fixture. It confers zero production authentication or public discoverability.
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
