import type {
  ObservatoryFeed,
  ObservedItem,
  EventKind,
  EvidenceClass,
  RegistrationStatus,
  SyntheticAgentRecord
} from '../types/observatory';
import { PRIMARY_SYNTHETIC_FEED } from '../data/syntheticFeed';
import { SYNTHETIC_DIRECTORY_AGENTS } from '../data/syntheticDirectory';

export interface DashboardStats {
  totalEvents: number;
  totalAgents: number;
  registeredCount: number;
  unverifiedCount: number;
  refusedCount: number;
  evidenceBreakdown: Record<EvidenceClass, number>;
  statusBreakdown: Record<RegistrationStatus, number>;
  kindBreakdown: Record<EventKind, number>;
}

export interface ActivityFilterOptions {
  eventKind?: EventKind | 'all';
  evidenceClass?: EvidenceClass | 'all';
  searchQuery?: string;
  claimedOnly?: boolean;
}

export class ObservatoryAdapter {
  private feed: ObservatoryFeed;
  private agents: SyntheticAgentRecord[];

  constructor(feed: ObservatoryFeed = PRIMARY_SYNTHETIC_FEED, agents: SyntheticAgentRecord[] = SYNTHETIC_DIRECTORY_AGENTS) {
    this.feed = feed;
    this.agents = agents;
  }

  public getFeed(): ObservatoryFeed {
    return this.feed;
  }

  public getTenantRef(): string {
    return this.feed.tenantRef;
  }

  public getOwnerRef(): string {
    return this.feed.ownerRef;
  }

  public getAuthorityFlags() {
    return this.feed.authorityFlags;
  }

  public getItems(): ObservedItem[] {
    return [...this.feed.items];
  }

  public getAgents(): SyntheticAgentRecord[] {
    return [...this.agents];
  }

  public getStats(): DashboardStats {
    const evidenceBreakdown: Record<EvidenceClass, number> = {
      infrastructure_observed: 0,
      agent_reported: 0,
      human_authorized: 0,
      unverified: 0,
    };

    const kindBreakdown: Record<EventKind, number> = {
      agent_identity_reference: 0,
      agent_activity_event: 0,
      a2a_conversation_metadata: 0,
      mcp_tool_request_metadata: 0,
      human_authorization_receipt: 0,
      human_refusal_receipt: 0,
      lifecycle_security_event: 0,
    };

    for (const item of this.feed.items) {
      if (item.evidenceClass in evidenceBreakdown) {
        evidenceBreakdown[item.evidenceClass]++;
      }
      if (item.eventKind in kindBreakdown) {
        kindBreakdown[item.eventKind]++;
      }
    }

    const statusBreakdown: Record<RegistrationStatus, number> = {
      registered: 0,
      revoked: 0,
      suspended: 0,
      unregistered: 0,
      unknown: 0,
    };

    for (const agent of this.agents) {
      statusBreakdown[agent.registrationStatus]++;
    }

    return {
      totalEvents: this.feed.items.length,
      totalAgents: this.agents.length,
      registeredCount: statusBreakdown.registered,
      unverifiedCount: evidenceBreakdown.agent_reported + evidenceBreakdown.unverified,
      refusedCount: kindBreakdown.human_refusal_receipt + 1, // refusal receipt + tool refusal
      evidenceBreakdown,
      statusBreakdown,
      kindBreakdown,
    };
  }

  public filterEvents(options: ActivityFilterOptions): ObservedItem[] {
    return this.feed.items.filter((item) => {
      if (options.eventKind && options.eventKind !== 'all') {
        if (item.eventKind !== options.eventKind) return false;
      }
      if (options.evidenceClass && options.evidenceClass !== 'all') {
        if (item.evidenceClass !== options.evidenceClass) return false;
      }
      if (options.claimedOnly && !item.claimed) {
        return false;
      }
      if (options.searchQuery && options.searchQuery.trim() !== '') {
        const query = options.searchQuery.toLowerCase().trim();
        const matchesId = item.eventId.toLowerCase().includes(query);
        const matchesCorr = item.correlationId.toLowerCase().includes(query);
        const matchesSource = item.sourceIdentity.toLowerCase().includes(query);
        const matchesPayload = JSON.stringify(item.payload).toLowerCase().includes(query);
        if (!matchesId && !matchesCorr && !matchesSource && !matchesPayload) {
          return false;
        }
      }
      return true;
    });
  }

  public filterAgents(query: string, statusFilter: string = 'all'): SyntheticAgentRecord[] {
    const q = query.toLowerCase().trim();
    return this.agents.filter((agent) => {
      if (statusFilter !== 'all' && agent.registrationStatus !== statusFilter) {
        return false;
      }
      if (!q) return true;
      return (
        agent.agentRef.toLowerCase().includes(q) ||
        agent.frameworkKind.toLowerCase().includes(q) ||
        agent.frameworkLabel.toLowerCase().includes(q) ||
        agent.ownerRef.toLowerCase().includes(q) ||
        agent.tenantRef.toLowerCase().includes(q) ||
        agent.description.toLowerCase().includes(q)
      );
    });
  }

  public static formatIsoUtc(isoString: string): string {
    try {
      const date = new Date(isoString);
      return date.toISOString().replace(/\.\d{3}Z$/, " UTC").replace('Z', ' UTC').replace('T', ' ');
    } catch {
      return isoString;
    }
  }

  public static formatEvidenceLabel(evidenceClass: EvidenceClass): { label: string; verified: boolean; tone: 'success' | 'warning' | 'info' | 'danger' } {
    switch (evidenceClass) {
      case 'infrastructure_observed':
        return { label: 'Infrastructure Observed', verified: true, tone: 'success' };
      case 'human_authorized':
        return { label: 'Human Authorized', verified: true, tone: 'info' };
      case 'agent_reported':
        return { label: 'Agent Reported (Claimed)', verified: false, tone: 'warning' };
      case 'unverified':
      default:
        return { label: 'Unverified External Claim', verified: false, tone: 'danger' };
    }
  }
}

export const defaultAdapter = new ObservatoryAdapter();
