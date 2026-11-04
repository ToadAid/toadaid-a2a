import React from "react";
import { SunIcon, MoonIcon, ShieldIcon } from "../common/Icons";
import { BlueToby } from "../common/BlueToby";
import { useTheme } from "../../theme/ThemeContext";

interface HeaderProps {
  tenantRef: string;
  ownerRef: string;
}

export const Header: React.FC<HeaderProps> = ({ tenantRef, ownerRef }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <header
      className="sticky top-0 z-40 border-b backdrop-blur-md transition-colors"
      style={{
        background: "var(--color-surface-overlay)",
        borderColor: "var(--color-border-subtle)",
      }}
      role="banner"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3">
        {/* Brand & Blue Toby Mascot */}
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center shrink-0">
            {/* Desktop: 42px, Mobile: 38px */}
            <div className="hidden sm:block">
              <BlueToby size={42} />
            </div>
            <div className="block sm:hidden">
              <BlueToby size={38} />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-base sm:text-lg text-[var(--color-text-primary)]">
                ToadAid
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-[var(--color-gold-bg)] text-[var(--color-gold)] border border-[rgba(245,158,11,0.3)] font-semibold">
                Observatory
              </span>
            </div>
            <p className="text-[11px] text-[var(--color-text-dim)] hidden sm:block">
              A2A Sovereign Agent Telemetry & Seam Governance (Synthetic)
            </p>
          </div>
        </div>

        {/* Scope Context & Theme Switcher */}
        <div className="flex items-center gap-2.5">
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card)] text-xs font-mono">
            <span className="text-[var(--color-text-dim)]">Scope (Synthetic):</span>
            <span className="text-[var(--color-jade)] font-medium">{tenantRef}</span>
            <span className="text-[var(--color-border)]">/</span>
            <span className="text-[var(--color-gold)] font-medium">{ownerRef}</span>
          </div>

          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono text-[var(--color-jade)] border border-[var(--color-success-border)] bg-[var(--color-success-bg)]">
            <ShieldIcon size={14} />
            <span>Synthetic Fail-Closed Engine</span>
          </div>

          {/* Theme Switcher */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface-card-hover)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] cursor-pointer"
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          >
            {theme === "dark" ? <SunIcon size={18} /> : <MoonIcon size={18} />}
          </button>
        </div>
      </div>
    </header>
  );
};
