const NAV_ITEMS = [
  { id: "home", label: "Home" },
  { id: "advisor", label: "AI Advisor" },
  { id: "computer-engineering", label: "Computer Engineering" },
  { id: "sources", label: "Sources" },
  { id: "about-project", label: "About Project" },
];

function WebsiteLayout({ currentPage, onNavigate, children }) {
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
