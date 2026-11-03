import { describe, it, expect } from 'vitest';
import { ObservatoryAdapter, defaultAdapter } from '../services/observatoryAdapter';

describe('ObservatoryAdapter Contract Conformance', () => {
  it('conforms to the feed contract kind and version', () => {
    const feed = defaultAdapter.getFeed();
    expect(feed.kind).toBe('toadaid-observatory-owner-dashboard-feed');
    expect(feed.schemaVersion).toBe('0.1.0');
    expect(feed.status).toBe('SYNTHETIC_LOCAL_FOUNDATION_READ_ONLY');
    expect(feed.tenantRef).toBe('tenant-alpha');
    expect(feed.ownerRef).toBe('owner-alpha');
  });

  it('guarantees all authority flags are strictly false', () => {
    const flags = defaultAdapter.getAuthorityFlags();
    expect(flags.executionAuthorized).toBe(false);
    expect(flags.publicationAuthorized).toBe(false);
    expect(flags.deploymentAuthorized).toBe(false);
    expect(flags.agentRegistrationActive).toBe(false);
    expect(flags.publicDirectoryExposed).toBe(false);
  });

  it('calculates honest dashboard statistics', () => {
    const stats = defaultAdapter.getStats();
    expect(stats.totalEvents).toBeGreaterThanOrEqual(12);
    expect(stats.totalAgents).toBe(6);
    expect(stats.registeredCount).toBe(2);
    expect(stats.evidenceBreakdown.infrastructure_observed).toBeGreaterThan(0);
    expect(stats.evidenceBreakdown.agent_reported).toBeGreaterThan(0);
    expect(stats.evidenceBreakdown.human_authorized).toBeGreaterThan(0);
  });

  it('filters events by eventKind', () => {
    const events = defaultAdapter.filterEvents({
      eventKind: 'human_refusal_receipt',
    });
    expect(events.length).toBe(1);
    expect(events[0].eventId).toBe('evt-synthetic-alpha-003');
    expect(events[0].payload.objectionCode).toBe('PRIVACY');
  });

  it('filters events by evidenceClass', () => {
    const humanEvents = defaultAdapter.filterEvents({
      evidenceClass: 'human_authorized',
    });
    expect(humanEvents.length).toBe(2);
    humanEvents.forEach((evt) => {
      expect(evt.evidenceClass).toBe('human_authorized');
    });
  });

  it('filters claimed events accurately', () => {
    const claimedEvents = defaultAdapter.filterEvents({
      claimedOnly: true,
    });
    expect(claimedEvents.length).toBeGreaterThan(0);
    claimedEvents.forEach((evt) => {
      expect(evt.claimed).toBe(true);
    });
  });

  it('filters agents by search query and registration status', () => {
    const registered = defaultAdapter.filterAgents('', 'registered');
    expect(registered.length).toBe(2);

    const hermes = defaultAdapter.filterAgents('Hermes', 'all');
    expect(hermes.length).toBe(2);

    const nonexistent = defaultAdapter.filterAgents('non-existent-agent-id', 'all');
    expect(nonexistent.length).toBe(0);
  });

  it('formats calendar-real ISO UTC strings properly', () => {
    const formatted = ObservatoryAdapter.formatIsoUtc('2026-11-03T12:00:00Z');
    expect(formatted).toBe('2026-11-03 12:00:00 UTC');
  });
});
