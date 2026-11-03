import type { ObservatoryFeed } from '../types/observatory';

export const PRIMARY_SYNTHETIC_FEED: ObservatoryFeed = {
  kind: "toadaid-observatory-owner-dashboard-feed",
  schemaVersion: "0.1.0",
  status: "SYNTHETIC_LOCAL_FOUNDATION_READ_ONLY",
  tenantRef: "tenant-alpha",
  ownerRef: "owner-alpha",
  stats: {
    totalForOwner: 12
  },
  authorityFlags: {
    executionAuthorized: false,
    publicationAuthorized: false,
    deploymentAuthorized: false,
    agentRegistrationActive: false,
    publicDirectoryExposed: false
  },
  items: [
    // --- EXACT FIXTURE ITEMS FROM contracts/examples/synthetic-observatory-feed.v0.json ---
    {
      eventId: "evt-synthetic-alpha-001",
      eventKind: "agent_identity_reference",
      correlationId: "corr-synthetic-alpha-001",
      occurredAtUtc: "2026-11-03T00:00:00Z",
      evidenceClass: "infrastructure_observed",
      sourceIdentity: "agent-admission-portal",
      claimed: false,
      payload: {
        agentRef: "agent-synthetic-one",
        registrationStatus: "registered"
      }
    },
    {
      eventId: "evt-synthetic-alpha-002",
      eventKind: "agent_identity_reference",
      correlationId: "corr-synthetic-alpha-002",
      occurredAtUtc: "2026-11-03T00:00:01Z",
      evidenceClass: "agent_reported",
      sourceIdentity: "agent-synthetic-two",
      claimed: true,
      claimedRegistrationStatus: "registered",
      payload: {
        agentRef: "agent-synthetic-two",
        registrationStatus: "unknown"
      }
    },
    {
      eventId: "evt-synthetic-alpha-003",
      eventKind: "human_refusal_receipt",
      correlationId: "corr-synthetic-alpha-003",
      occurredAtUtc: "2026-11-03T00:00:02Z",
      evidenceClass: "human_authorized",
      sourceIdentity: "independent-off-chat-human-process",
      claimed: false,
      payload: {
        decisionChannel: "independent-off-chat-human-process",
        decisionId: "dec-synthetic-003",
        objectionCode: "PRIVACY",
        subjectKind: "agent_enrollment_publication",
        subjectRef: "agent-synthetic-two"
      }
    },
    // --- EXTENDED SCHEMA-CONFORMANT SYNTHETIC EVENTS FOR EXPLORER & TIMELINE ---
    {
      eventId: "evt-synthetic-alpha-004",
      eventKind: "a2a_conversation_metadata",
      correlationId: "corr-synthetic-alpha-004",
      occurredAtUtc: "2026-11-03T01:15:20Z",
      evidenceClass: "infrastructure_observed",
      sourceIdentity: "lifecycle-journal",
      claimed: false,
      payload: {
        conversationId: "conv-synt-pond-081",
        turnCount: 4,
        participants: ["agent-synthetic-one", "agent-synthetic-alpha"]
      }
    },
    {
      eventId: "evt-synthetic-alpha-005",
      eventKind: "mcp_tool_request_metadata",
      correlationId: "corr-synthetic-alpha-005",
      occurredAtUtc: "2026-11-03T02:30:10Z",
      evidenceClass: "infrastructure_observed",
      sourceIdentity: "observatory-recorder",
      claimed: false,
      payload: {
        toolName: "read_water_temperature",
        requestState: "authorized",
        authorizationGrantRef: "grant-synthetic-read-001"
      }
    },
    {
      eventId: "evt-synthetic-alpha-006",
      eventKind: "mcp_tool_request_metadata",
      correlationId: "corr-synthetic-alpha-006",
      occurredAtUtc: "2026-11-03T02:45:00Z",
      evidenceClass: "infrastructure_observed",
      sourceIdentity: "observatory-recorder",
      claimed: false,
      payload: {
        toolName: "execute_shell_command",
        requestState: "refused",
        authorizationGrantRef: "refused-zero-execution-authority"
      }
    },
    {
      eventId: "evt-synthetic-alpha-007",
      eventKind: "agent_activity_event",
      correlationId: "corr-synthetic-alpha-007",
      occurredAtUtc: "2026-11-03T03:10:45Z",
      evidenceClass: "agent_reported",
      sourceIdentity: "agent-synthetic-one",
      claimed: true,
      payload: {
        agentRef: "agent-synthetic-one",
        activityKind: "task_update"
      }
    },
    {
      eventId: "evt-synthetic-alpha-008",
      eventKind: "lifecycle_security_event",
      correlationId: "corr-synthetic-alpha-008",
      occurredAtUtc: "2026-11-03T04:22:18Z",
      evidenceClass: "infrastructure_observed",
      sourceIdentity: "lifecycle-journal",
      claimed: false,
      payload: {
        agentRef: "agent-synthetic-one",
        lifecycleKind: "rotation",
        generation: 3,
        revocationEpoch: 1
      }
    },
    {
      eventId: "evt-synthetic-alpha-009",
      eventKind: "human_authorization_receipt",
      correlationId: "corr-synthetic-alpha-009",
      occurredAtUtc: "2026-11-03T05:00:00Z",
      evidenceClass: "human_authorized",
      sourceIdentity: "independent-off-chat-human-process",
      claimed: false,
      payload: {
        decisionChannel: "independent-off-chat-human-process",
        decisionId: "dec-synthetic-009",
        subjectKind: "agent_rehearsal_observation",
        subjectRef: "agent-synthetic-one"
      }
    },
    {
      eventId: "evt-synthetic-alpha-010",
      eventKind: "agent_identity_reference",
      correlationId: "corr-synthetic-alpha-010",
      occurredAtUtc: "2026-11-03T06:12:00Z",
      evidenceClass: "unverified",
      sourceIdentity: "external-unauthenticated-beacon",
      claimed: true,
      claimedRegistrationStatus: "registered",
      payload: {
        agentRef: "agent-synthetic-three",
        registrationStatus: "unknown"
      }
    },
    {
      eventId: "evt-synthetic-alpha-011",
      eventKind: "lifecycle_security_event",
      correlationId: "corr-synthetic-alpha-011",
      occurredAtUtc: "2026-11-03T07:40:15Z",
      evidenceClass: "infrastructure_observed",
      sourceIdentity: "lifecycle-journal",
      claimed: false,
      payload: {
        agentRef: "agent-synthetic-revoked",
        lifecycleKind: "revocation",
        generation: 1,
        revocationEpoch: 2
      }
    },
    {
      eventId: "evt-synthetic-alpha-012",
      eventKind: "agent_activity_event",
      correlationId: "corr-synthetic-alpha-012",
      occurredAtUtc: "2026-11-03T08:05:30Z",
      evidenceClass: "infrastructure_observed",
      sourceIdentity: "observatory-recorder",
      claimed: false,
      payload: {
        agentRef: "agent-synthetic-alpha",
        activityKind: "conversation_message"
      }
    }
  ]
};
