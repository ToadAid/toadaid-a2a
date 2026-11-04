import React from "react";
import type { ObservedItem, SyntheticAgentRecord } from "../../types/observatory";
import { StatCard } from "../common/StatCard";
import { Card } from "../common/Card";
import { StatusBadge, EvidenceBadge, ScopeBadge } from "../common/Badge";
import { EvidenceBarChart } from "../charts/EvidenceBarChart";
import { StatusDonutChart } from "../charts/StatusDonutChart";
import { UsersIcon, ActivityIcon, ShieldIcon, AlertOctagonIcon, TerminalIcon, ArrowRightIcon } from "../common/Icons";
import { ObservatoryAdapter, type DashboardStats } from "../../services/observatoryAdapter";

interface OverviewViewProps {
  stats: DashboardStats;
  recentEvents: ObservedItem[];
  agents: SyntheticAgentRecord[];
  onNavigateToView: (view: any) => void;
  onSelectEvent: (event: ObservedItem) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  stats,
  recentEvents,
  agents,
  onNavigateToView,
  onSelectEvent,
}) => {
  return (
    <div className="space-y-6">

      {/* KPI Top Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Agents (Synthetic)"
          value={stats.totalAgents}
          subtext="Simulated test participants in local pond scope"
          icon={<UsersIcon size={20} />}
          tone="primary"
        />
        <StatCard
          label="Registered Agents (Synthetic)"
          value={stats.registeredCount}
          subtext="Seam-verified in offline test fixture"
          icon={<ShieldIcon size={20} />}
          tone="gold"
          trend="Qualified"
        />
        <StatCard
          label="Unverified Claims (Synthetic)"
          value={stats.unverifiedCount}
          subtext="Self-asserted claims requiring independent proof"
          icon={<AlertOctagonIcon size={20} />}
          tone="warning"
        />
        <StatCard
          label="Observed Events (Simulated)"
          value={stats.totalEvents}
          subtext="Bounded in-memory synthetic journal records"
          icon={<ActivityIcon size={20} />}
          tone="primary"
        />
      </div>

      {/* Charts Row: Evidence & Status Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title="Simulated Evidence Classification Breakdown"
          subtitle="Constitutional hierarchy: Infrastructure & Human receipts dominate claims"
          highlight="jade"
        >
          <EvidenceBarChart data={stats.evidenceBreakdown} total={stats.totalEvents} />
        </Card>

        <Card
          title="Synthetic Registration Status Projection"
          subtitle="Fail-closed status projection: Registered vs Unknown/Revoked"
          highlight="gold"
        >
          <StatusDonutChart data={stats.statusBreakdown} total={stats.totalAgents} />
        </Card>
      </div>

      {/* Two Column Grid: Agents Preview & Recent Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Sample Agents in Scope */}
        <div className="lg:col-span-1 space-y-4">
          <Card
            title="Active Agents Preview"
            subtitle="Private owner scope representation"
            action={
              <button
                type="button"
                onClick={() => onNavigateToView("directory")}
                className="text-xs font-semibold text-[var(--color-jade)] hover:underline inline-flex items-center gap-1 cursor-pointer"
              >
                View all <ArrowRightIcon size={12} />
              </button>
            }
          >
            <div className="space-y-3">
              {agents.slice(0, 4).map((agent) => (
                <div
                  key={agent.agentRef}
                  className="p-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card-hover)] space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-[var(--color-text-primary)]">
                      {agent.agentRef}
                    </span>
                    <StatusBadge status={agent.registrationStatus} size="sm" />
                  </div>
                  <div className="text-[11px] text-[var(--color-text-dim)]">
                    {agent.frameworkLabel}
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {agent.supportedScopes.map((scope) => (
                      <ScopeBadge key={scope} scope={scope} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right Column: Recent Activity Feed */}
        <div className="lg:col-span-2 space-y-4">
          <Card
            title="Recent Telemetry Timeline"
            subtitle="Recorder insertion order (R1 truthful sequencing)"
            action={
              <button
                type="button"
                onClick={() => onNavigateToView("activity")}
                className="text-xs font-semibold text-[var(--color-jade)] hover:underline inline-flex items-center gap-1 cursor-pointer"
              >
                Explorer <ArrowRightIcon size={12} />
              </button>
            }
          >
            <div className="space-y-2.5">
              {recentEvents.slice(0, 5).map((item) => (
                <div
                  key={item.eventId}
                  onClick={() => onSelectEvent(item)}
                  className="p-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card-hover)] hover:border-[var(--color-border-focus)] transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      onSelectEvent(item);
                    }
                  }}
                  aria-label={`View details for event ${item.eventId}`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <TerminalIcon size={14} className="text-[var(--color-jade)] shrink-0" />
                      <span className="font-mono text-xs font-bold text-[var(--color-text-primary)]">
                        {item.eventKind}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--color-text-dim)]">
                        ({item.eventId})
                      </span>
                    </div>
                    <p className="text-xs text-[var(--color-text-muted)]">
                      Source: <span className="font-mono text-[var(--color-text-primary)]">{item.sourceIdentity}</span>
                    </p>
                  </div>

                  <div className="flex sm:flex-col items-start sm:items-end justify-between gap-1.5 shrink-0">
                    <EvidenceBadge evidenceClass={item.evidenceClass} claimed={item.claimed} size="sm" />
                    <span className="text-[10px] font-mono text-[var(--color-text-dim)]">
                      {ObservatoryAdapter.formatIsoUtc(item.occurredAtUtc)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
