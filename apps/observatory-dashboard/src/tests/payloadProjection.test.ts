/**
 * A2A-UI-P0-R3 regression tests: fail-closed payload projection (R3-A),
 * safe payload search, and strict runtime authority-flag validation (R3-B).
 *
 * Canary strings used here are SYNTHETIC only — no real credential exists
 * or is referenced anywhere in these tests.
 */
import { describe, it, expect } from 'vitest';
import { ObservatoryAdapter, defaultAdapter } from '../services/observatoryAdapter';
import { projectPayload, projectedSearchText } from '../services/payloadProjection';
import { PRIMARY_SYNTHETIC_FEED } from '../data/syntheticFeed';
import type { ObservedItem, AuthorityFlags, EventKind } from '../types/observatory';

const CANARY_FIELD_NAMES = [
  'accessToken',
  'privateKey',
  'apiKey',
  'password',
  'rawPrompt',
  'messageBody',
  'walletSeed',
] as const;

// Synthetic canary VALUES — deliberately fake, never a real credential.
const canaryValue = (field: string) => `SYNTHETIC-CANARY-${field}-must-never-render`;

const projectionOf = (eventKind: EventKind, payload: unknown) =>
  JSON.stringify(projectPayload(eventKind, payload).fields);

describe('R3-A: fail-closed payload projection', () => {
  it('projects every trusted synthetic feed event without withholding anything', () => {
    for (const item of PRIMARY_SYNTHETIC_FEED.items) {
      const projected = projectPayload(item.eventKind, item.payload);
      expect(projected.withheldFieldCount).toBe(0);
      expect(projected.fields).toEqual(item.payload);
    }
  });

  it('withholds canary payload fields so their names and values never render', () => {
    for (const field of CANARY_FIELD_NAMES) {
      const payload = { agentRef: 'agent-synthetic-one', activityKind: 'task_update', [field]: canaryValue(field) };
      const projected = projectPayload('agent_activity_event', payload);
      expect(projected.fields[field as string]).toBeUndefined();
      expect(projected.withheldFieldCount).toBe(1);
      const text = projectionOf('agent_activity_event', payload);
      expect(text).not.toContain(field);
      expect(text).not.toContain(canaryValue(field));
    }
  });

  it('withholds a canary smuggled INTO the value of an allowlisted field', () => {
    const payload = {
      agentRef: canaryValue('privateKey').toUpperCase(), // violates the agentRef shape
      activityKind: 'task_update',
    };
    const projected = projectPayload('agent_activity_event', payload);
    expect(projected.fields.agentRef).toBeUndefined();
    expect(projected.withheldFieldCount).toBe(1);
    expect(projectionOf('agent_activity_event', payload)).not.toContain('SYNTHETIC-CANARY');
  });

  it('refuses nested objects and arrays of objects outright', () => {
    const nested = {
      agentRef: 'agent-synthetic-one',
      activityKind: 'task_update',
      nested: { deep: canaryValue('walletSeed') },
      participants: [{ leak: canaryValue('messageBody') }, 'agent-synthetic-alpha'],
    };
    const projected = projectPayload('agent_activity_event', nested);
    expect(projected.fields.nested).toBeUndefined();
    expect(projected.fields.participants).toBeUndefined();
    expect(projected.withheldFieldCount).toBe(2);
    const text = projectionOf('agent_activity_event', nested);
    expect(text).not.toContain('deep');
    expect(text).not.toContain(canaryValue('walletSeed'));
    expect(text).not.toContain(canaryValue('messageBody'));
  });

  it('bounds string lengths and non-conforming types out of the projection', () => {
    const overlong = 'a'.repeat(300);
    const payload = {
      agentRef: overlong,
      activityKind: 'task_update',
      wrongType: 42,
    };
    const projected = projectPayload('agent_activity_event', payload);
    expect(projected.fields.agentRef).toBeUndefined();
    expect(projected.withheldFieldCount).toBe(2);
  });

  it('bounds integers and enums out of the projection', () => {
    const payload = { turnCount: 9_999_999, lifecycleKind: 'recovery', agentRef: 'agent-synthetic-one' };
    const projected = projectPayload('lifecycle_security_event', payload);
    expect(projected.fields.turnCount).toBeUndefined();
    expect(projected.fields.lifecycleKind).toBe('recovery');
    expect(projected.withheldFieldCount).toBe(1);
  });

  it('fails closed for unknown event kinds and non-object payloads', () => {
    const payload = { agentRef: 'agent-synthetic-one', accessToken: canaryValue('apiKey') };
    const unknown = projectPayload('not_a_known_kind' as EventKind, payload);
    expect(unknown.fields).toEqual({});
    expect(unknown.withheldFieldCount).toBe(2);

    const nonObject = projectPayload('agent_activity_event', 'raw-string-payload');
    expect(nonObject.fields).toEqual({});
    expect(nonObject.withheldFieldCount).toBe(1);
  });

  it('safe search text exposes allowlisted values but never withheld data', () => {
    const payload = {
      conversationId: 'conv-synt-pond-081',
      turnCount: 4,
      participants: ['agent-synthetic-one'],
      rawPrompt: canaryValue('rawPrompt'),
    };
    const text = projectedSearchText('a2a_conversation_metadata', payload);
    expect(text).toContain('pond-081');
    expect(text).not.toContain(canaryValue('rawPrompt'));
    expect(text).not.toContain('rawprompt');
  });

  it('adapter payload search uses the projection, never the raw payload', () => {
    const maliciousItem: ObservedItem = {
      eventKind: 'agent_activity_event',
      eventId: 'evt-canary-001',
      correlationId: 'corr-canary-001',
      occurredAtUtc: '2026-11-03T09:00:00Z',
      evidenceClass: 'agent_reported',
      sourceIdentity: 'agent-synthetic-one',
      claimed: true,
      payload: {
        agentRef: 'agent-synthetic-one',
        activityKind: 'task_update',
        accessToken: canaryValue('accessToken'),
        privateKey: canaryValue('privateKey'),
      },
    };
    const feed = {
      ...PRIMARY_SYNTHETIC_FEED,
      items: [...PRIMARY_SYNTHETIC_FEED.items, maliciousItem],
    };
    const adapter = new ObservatoryAdapter(feed);

    const secretHits = adapter.filterEvents({ searchQuery: canaryValue('accessToken').slice(-14) });
    expect(secretHits).toEqual([]);
    const keyNameHits = adapter.filterEvents({ searchQuery: 'accesstoken' });
    expect(keyNameHits).toEqual([]);

    const legitimate = adapter.filterEvents({ searchQuery: 'pond-081' });
    expect(legitimate.map((item) => item.eventId)).toEqual(['evt-synthetic-alpha-004']);
  });
});

