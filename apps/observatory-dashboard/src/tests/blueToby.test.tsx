import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import App from "../App";
import { BlueToby } from "../components/common/BlueToby";

describe("Blue Toby Mascot & Mobile Qualification Regressions", () => {
  it("renders Blue Toby mascot in the header with accessible alternative text", () => {
    render(<App />);
    const tobyImages = screen.getAllByAltText("ToadAid Blue Toby");
    expect(tobyImages.length).toBeGreaterThanOrEqual(2); // Header (desktop + mobile) + Footer
    tobyImages.forEach((img) => {
      expect(img).toBeInTheDocument();
      expect(img.tagName).toBe("IMG");
      expect(img).toHaveAttribute("src");
      expect(img.getAttribute("src")).toContain("blue-toby");
      expect(img).toHaveStyle({ objectFit: "contain", aspectRatio: "1 / 1" });
    });
  });

  it("renders all four critical mobile security invariants completely", () => {
    render(<App />);
    expect(screen.getByText(/SYNTHETIC PREVIEW — NO LIVE AGENTS/i)).toBeInTheDocument();
    // Verified always-truthful SYNTHETIC PREVIEW — NO LIVE AGENTS replaces temporary NOT DEPLOYED badge
    expect(screen.getByText(/A2A CHAT HAS ZERO EXECUTION AUTHORITY/i)).toBeInTheDocument();
    expect(screen.getAllByText(/AUTHORITY IS NEVER ASSUMED/i).length).toBeGreaterThanOrEqual(1);
  });

  it("supports mobile navigation drawer opening, view switching, and escape dismissal", () => {
    render(<App />);

    // Find the mobile menu toggle button
    const toggleButton = screen.getByLabelText(/Open all 5 views menu/i);
    expect(toggleButton).toBeInTheDocument();
    expect(toggleButton).toHaveAttribute("aria-expanded", "false");

    // Click toggle to open menu
    fireEvent.click(toggleButton);
    expect(toggleButton).toHaveAttribute("aria-expanded", "true");

    const mobileMenu = screen.getByRole("menu", { name: /All Observatory Views/i });
    expect(mobileMenu).toBeInTheDocument();

    // Verify all 5 views exist as menu items
    const menuItems = screen.getAllByRole("menuitem");
    expect(menuItems.length).toBe(5);

    // Switch view via mobile menu to "Security & Governance"
    const secItem = screen.getByRole("menuitem", { name: /Security & Governance/i });
    fireEvent.click(secItem);

    // Menu should be closed
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(screen.getByText(/REVOCATION_OVERRIDES_PRIOR_APPROVAL/i)).toBeInTheDocument();

    // Re-open and test Escape dismissal
    const reopenBtn = screen.getByLabelText(/Open all 5 views menu/i);
    fireEvent.click(reopenBtn);
    expect(screen.getByRole("menu")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("standalone BlueToby component preserves custom dimensions and alt text", () => {
    const { container } = render(<BlueToby size={44} alt="Custom Toby" className="test-class" />);
    const img = container.querySelector("img");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("width", "44");
    expect(img).toHaveAttribute("height", "44");
    expect(img).toHaveAttribute("alt", "Custom Toby");
    expect(img).toHaveClass("test-class");
  });
});
