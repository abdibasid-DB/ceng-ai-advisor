function HomePage({ onNavigate }) {
  const sampleQuestions = [
    "What is Computer Engineering?",
    "What courses are taught in Computer Engineering?",
    "What programming languages should I learn?",
    "What careers can Computer Engineering graduates pursue?",
  ];

  return (
    <section className="page-section home-page" aria-labelledby="home-title">
      <div className="home-hero">
        <div>
          <p className="eyebrow">University project</p>
          <h1 id="home-title">AI-Powered Computer Engineering Student Advisor</h1>
          <p className="hero-copy">
            A source-grounded local AI advisor that helps students explore Computer Engineering education, curriculum,
            skills, careers, internships, and future technology topics.
          </p>
          <div className="action-row">
            <button type="button" className="primary-button" onClick={() => onNavigate("advisor")}>
              Ask the AI Advisor
            </button>
            <button type="button" className="secondary-button" onClick={() => onNavigate("sources")}>
              View Knowledge Sources
            </button>
          </div>
        </div>
        <div className="summary-panel" aria-label="Project summary">
          <p className="summary-number">56</p>
          <p>approved knowledge sources support the advisor's answers and source cards.</p>
        </div>
      </div>

      <section className="content-band" aria-labelledby="topics-title">
        <h2 id="topics-title">What You Can Ask About</h2>
        <div className="feature-grid">
          {[
            "What Computer Engineering is",
            "Curriculum and course topics",
            "Programming and technical skills",
            "Career opportunities",
            "Internships and workplace learning",
            "AI, cybersecurity, and future technologies",
            "Graduate study directions",
            "When evidence is not enough",
          ].map((item) => (
            <article className="feature-card" key={item}>
              <h3>{item}</h3>
            </article>
          ))}
        </div>
      </section>

      <section className="content-band" aria-labelledby="sample-questions-title">
        <h2 id="sample-questions-title">Sample Questions</h2>
        <div className="feature-grid">
          {sampleQuestions.map((question) => (
            <article className="feature-card" key={question}>
              <h3>{question}</h3>
              <button type="button" className="secondary-button" onClick={() => onNavigate("advisor")}>
                Ask in Advisor
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="content-band" aria-labelledby="how-title">
        <h2 id="how-title">How It Works</h2>
        <ol className="process-list">
          <li>Ask a Computer Engineering question.</li>
          <li>The system searches the curated knowledge base.</li>
          <li>Relevant passages are retrieved as evidence.</li>
          <li>A local AI model creates an answer from that evidence.</li>
          <li>Sources are displayed so the answer can be checked.</li>
        </ol>
      </section>
    </section>
  );
}

export default HomePage;
