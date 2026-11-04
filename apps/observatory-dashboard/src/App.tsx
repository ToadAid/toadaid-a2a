import React from "react";
import { ThemeProvider } from "./theme/ThemeContext";
import { AppShell } from "./components/layout/AppShell";

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppShell />
    </ThemeProvider>
  );
};

export default App;
