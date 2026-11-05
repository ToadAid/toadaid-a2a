import React, { createContext, useContext, useEffect, useLayoutEffect, useState } from "react";
import type { ThemeMode } from "../types/observatory";

interface ThemeContextType {
  theme: ThemeMode;
  toggleTheme: () => void;
  setTheme: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    try {
      const urlTheme = new URLSearchParams(window.location.search).get("theme");
      if (urlTheme === "light" || urlTheme === "dark") return urlTheme;
      const saved = localStorage.getItem("toadaid_theme");
      if (saved === "light" || saved === "dark") return saved;
    } catch {
      // fallback
    }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  });

  // Theme tokens must be present before the committed controls can paint.
  useLayoutEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Preference persistence is not paint-critical.
  useEffect(() => {
    try {
      localStorage.setItem("toadaid_theme", theme);
    } catch {
      // ignore
    }
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const setTheme = (mode: ThemeMode) => {
    setThemeState(mode);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
};