describe('R3-B: strict runtime authority-flag validation', () => {
  const validFlags: AuthorityFlags = {
    executionAuthorized: false,
    publicationAuthorized: false,
    deploymentAuthorized: false,
    agentRegistrationActive: false,
    publicDirectoryExposed: false,
  };

  it('accepts exactly the five strictly-false flags', () => {
    const result = ObservatoryAdapter.validateAuthorityFlags(validFlags);
    expect(result.valid).toBe(true);
    expect(result.problems).toEqual([]);
  });

  it('rejects missing required flags', () => {
    const { executionAuthorized, ...missing } = validFlags;
    const result = ObservatoryAdapter.validateAuthorityFlags(missing);
    expect(result.valid).toBe(false);
    expect(result.problems.some((problem) => problem.includes('missing required authority flag'))).toBe(true);
  });

  it('rejects unexpected extra flags without echoing their names', () => {
    const extra = { ...validFlags, shadowFlag: false } as unknown as Record<string, unknown>;
    const result = ObservatoryAdapter.validateAuthorityFlags(extra);
    expect(result.valid).toBe(false);
    expect(result.problems.some((problem) => problem.includes('unexpected extra authority flags'))).toBe(true);
    expect(result.problems.join(' ')).not.toContain('shadowFlag');
  });

  it('rejects a runtime TRUE value instead of rendering it as enforced', () => {
    const asserted = { ...validFlags, executionAuthorized: true } as unknown as AuthorityFlags;
    const result = ObservatoryAdapter.validateAuthorityFlags(asserted);
    expect(result.valid).toBe(false);
    expect(result.problems.some((problem) => problem.includes('not strictly boolean false'))).toBe(true);
  });

  it('rejects non-boolean flag values', () => {
    const stringified = { ...validFlags, deploymentAuthorized: 'false' } as unknown as AuthorityFlags;
    expect(ObservatoryAdapter.validateAuthorityFlags(stringified).valid).toBe(false);
    expect(ObservatoryAdapter.validateAuthorityFlags(null).valid).toBe(false);
    expect(ObservatoryAdapter.validateAuthorityFlags('flags').valid).toBe(false);
    expect(ObservatoryAdapter.validateAuthorityFlags([]).valid).toBe(false);
  });

  it('the trusted synthetic feed passes strict validation', () => {
    expect(ObservatoryAdapter.validateAuthorityFlags(defaultAdapter.getAuthorityFlags()).valid).toBe(true);
  });
});