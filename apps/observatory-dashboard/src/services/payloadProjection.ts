/**
 * Fail-closed, event-kind-specific payload projection (A2A-UI-P0-R3-A).
 *
 * The payload contract allows arbitrary extra keys (`[key: string]: unknown`),
 * so payload data is NEVER trusted for display or search. Every value rendered
 * in the interface, and every string fed to payload search, must come out of
 * this projection:
 *   - Only allowlisted metadata fields for the event's kind may pass.
 *   - Each field is bounded in type, length, and (where known) character set.
 *   - Nested objects / arrays of objects are refused outright.
 *   - Unexpected or non-conforming fields are WITHHELD — neither their key
 *     names nor their values ever reach the rendered interface or search
 *     results (the withheld count alone is exposed).
 *
 * This projection is a browser-side safeguard for the trusted synthetic feed.
 * It is not the trust boundary: for a future production data source, real
 * private data must be excluded by trusted server-side projection BEFORE it
 * reaches the browser.
 */

import type { EventKind } from "../types/observatory";

/* ------------------------------------------------------------------ */
/* Bounded field validators                                            */
/* ------------------------------------------------------------------ */

const REGISTRATION_STATUSES = new Set([
  "registered",
  "revoked",
  "suspended",
  "unregistered",
  "unknown",
]);

const REQUEST_STATES = new Set(["requested", "authorized", "refused"]);

const LIFECYCLE_KINDS = new Set([
  "rotation",
  "revocation",
  "emergency_disable",
  "recovery",
]);

type FieldSpec =
  | { kind: "string"; pattern: RegExp; maxLength: number }
  | { kind: "enum"; allowed: ReadonlySet<string> }
  | { kind: "int"; maxValue: number }
  | { kind: "string-array"; itemPattern: RegExp; itemMaxLength: number; maxItems: number };

// Lowercase-hyphen agent/reference identifiers, e.g. "agent-synthetic-one".
const AGENT_REF: FieldSpec = { kind: "string", pattern: /^[a-z][a-z0-9-]{1,63}$/, maxLength: 64 };
// Lowercase-hyphen metadata identifiers, e.g. "conv-synt-pond-081", "dec-synthetic-003".
const METADATA_ID: FieldSpec = { kind: "string", pattern: /^[a-z0-9][a-z0-9-]{0,127}$/, maxLength: 128 };
// Lowercase snake_case vocabularies, e.g. "task_update", "read_water_temperature".
const SNAKE_KIND: FieldSpec = { kind: "string", pattern: /^[a-z][a-z0-9_]{0,63}$/, maxLength: 64 };
// Uppercase refusal/objection codes, e.g. "PRIVACY".
const UPPER_CODE: FieldSpec = { kind: "string", pattern: /^[A-Z][A-Z0-9_]{0,63}$/, maxLength: 64 };
// Lowercase vocabulary with hyphens or underscores, e.g. "independent-off-chat-human-process".
const CHANNEL_KIND: FieldSpec = { kind: "string", pattern: /^[a-z][a-z0-9_-]{0,63}$/, maxLength: 64 };

const SPEC: Record<string, FieldSpec> = {
  agentRef: AGENT_REF,
  registrationStatus: { kind: "enum", allowed: REGISTRATION_STATUSES },
  activityKind: SNAKE_KIND,
  conversationId: METADATA_ID,
  turnCount: { kind: "int", maxValue: 1_000_000 },
  participants: { kind: "string-array", itemPattern: AGENT_REF.pattern, itemMaxLength: 64, maxItems: 16 },
  toolName: SNAKE_KIND,
  requestState: { kind: "enum", allowed: REQUEST_STATES },
  authorizationGrantRef: METADATA_ID,
  decisionChannel: CHANNEL_KIND,
  decisionId: METADATA_ID,
  subjectKind: SNAKE_KIND,
  subjectRef: AGENT_REF,
  objectionCode: UPPER_CODE,
  lifecycleKind: { kind: "enum", allowed: LIFECYCLE_KINDS },
  generation: { kind: "int", maxValue: 1_000_000 },
  revocationEpoch: { kind: "int", maxValue: 1_000_000 },
};

