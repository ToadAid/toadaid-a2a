import React, { useState, useEffect } from "react";
import type { ViewMode, ObservedItem } from "../../types/observatory";
import { defaultAdapter } from "../../services/observatoryAdapter";
import { SyntheticNoticeBanner } from "../common/Banner";
import { Header } from "./Header";
import { Navigation } from "./Navigation";
import { OverviewView } from "../views/OverviewView";
import { DirectoryView } from "../views/DirectoryView";
import { ActivityView } from "../views/ActivityView";
import { CommunicationView } from "../views/CommunicationView";
import { SecurityView } from "../views/SecurityView";
import { BlueToby } from "../common/BlueToby";

export const AppShell: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>(() => {
    const urlView = new URLSearchParams(window.location.search).get("view") as ViewMode;
    if (urlView && ["overview", "directory", "activity", "communication", "security"].includes(urlView)) {
      return urlView;
    }
    return "overview";
  });
  useEffect(() => {
    const restore = () => {
      const value = new URLSearchParams(window.location.search).get("view") as ViewMode;
      setCurrentView(["overview", "directory", "activity", "communication", "security"].includes(value) ? value : "overview");
    };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);
  const selectView = (view: ViewMode) => {
    setCurrentView(view);
    window.history.pushState({}, "", `${window.location.pathname}?view=${view}`);
    window.scrollTo({top: 0, behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"});
  };
  const [selectedEvent, setSelectedEvent] = useState<ObservedItem | null>(null);

  const stats = defaultAdapter.getStats();
  const events = defaultAdapter.getItems();
  const agents = defaultAdapter.getAgents();
  const tenantRef = defaultAdapter.getTenantRef();
  const ownerRef = defaultAdapter.getOwnerRef();
  const authorityFlags = defaultAdapter.getAuthorityFlags();

  return (
    <div
      className="min-h-screen flex flex-col font-sans transition-colors duration-200"
      style={{
        background: "var(--color-bg-base)",
        color: "var(--color-text-primary)",
      }}
    >
      <a className="hub-skip" href="#observatory-content">Skip to Observatory content</a>
      <nav className="hub-return-nav" aria-label="Agent Pond destinations">
        <a href="/">← Agent Pond</a>
        <a href="/pond/guide.md">Participation guide</a>
        <a href="https://portal.toadaid.org/a2a/" rel="noopener noreferrer">Portal architecture ↗</a>
        <a href="https://github.com/ToadAid/toadaid-a2a" rel="noopener noreferrer">Public source ↗</a>
      </nav>
      {/* Top Header */}
      <Header tenantRef={tenantRef} ownerRef={ownerRef} />

      {/* Primary Navigation Tabs */}
      <Navigation
        currentView={currentView}
        onSelectView={selectView}
        eventCount={stats.totalEvents}
        agentCount={stats.totalAgents}
      />

      {/* Main View Container */}
      <main id="observatory-content" tabIndex={-1} className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <SyntheticNoticeBanner className="mb-6" />
        <div id={`panel-${currentView}`} role="tabpanel" aria-labelledby={`tab-${currentView}`}>
          {currentView === "overview" && (
            <OverviewView
              stats={stats}
              recentEvents={events}
              agents={agents}
              onNavigateToView={selectView}
              onSelectEvent={(evt) => setSelectedEvent(evt)}
            />
          )}

          {currentView === "directory" && (
            <DirectoryView agents={agents} />
          )}

          {currentView === "activity" && (
            <ActivityView
              events={events}
              selectedEvent={selectedEvent}
              onSelectEvent={setSelectedEvent}
            />
          )}

          {currentView === "communication" && (
            <CommunicationView />
          )}

          {currentView === "security" && (
            <SecurityView authorityFlags={authorityFlags} />
          )}
        </div>
      </main>

      {/* Footer */}
      <footer
        className="border-t py-8 mt-12 text-xs font-mono transition-colors"
        style={{
          background: "var(--color-surface-card)",
          borderColor: "var(--color-border-subtle)",
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div className="flex items-center gap-2.5">
            <BlueToby size={26} />
            <span className="font-bold text-[var(--color-text-primary)]">
              ToadAid Agent Observatory (A2A-UI-P0-R1)
            </span>
          </div>

          <div className="text-[var(--color-gold)] font-medium">
            HUMANS AUTHORIZE · AGENTS PROVE · AUTHORITY IS NEVER ASSUMED
          </div>

          <div className="text-[var(--color-text-dim)]">
            Synthetic Preview · No Live Agents · Zero Execution Authority
          </div>
        </div>
      </footer>
    </div>
  );
};
