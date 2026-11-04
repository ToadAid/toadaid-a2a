/**
 * ToadAid Agent Observatory Type Definitions
 * Strictly aligned with contracts/agent-web/observatory-feed.v0.schema.json
 * and observatory/model.py
 */

export type EventKind =
  | 'agent_identity_reference'
  | 'agent_activity_event'
  | 'a2a_conversation_metadata'
  | 'mcp_tool_request_metadata'
  | 'human_authorization_receipt'
  | 'human_refusal_receipt'
  | 'lifecycle_security_event';

export type EvidenceClass =
  | 'agent_reported'
  | 'infrastructure_observed'
  | 'human_authorized'
  | 'unverified';

export type RegistrationStatus =
  | 'registered'
  | 'revoked'
  | 'suspended'
  | 'unregistered'
  | 'unknown';

export type ParticipationScope =
  | 'a2a-message-send'
  | 'a2a-message-receive';

export interface AuthorityFlags {
  executionAuthorized: false;
  publicationAuthorized: false;
  deploymentAuthorized: false;
  agentRegistrationActive: false;
  publicDirectoryExposed: false;
}

export interface ObservedItemPayload {
  agentRef?: string;
  registrationStatus?: RegistrationStatus;
  activityKind?: string;
  conversationId?: string;
  turnCount?: number;
  participants?: string[];
  toolName?: string;
  requestState?: 'requested' | 'authorized' | 'refused';
  authorizationGrantRef?: string;
  decisionChannel?: string;
  decisionId?: string;
  subjectKind?: string;
  subjectRef?: string;
  objectionCode?: string;
  lifecycleKind?: 'rotation' | 'revocation' | 'emergency_disable' | 'recovery';
  generation?: number;
  revocationEpoch?: number;
  [key: string]: unknown;
}

export interface ObservedItem {
  eventKind: EventKind;
  eventId: string;
  correlationId: string;
  occurredAtUtc: string;
  evidenceClass: EvidenceClass;
  sourceIdentity: string;
  claimed: boolean;
  claimedRegistrationStatus?: RegistrationStatus;
  payload: ObservedItemPayload;
}

export interface ObservatoryFeed {
  kind: 'toadaid-observatory-owner-dashboard-feed';
  schemaVersion: '0.1.0';
  status: 'SYNTHETIC_LOCAL_FOUNDATION_READ_ONLY';
  tenantRef: string;
  ownerRef: string;
  nextPageToken?: string;
  items: ObservedItem[];
  stats: {
    totalForOwner: number;
  };
  authorityFlags: AuthorityFlags;
}

export interface SyntheticAgentRecord {
  agentRef: string;
  frameworkKind: 'openclaw-like' | 'hermes-like' | 'synthetic-evaluator' | 'custom-agent';
  frameworkLabel: string;
  registrationStatus: RegistrationStatus;
  claimedStatus?: RegistrationStatus;
  evidenceClass: EvidenceClass;
  tenantRef: string;
  ownerRef: string;
  supportedScopes: ParticipationScope[];
  credentialGeneration: number;
  revocationEpoch: number;
  observedAtUtc: string;
  description: string;
}

export interface CommunicationStep {
  name: string;
  status: 'passed' | 'refused' | 'checked';
  detail: string;
  failClosedRule: string;
}

export interface CommunicationScenario {
  id: string;
  title: string;
  description: string;
  outcome: 'admitted' | 'refused';
  refusalCode?: string;
  sender: {
    agentRef: string;
    tenantRef: string;
    ownerRef: string;
    claimedGeneration: number;
    claimedEpoch: number;
  };
  recipient: {
    agentRef: string;
    tenantRef: string;
    ownerRef: string;
    claimedGeneration: number;
    claimedEpoch: number;
  };
  steps: CommunicationStep[];
  receiptPreview?: {
    receiptId: string;
    journalHash: string;
    authorityFlags: AuthorityFlags;
    timestamp: string;
  };
}

export type ViewMode =
  | 'overview'
  | 'directory'
  | 'activity'
  | 'communication'
  | 'security';

export type ThemeMode = 'dark' | 'light';