// Per-event-kind allowlist, aligned exactly with the recorded feed vocabulary.
const KIND_ALLOWLIST: Record<EventKind, string[]> = {
  agent_identity_reference: ["agentRef", "registrationStatus"],
  agent_activity_event: ["agentRef", "activityKind"],
  a2a_conversation_metadata: ["conversationId", "turnCount", "participants"],
  mcp_tool_request_metadata: ["toolName", "requestState", "authorizationGrantRef"],
  human_authorization_receipt: ["decisionChannel", "decisionId", "subjectKind", "subjectRef"],
  human_refusal_receipt: ["decisionChannel", "decisionId", "subjectKind", "subjectRef", "objectionCode"],
  lifecycle_security_event: ["agentRef", "lifecycleKind", "generation", "revocationEpoch"],
};

export type ProjectedFieldValue = string | number | string[];

export interface ProjectedPayload {
  /** Allowlisted, validated, bounded fields only — safe to render and search. */
  fields: Record<string, ProjectedFieldValue>;
  /** Number of payload fields withheld (key names AND values are never exposed). */
  withheldFieldCount: number;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validateField(spec: FieldSpec, value: unknown): ProjectedFieldValue | null {
  switch (spec.kind) {
    case "string":
      if (typeof value !== "string" || value.length > spec.maxLength || !spec.pattern.test(value)) {
        return null;
      }
      return value;
    case "enum":
      if (typeof value !== "string" || !spec.allowed.has(value)) {
        return null;
      }
      return value;
    case "int":
      if (typeof value !== "number" || !Number.isInteger(value) || value < 0 || value > spec.maxValue) {
        return null;
      }
      return value;
    case "string-array": {
      if (!Array.isArray(value) || value.length > spec.maxItems) {
        return null;
      }
      const items: string[] = [];
      for (const item of value) {
        if (
          typeof item !== "string" ||
          item.length > spec.itemMaxLength ||
          !spec.itemPattern.test(item)
        ) {
          return null; // Any non-conforming member fails the whole field.
        }
        items.push(item);
      }
      return items;
    }
  }
}

/**
 * Project a payload to its safe, allowlisted form for the given event kind.
 * Never throws: any malformed input fails closed to an empty projection.
 */
export function projectPayload(eventKind: EventKind, payload: unknown): ProjectedPayload {
  const allowlist = KIND_ALLOWLIST[eventKind];
  const fields: Record<string, ProjectedFieldValue> = {};
  let withheldFieldCount = 0;

  if (!isPlainObject(payload)) {
    // A non-object payload can carry anything; it is withheld wholesale.
    return { fields, withheldFieldCount: payload === undefined ? 0 : 1 };
  }

  if (!allowlist) {
    // Unknown event kind: fail closed, withhold everything.
    return { fields, withheldFieldCount: Object.keys(payload).length };
  }

  const allowlistSet = new Set(allowlist);
  for (const key of Object.keys(payload)) {
    const spec = allowlistSet.has(key) ? SPEC[key] : undefined;
    if (spec !== undefined) {
      const validated = validateField(spec, payload[key]);
      if (validated !== null) {
        fields[key] = validated;
        continue;
      }
    }
    withheldFieldCount += 1; // Unexpected key OR failed validation: withheld entirely.
  }

  return { fields, withheldFieldCount };
}

/**
 * Safe search text for a payload: the allowlisted projection only (values,
 * never raw JSON of the unprojected payload, never withheld key names).
 */
export function projectedSearchText(eventKind: EventKind, payload: unknown): string {
  return JSON.stringify(projectPayload(eventKind, payload).fields).toLowerCase();
}