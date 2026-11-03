import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../App';

describe('ToadAid Agent Observatory App Shell', () => {
  it('renders application brand, header, and scope', () => {
    render(<App />);
    expect(screen.getByText('ToadAid')).toBeInTheDocument();
    expect(screen.getByText('Observatory')).toBeInTheDocument();
    expect(screen.getByText('tenant-alpha')).toBeInTheDocument();
    expect(screen.getByText('owner-alpha')).toBeInTheDocument();
  });

  it('renders prominent synthetic foundation disclaimer', () => {
    render(<App />);
    expect(
      screen.getByText(/STATUS: LOCAL SYNTHETIC FOUNDATION/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/A2A CHAT HAS ZERO EXECUTION AUTHORITY/i)
    ).toBeInTheDocument();
  });

  it('navigates between all authorized dashboard tabs', () => {
    render(<App />);

    // Directory Preview
    const dirTab = screen.getByRole('tab', { name: /Directory Preview/i });
    fireEvent.click(dirTab);
    expect(
      screen.getByText(/SYNTHETIC DIRECTORY PREVIEW — NOT PUBLIC/i)
    ).toBeInTheDocument();

    // Agent Activity
    const activityTab = screen.getByRole('tab', { name: /Agent Activity/i });
    fireEvent.click(activityTab);
    expect(
      screen.getByText(/Observed Telemetry Records/i)
    ).toBeInTheDocument();

    // Communication Visualization
    const commTab = screen.getByRole('tab', { name: /Communication Vis/i });
    fireEvent.click(commTab);
    expect(
      screen.getByText(/RegisteredAgentGate/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/A2A Multi-Agent Admission Pipeline/i)
    ).toBeInTheDocument();

    // Security & Governance
    const secTab = screen.getByRole('tab', { name: /Security & Governance/i });
    fireEvent.click(secTab);
    expect(
      screen.getByText(/REVOCATION_OVERRIDES_PRIOR_APPROVAL/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Immutable Authority Flag Block/i)
    ).toBeInTheDocument();
  });

  it('toggles dark and light themes smoothly', () => {
    render(<App />);
    const themeBtn = screen.getByLabelText(/Switch to/i);
    const initialTheme = document.documentElement.getAttribute('data-theme');

    fireEvent.click(themeBtn);
    const nextTheme = document.documentElement.getAttribute('data-theme');
    expect(nextTheme).not.toBe(initialTheme);
  });
});
