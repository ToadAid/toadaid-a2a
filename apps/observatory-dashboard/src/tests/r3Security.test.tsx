/**
 * A2A-UI-P0-R3 component-level regression tests:
 *  - R3-A: canaries never reach the rendered ActivityView interface
 *          (display or search) — SYNTHETIC canary strings only.
 *  - R3-B: SecurityView renders "ENFORCED FALSE" only for strictly
 *          conforming data and fails closed on invalid data.
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React, { useState } from 'react';
import { ActivityView } from '../components/views/ActivityView';
import { SecurityView } from '../components/views/SecurityView';
import { PRIMARY_SYNTHETIC_FEED } from '../data/syntheticFeed';
import type { ObservedItem, AuthorityFlags } from '../types/observatory';

const CANARY = 'SYNTHETIC-CANARY-secret-must-never-render';

const maliciousItem: ObservedItem = {
  eventKind: 'agent_activity_event',
  eventId: 'evt-canary-100',
  correlationId: 'corr-canary-100',
  occurredAtUtc: '2026-11-03T10:00:00Z',
  evidenceClass: 'agent_reported',
  sourceIdentity: 'agent-synthetic-one',
  claimed: true,
  payload: {
    agentRef: 'agent-synthetic-one',
    activityKind: 'task_update',
    accessToken: CANARY,
    privateKey: CANARY,
    apiKey: CANARY,
    password: CANARY,
    rawPrompt: CANARY,
    messageBody: CANARY,
    walletSeed: CANARY,
  },
};

const VALID_FLAGS: AuthorityFlags = {
  executionAuthorized: false,
  publicationAuthorized: false,
  deploymentAuthorized: false,
  agentRegistrationActive: false,
  publicDirectoryExposed: false,
};

function ActivityHarness({ items }: { items: ObservedItem[] }) {
  const [selected, setSelected] = useState<ObservedItem | null>(null);
  return <ActivityView events={items} selectedEvent={selected} onSelectEvent={setSelected} />;
}

function bodyText(): string {
  return document.body.textContent ?? '';
}

describe('R3-A: ActivityView never renders canary payload data', () => {
  it('the inspector modal and search results exclude canary fields and values', () => {
    render(<ActivityHarness items={[...PRIMARY_SYNTHETIC_FEED.items, maliciousItem]} />);

    // Search for the synthetic canary value: NO result row may appear.
    const search = screen.getByRole('textbox') as HTMLInputElement;
    fireEvent.change(search, { target: { value: CANARY } });
    expect(screen.queryByText('evt-canary-100')).toBeNull();
    expect(screen.getByText('No events match the selected filters.')).toBeTruthy();

    // Search for the raw field name: also no raw-payload leakage.
    fireEvent.change(search, { target: { value: 'privatekey' } });
    expect(screen.queryByText('evt-canary-100')).toBeNull();

    // Open the inspector for the canary-carrying record (last row).
    fireEvent.change(search, { target: { value: '' } });
    const inspectButtons = screen.getAllByRole('button', { name: 'Inspect' });
    fireEvent.click(inspectButtons[inspectButtons.length - 1]);

    const text = bodyText();
    for (const field of ['accessToken', 'privateKey', 'apiKey', 'password', 'rawPrompt', 'messageBody', 'walletSeed']) {
      expect(text.includes(field)).toBe(false);
    }
    expect(text.includes(CANARY)).toBe(false);

    // The fail-closed withheld notice IS shown.
    expect(screen.getByText(/FAIL-CLOSED REDACTION: 7/)).toBeTruthy();

    // Allowlisted projection still renders.
    expect(screen.getByText(/fail-closed allowlisted projection/)).toBeTruthy();
  });

  it('allowlisted trusted events still project unchanged in the inspector', () => {
    render(<ActivityHarness items={PRIMARY_SYNTHETIC_FEED.items} />);
    fireEvent.click(screen.getAllByRole('button', { name: 'Inspect' })[0]);
    expect(screen.getByLabelText('Allowlisted event payload projection').textContent).toContain(
      'agent-synthetic-one'
    );
    expect(bodyText()).not.toContain('FAIL-CLOSED REDACTION');
  });
});

describe('R3-B: SecurityView fails closed on invalid authority-flag data', () => {
  it('renders ENFORCED FALSE exactly five times for strictly conforming data', () => {
    render(<SecurityView authorityFlags={VALID_FLAGS} />);
    expect(screen.getAllByText('ENFORCED FALSE')).toHaveLength(5);
    expect(screen.queryByText(/AUTHORITY FLAG DATA INVALID/)).toBeNull();
    // Constitutional invariant preserved.
    expect(bodyText()).toContain('A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY');
  });

  const invalidCases: [string, unknown][] = [
    ['a runtime TRUE flag', { ...VALID_FLAGS, executionAuthorized: true }],
    ['a missing required flag', { publicationAuthorized: false, deploymentAuthorized: false, agentRegistrationActive: false, publicDirectoryExposed: false }],
    ['an unexpected extra flag', { ...VALID_FLAGS, shadowFlag: false } as unknown],
    ['a non-boolean string value', { ...VALID_FLAGS, deploymentAuthorized: 'false' } as unknown],
    ['non-object data', null],
  ];

  for (const [label, invalid] of invalidCases) {
    it(`shows NO "ENFORCED FALSE" and a fail-closed warning for ${label}`, () => {
      render(<SecurityView authorityFlags={invalid as unknown as AuthorityFlags} />);
      // R4 strengthening: substring-level assertion — the phrase must not
      // appear anywhere in the rendered DOM, including inside paragraph text.
      expect(bodyText().includes('ENFORCED FALSE')).toBe(false);
      expect(screen.queryAllByText('ENFORCED FALSE')).toHaveLength(0);
      expect(screen.getByLabelText('Invalid authority flag state')).toBeTruthy();
      expect(bodyText()).toContain('AUTHORITY FLAG DATA INVALID');
      // Constitutional invariant still preserved on the invalid path.
      expect(bodyText()).toContain('A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY');
    });
  }

  it('never echoes unexpected extra flag names into the interface', () => {
    const polluted = { ...VALID_FLAGS, accessToken: false, shadowFlag: true } as unknown as AuthorityFlags;
    render(<SecurityView authorityFlags={polluted} />);
    expect(bodyText().includes('accessToken')).toBe(false);
    expect(bodyText().includes('shadowFlag')).toBe(false);
    expect(bodyText().includes('ENFORCED FALSE')).toBe(false);
    expect(screen.queryAllByText('ENFORCED FALSE')).toHaveLength(0);
  });
});