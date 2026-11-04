import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../App';

describe('ToadAid Agent Observatory Accessibility & Invariant Checks', () => {
  it('contains proper semantic landmarks and ARIA roles', () => {
    render(<App />);

    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: /Observatory Primary Navigation/i })).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
    expect(screen.getByRole('tablist')).toBeInTheDocument();
  });

  it('renders all disabled administrative controls with explicit Director authorization requirement', () => {
    render(<App />);

    const secTab = screen.getByRole('tab', { name: /Security & Governance/i });
    fireEvent.click(secTab);

    const disabledButtons = screen.getAllByRole('button', {
      name: /NOT IMPLEMENTED — DIRECTOR AUTHORIZATION REQUIRED/i,
    });
    expect(disabledButtons.length).toBeGreaterThanOrEqual(3);
    disabledButtons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });

  it('supports keyboard modal open and Escape key dismiss in activity view', () => {
    render(<App />);

    const activityTab = screen.getByRole('tab', { name: /Agent Activity/i });
    fireEvent.click(activityTab);

    // Click inspect on the first item
    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    // Modal should be open
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');

    // Press Escape to dismiss
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
