import { useEffect, useState } from "react";

const NAV_ITEMS = [
  { id: "home", label: "Home" },
  { id: "advisor", label: "AI Advisor" },
  { id: "computer-engineering", label: "Computer Engineering" },
  { id: "sources", label: "Sources" },
  { id: "about-project", label: "About Project" },
];

function WebsiteLayout({ currentPage, onNavigate, children }) {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem("advisor-theme") || "system"; }
    catch { return "system"; }
  });
  useEffect(() => {
    const system = window.matchMedia("(prefers-color-scheme: dark)");
    function applyTheme() {
      document.documentElement.dataset.theme = theme === "system" ? (system.matches ? "dark" : "light") : theme;
    }
    applyTheme();
    system.addEventListener("change", applyTheme);
    try { localStorage.setItem("advisor-theme", theme); } catch { /* Storage may be disabled. */ }
    return () => system.removeEventListener("change", applyTheme);
  }, [theme]);
  return (
    <div className="site-shell">
      <header className="site-header">
        <a
          className="site-brand"
          href="#home"
          onClick={(event) => {
            event.preventDefault();
            onNavigate("home");
          }}
        >
          <span className="brand-mark">AI</span>
          <span>
            <strong>Computer Engineering Advisor</strong>
            <small>Source-grounded local AI</small>
          </span>
        </a>

        <nav className="site-nav" aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              aria-current={currentPage === item.id ? "page" : undefined}
              onClick={(event) => {
                event.preventDefault();
                onNavigate(item.id);
              }}
            >
              {item.label}
            </a>
          ))}
        </nav>
        <label className="theme-control">
          Theme
          <select value={theme} onChange={(event) => setTheme(event.target.value)}>
            <option value="system">System</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </label>
      </header>

      <main className="site-main">{children}</main>

      <footer className="site-footer">
        <p>AI-Powered Computer Engineering Student Advisor</p>
        <p>University project demonstrating source-grounded local AI with FastAPI, ChromaDB, Ollama, React, and Vite.</p>
      </footer>
    </div>
  );
}

export default WebsiteLayout;
