import React, { useState } from "react";
import type { ObservedItem, EventKind, EvidenceClass } from "../../types/observatory";
import { Card } from "../common/Card";
import { EvidenceBadge } from "../common/Badge";
import { Modal } from "../common/Modal";
import { SearchIcon, ShieldIcon } from "../common/Icons";
import { ObservatoryAdapter } from "../../services/observatoryAdapter";
import { projectPayload, projectedSearchText } from "../../services/payloadProjection";

interface ActivityViewProps {
  events: ObservedItem[];
  selectedEvent: ObservedItem | null;
  onSelectEvent: (event: ObservedItem | null) => void;
}

export const ActivityView: React.FC<ActivityViewProps> = ({
  events,
  selectedEvent,
  onSelectEvent,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedKind, setSelectedKind] = useState<EventKind | "all">("all");
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceClass | "all">("all");
  const [claimedOnly, setClaimedOnly] = useState(false);

  const filteredEvents = events.filter((item) => {
    if (selectedKind !== "all" && item.eventKind !== selectedKind) return false;
    if (selectedEvidence !== "all" && item.evidenceClass !== selectedEvidence) return false;
    if (claimedOnly && !item.claimed) return false;
    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase().trim();
      const matchId = item.eventId.toLowerCase().includes(q);
      const matchCorr = item.correlationId.toLowerCase().includes(q);
      const matchSource = item.sourceIdentity.toLowerCase().includes(q);
      const matchKind = item.eventKind.toLowerCase().includes(q);
      // Payload matching runs over the fail-closed allowlisted projection
      // only (R3-A) — raw payload data never feeds search results or display.
      const matchPayload = projectedSearchText(item.eventKind, item.payload).includes(q);
      if (!matchId && !matchCorr && !matchSource && !matchKind && !matchPayload) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Search and Filters Bar */}
      <Card>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="relative">
            <SearchIcon size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-dim)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search event ID, correlation..."
              className="w-full pl-9 pr-4 py-2 rounded-lg text-xs font-mono bg-[var(--color-surface-card-hover)] border border-[var(--color-border)] text-[var(--color-text-primary)] placeholder-[var(--color-text-dim)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] transition-all"
            />
          </div>

          <div>
            <select
              aria-label="Filter by event kind"
              value={selectedKind}
              onChange={(e) => setSelectedKind(e.target.value as any)}
              className="w-full px-3 py-2 rounded-lg text-xs font-mono bg-[var(--color-surface-card-hover)] border border-[var(--color-border)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] cursor-pointer"
            >
              <option value="all">All Event Kinds</option>
              <option value="agent_identity_reference">agent_identity_reference</option>
              <option value="agent_activity_event">agent_activity_event</option>
              <option value="a2a_conversation_metadata">a2a_conversation_metadata</option>
              <option value="mcp_tool_request_metadata">mcp_tool_request_metadata</option>
              <option value="human_authorization_receipt">human_authorization_receipt</option>
              <option value="human_refusal_receipt">human_refusal_receipt</option>
              <option value="lifecycle_security_event">lifecycle_security_event</option>
            </select>
          </div>

          <div>
            <select
              aria-label="Filter by evidence class"
              value={selectedEvidence}
              onChange={(e) => setSelectedEvidence(e.target.value as any)}
              className="w-full px-3 py-2 rounded-lg text-xs font-mono bg-[var(--color-surface-card-hover)] border border-[var(--color-border)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] cursor-pointer"
            >
              <option value="all">All Evidence Classes</option>
              <option value="infrastructure_observed">Infrastructure Observed</option>
              <option value="human_authorized">Human Authorized</option>
              <option value="agent_reported">Agent Reported (Claimed)</option>
              <option value="unverified">Unverified External</option>
            </select>
          </div>

          <div className="flex items-center gap-2 px-2">
            <input
              id="claimed-toggle"
              type="checkbox"
              checked={claimedOnly}
              onChange={(e) => setClaimedOnly(e.target.checked)}
              className="rounded border-[var(--color-border)] text-[var(--color-jade)] focus:ring-[var(--color-border-focus)]"
            />
            <label htmlFor="claimed-toggle" className="text-xs text-[var(--color-text-dim)] cursor-pointer select-none">
              Claimed events only
            </label>
          </div>
        </div>
      </Card>

      {/* Events Table / List */}
      <Card title={`Observed Telemetry Records (${filteredEvents.length} items)`} subtitle="Deterministic recorder insertion order">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-[var(--color-border-subtle)] text-[var(--color-text-dim)] uppercase tracking-wider text-[11px]">
                <th scope="col" className="pb-3 pl-2">Event ID</th>
                <th scope="col" className="pb-3">Event Kind</th>
                <th scope="col" className="pb-3">Evidence Class</th>
                <th scope="col" className="pb-3">Source Identity</th>
                <th scope="col" className="pb-3">Occurred At (UTC)</th>
                <th scope="col" className="pb-3 text-right pr-2">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)]">
              {filteredEvents.map((item) => (
                <tr
                  key={item.eventId}
                  className="hover:bg-[var(--color-surface-card-hover)] transition-colors cursor-pointer"
                  onClick={() => onSelectEvent(item)}
                >
                  <td className="py-3 pl-2 font-bold text-[var(--color-jade)]">
                    {item.eventId}
                  </td>
                  <td className="py-3 text-[var(--color-text-primary)]">
                    {item.eventKind}
                  </td>
                  <td className="py-3">
                    <EvidenceBadge evidenceClass={item.evidenceClass} claimed={item.claimed} size="sm" />
                  </td>
                  <td className="py-3 text-[var(--color-text-muted)] truncate max-w-xs">
                    {item.sourceIdentity}
                  </td>
                  <td className="py-3 text-[var(--color-text-dim)]">
                    {ObservatoryAdapter.formatIsoUtc(item.occurredAtUtc)}
                  </td>
                  <td className="py-3 text-right pr-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectEvent(item);
                      }}
                      className="px-2.5 py-1 rounded text-xs font-semibold text-[var(--color-jade)] bg-[rgba(45,212,191,0.1)] hover:bg-[rgba(45,212,191,0.2)] transition-all cursor-pointer"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
              {filteredEvents.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-xs text-[var(--color-text-dim)]">
                    No events match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Event Details Inspection Modal */}
      {selectedEvent && (
        <Modal
          isOpen={true}
          onClose={() => onSelectEvent(null)}
          title={`Simulated Telemetry Record: ${selectedEvent.eventId}`}
          subtitle={`Correlation ID: ${selectedEvent.correlationId}`}
        >
          <div className="space-y-4 font-mono text-xs">
            <div className="p-3 rounded-lg bg-[var(--color-surface-card-hover)] border border-[var(--color-border-subtle)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-text-dim)]">Event Kind:</span>
                <span className="font-bold text-[var(--color-text-primary)]">{selectedEvent.eventKind}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-text-dim)]">Evidence Class:</span>
                <EvidenceBadge evidenceClass={selectedEvent.evidenceClass} claimed={selectedEvent.claimed} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-text-dim)]">Source Identity:</span>
                <span className="text-[var(--color-text-muted)]">{selectedEvent.sourceIdentity}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-text-dim)]">Occurred At:</span>
                <span className="text-[var(--color-text-dim)]">{ObservatoryAdapter.formatIsoUtc(selectedEvent.occurredAtUtc)}</span>
              </div>
            </div>

            <div>
              {(() => {
                const projected = projectPayload(
                  selectedEvent.eventKind,
                  selectedEvent.payload
                );
                return (
                  <>
                    <span className="text-[var(--color-text-dim)] block mb-1 font-sans font-semibold">
                      Payload Inspection (fail-closed allowlisted projection)
                    </span>
                    <pre
                      className="p-3.5 rounded-lg border border-[var(--color-border-subtle)] bg-[#040c0e] text-[#a7f3d0] overflow-x-auto text-xs"
                      tabIndex={0}
                      aria-label="Allowlisted event payload projection"
                    >
                      {JSON.stringify(projected.fields, null, 2)}
                    </pre>
                    {projected.withheldFieldCount > 0 && (
                      <div
                        className="mt-2 p-2.5 rounded-lg text-xs font-mono text-[var(--color-gold)]"
                        style={{
                          background: "rgba(245, 158, 11, 0.12)",
                          border: "1px solid rgba(245, 158, 11, 0.35)",
                        }}
                        role="status"
                      >
                        FAIL-CLOSED REDACTION: {projected.withheldFieldCount} unexpected or
                        non-conforming payload field(s) withheld — their names and values are not displayed.
                      </div>
                    )}
                  </>
                );
              })()}
            </div>

            <div className="p-3 rounded-lg bg-[rgba(13,148,136,0.1)] border border-[rgba(45,212,191,0.25)] text-xs text-[var(--color-text-dim)] font-sans">
              <ShieldIcon size={14} className="inline mr-1 text-[var(--color-jade)]" />
              Privacy Floor: only explicit, event-kind-specific allowlisted metadata fields are rendered; unexpected
              fields are withheld without exposing names or values. This client-side projection is a browser-side
              safeguard for the trusted synthetic feed, not a trust boundary — for a future production data source,
              real private data must be excluded by trusted server-side projection BEFORE it reaches the browser.
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
