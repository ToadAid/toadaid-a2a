import type { CommunicationScenario } from '../types/observatory';

export const SYNTHETIC_FLOW_SCENARIOS: CommunicationScenario[] = [
  {
    id: "flow-admitted-bilateral",
    title: "1. Verified Bilateral Delivery (Admitted)",
    description: "Sender and recipient both hold valid registration, current generation/epoch, same tenant context, and explicit send/receive scopes.",
    outcome: "admitted",
    sender: {
      agentRef: "agent-synthetic-one",
      tenantRef: "tenant-alpha",
      ownerRef: "owner-alpha",
      claimedGeneration: 3,
      claimedEpoch: 1
    },
    recipient: {
      agentRef: "agent-synthetic-alpha",
      tenantRef: "tenant-alpha",
      ownerRef: "owner-alpha",
      claimedGeneration: 2,
      claimedEpoch: 1
    },
    steps: [
      {
        name: "1. Caller Identity Seam",
        status: "passed",
        detail: "Caller credential verified against principal 'agent-synthetic-one'.",
        failClosedRule: "Self-asserted context cannot authenticate caller."
      },
      {
        name: "2. Registration Adapter Seam",
        status: "passed",
        detail: "Sender holds status 'registered' and scope 'a2a-message-send'. Recipient holds scope 'a2a-message-receive'.",
        failClosedRule: "Unregistered or wrong scope immediately refuses."
      },
      {
        name: "3. Credential Lifecycle Seam",
        status: "passed",
        detail: "Sender gen 3 == current 3, epoch 1 == current 1. Recipient gen 2 == current 2, epoch 1 == current 1.",
        failClosedRule: "Stale generation or epoch fails closed."
      },
      {
        name: "4. Trusted Clock Seam",
        status: "passed",
        detail: "Evidence expiry is 2026-11-03T18:00:00Z (valid for current time).",
        failClosedRule: "Expired ISO timestamp fails closed."
      },
      {
        name: "5. Tenant Isolation Seam",
        status: "passed",
        detail: "Both agents belong to 'tenant-alpha'. Cross-tenant boundary respected.",
        failClosedRule: "Cross-tenant messaging strictly prohibited."
      },
      {
        name: "6. Tamper-Evident Journal Record",
        status: "passed",
        detail: "An ILLUSTRATIVE journal-digest placeholder is shown; no digest is computed or verified anywhere in this offline synthetic console. Zero execution authority.",
        failClosedRule: "No delivery permitted without journal recording."
      }
    ],
    receiptPreview: {
      receiptId: "rec-synt-pond-9081",
      journalHash: "ILLUSTRATIVE-PLACEHOLDER — NOT A COMPUTED OR VERIFIED DIGEST",
      authorityFlags: {
        executionAuthorized: false,
        publicationAuthorized: false,
        deploymentAuthorized: false,
        agentRegistrationActive: false,
        publicDirectoryExposed: false
      },
      timestamp: "2026-11-03T08:05:30Z"
    }
  },
  {
    id: "flow-refused-stale-credential",
    title: "2. Stale Credential Generation (Refused)",
    description: "Sender attempts to authenticate with rotated credential generation (Gen 1 vs Current Gen 3).",
    outcome: "refused",
    refusalCode: "CREDENTIAL_GENERATION_STALE",
    sender: {
      agentRef: "agent-synthetic-one",
      tenantRef: "tenant-alpha",
      ownerRef: "owner-alpha",
      claimedGeneration: 1,
      claimedEpoch: 1
    },
    recipient: {
      agentRef: "agent-synthetic-alpha",
      tenantRef: "tenant-alpha",
      ownerRef: "owner-alpha",
      claimedGeneration: 2,
      claimedEpoch: 1
    },
    steps: [
      {
        name: "1. Caller Identity Seam",
        status: "passed",
        detail: "Caller credential verified against principal 'agent-synthetic-one'.",
        failClosedRule: "Self-asserted context cannot authenticate caller."
      },
      {
        name: "2. Registration Adapter Seam",
        status: "passed",
        detail: "Point-in-time adapter decision loaded.",
        failClosedRule: "Unregistered or wrong scope immediately refuses."
      },
      {
        name: "3. Credential Lifecycle Seam",
        status: "refused",
        detail: "REFUSED: Claimed gen 1 < Current gen 3 (rotation invalidated previous credential).",
        failClosedRule: "CREDENTIAL_GENERATION_STALE: Rotation immediately invalidates all prior decisions."
      },
      {
        name: "4. Tamper-Evident Journal",
        status: "refused",
        detail: "No journal entry written. Refusals do not contaminate audit chain.",
        failClosedRule: "Refusal halts processing before journal recording."
      }
    ]
  },
  {
    id: "flow-refused-revocation",
    title: "3. Revocation Override (Refused)",
    description: "Constitutional invariant REVOCATION_OVERRIDES_PRIOR_APPROVAL: Recipient has been revoked by operator.",
    outcome: "refused",
    refusalCode: "LIFECYCLE_STATUS_REVOKED",
    sender: {
      agentRef: "agent-synthetic-one",
      tenantRef: "tenant-alpha",
      ownerRef: "owner-alpha",
      claimedGeneration: 3,
      claimedEpoch: 1
    },
    recipient: {
      agentRef: "agent-synthetic-revoked",
      tenantRef: "tenant-alpha",
      ownerRef: "owner-alpha",
      claimedGeneration: 1,
      claimedEpoch: 2
    },
    steps: [
      {
        name: "1. Caller Identity Seam",
        status: "passed",
        detail: "Caller credential verified against principal 'agent-synthetic-one'.",
        failClosedRule: "Caller verified."
      },
      {
        name: "2. Sender Lifecycle Check",
        status: "passed",
        detail: "Sender state is registered and current.",
        failClosedRule: "Sender verified."
      },
      {
        name: "3. Recipient Lifecycle Seam",
        status: "refused",
        detail: "REFUSED: Recipient status is 'revoked' (Epoch 2).",
        failClosedRule: "REVOCATION_OVERRIDES_PRIOR_APPROVAL: A decision minted before revocation never authorizes afterwards."
      },
      {
        name: "4. Replay Protection",
        status: "refused",
        detail: "Identical message replay after revocation is refused fail-closed.",
        failClosedRule: "Replay cannot bypass lifecycle enforcement."
      }
    ]
  },
  {
    id: "flow-refused-cross-tenant",
    title: "4. Cross-Tenant Delivery (Refused)",
    description: "Sender 'tenant-alpha' attempts message delivery to 'tenant-gamma'. Strict boundary enforcement.",
    outcome: "refused",
    refusalCode: "CROSS_TENANT_DELIVERY_REFUSED",
    sender: {
      agentRef: "agent-synthetic-one",
      tenantRef: "tenant-alpha",
      ownerRef: "owner-alpha",
      claimedGeneration: 3,
      claimedEpoch: 1
    },
    recipient: {
      agentRef: "agent-synthetic-three",
      tenantRef: "tenant-gamma",
      ownerRef: "owner-foreign",
      claimedGeneration: 0,
      claimedEpoch: 0
    },
    steps: [
      {
        name: "1. Caller Identity Seam",
        status: "passed",
        detail: "Sender verified under 'tenant-alpha'.",
        failClosedRule: "Caller verified."
      },
      {
        name: "2. Tenant Matching Seam",
        status: "refused",
        detail: "REFUSED: Sender tenant 'tenant-alpha' != Recipient tenant 'tenant-gamma'.",
        failClosedRule: "CROSS_TENANT_DELIVERY_REFUSED: Same-tenant isolation is strictly enforced."
      },
      {
        name: "3. Journal Integrity",
        status: "refused",
        detail: "No cross-tenant journal entry created.",
        failClosedRule: "No journal entry written on cross-tenant refusal."
      }
    ]
  }
];
