import React, { useState, useEffect, useRef } from "react";
import type { ViewMode } from "../../types/observatory";
import { ActivityIcon, UsersIcon, ShieldIcon, RadioIcon, TerminalIcon, MenuIcon, CloseIcon } from "../common/Icons";

interface NavigationProps {
  currentView: ViewMode;
  onSelectView: (view: ViewMode) => void;
  eventCount: number;
  agentCount: number;
}

interface NavItem {
  id: ViewMode;
  label: string;
  icon: React.ReactNode;
  badge?: string | number;
}

export const Navigation: React.FC<NavigationProps> = ({
  currentView,
  onSelectView,
  eventCount,
  agentCount,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(() => {
    if (typeof window !== "undefined") {
      return new URLSearchParams(window.location.search).get("mobileNav") === "open";
    }
    return false;
  });
  const menuRef = useRef<HTMLDivElement>(null);

  const navItems: NavItem[] = [
    {
      id: "overview",
      label: "Observatory Overview",
      icon: <ActivityIcon size={18} />,
    },
    {
      id: "directory",
      label: "Directory Preview",
      icon: <UsersIcon size={18} />,
      badge: agentCount,
    },
    {
      id: "activity",
      label: "Agent Activity",
      icon: <TerminalIcon size={18} />,
      badge: eventCount,
    },
    {
      id: "communication",
      label: "Communication Vis",
      icon: <RadioIcon size={18} />,
    },
    {
      id: "security",
      label: "Security & Governance",
      icon: <ShieldIcon size={18} />,
      badge: "4 Seams",
    },
  ];

  const currentItem = navItems.find((item) => item.id === currentView) || navItems[0];

  // Close on Escape or click outside
  useEffect(() => {
    if (!mobileMenuOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileMenuOpen(false);
    };
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [mobileMenuOpen]);

  return (
    <nav
      className="border-b transition-colors relative z-30"
      style={{
        background: "var(--color-surface-card)",
        borderColor: "var(--color-border-subtle)",
      }}
      aria-label="Observatory Primary Navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* DESKTOP / TABLET HORIZONTAL TABS (md and up) */}
        <div className="hidden md:block">
          <ul className="flex items-center gap-2 py-2" role="tablist">
            {navItems.map((item) => {
              const isActive = currentView === item.id;
              return (
                <li key={item.id} role="presentation">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    aria-controls={`panel-${item.id}`}
                    id={`tab-${item.id}`}
                    onClick={() => onSelectView(item.id)}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs lg:text-sm font-medium transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] ${
                      isActive
                        ? "text-[var(--color-text-contrast)] font-semibold"
                        : "text-[var(--color-text-dim)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-card-hover)]"
                    }`}
                    style={{
                      background: isActive ? "var(--color-surface-elevated)" : "transparent",
                      border: isActive ? "1px solid var(--color-border)" : "1px solid transparent",
                      boxShadow: isActive ? "var(--shadow-sm)" : "none",
                    }}
                  >
                    <span
                      className={isActive ? "text-[var(--color-jade)]" : "text-[var(--color-text-dim)]"}
                      aria-hidden="true"
                    >
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                    {item.badge !== undefined && (
                      <span
                        className={`text-[11px] px-1.5 py-0.2 rounded-full font-mono ${
                          isActive
                            ? "bg-[var(--color-jade)] text-[var(--color-text-on-accent)] font-bold"
                            : "bg-[var(--color-border-subtle)] text-[var(--color-text-dim)]"
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        {/* MOBILE NAVIGATION BAR (< md) */}
        <div className="block md:hidden py-2" ref={menuRef}>
          <div className="flex items-center justify-between">
            {/* Active view indicator */}
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--color-text-primary)]">
              <span className="text-[var(--color-jade)]">{currentItem.icon}</span>
              <span>{currentItem.label}</span>
              {currentItem.badge !== undefined && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full font-mono bg-[var(--color-surface-elevated)] text-[var(--color-jade)] border border-[var(--color-border-subtle)]">
                  {currentItem.badge}
                </span>
              )}
            </div>

            {/* Mobile Menu Toggle Button (Min 44x44px touch target) */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-card-hover)] text-[var(--color-text-primary)] hover:border-[var(--color-border-focus)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] cursor-pointer"
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-views-menu"
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open all 5 views menu"}
            >
              {mobileMenuOpen ? <CloseIcon size={20} /> : <MenuIcon size={20} />}
            </button>
          </div>

          {/* Collapsible Full Views Menu */}
          {mobileMenuOpen && (
            <div
              id="mobile-views-menu"
              className="mt-2 py-2 border-t border-[var(--color-border-subtle)] space-y-1"
              role="menu"
              aria-label="All Observatory Views"
            >
              {navItems.map((item) => {
                const isActive = currentView === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="menuitem"
                    aria-current={isActive ? "page" : undefined}
                    onClick={() => {
                      onSelectView(item.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`w-full min-h-[44px] flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all text-left cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] ${
                      isActive
                        ? "text-[var(--color-text-contrast)] font-bold bg-[var(--color-surface-elevated)] border border-[var(--color-jade)]"
                        : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-card-hover)] border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className={isActive ? "text-[var(--color-jade)]" : "text-[var(--color-text-dim)]"}>
                        {item.icon}
                      </span>
                      <span>{item.label}</span>
                    </div>

                    {item.badge !== undefined && (
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-mono ${
                          isActive
                            ? "bg-[var(--color-jade)] text-[var(--color-text-on-accent)] font-bold"
                            : "bg-[var(--color-border-subtle)] text-[var(--color-text-dim)]"
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};
