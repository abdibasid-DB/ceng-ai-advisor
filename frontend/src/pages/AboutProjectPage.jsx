function AboutProjectPage() {
  return (
    <section className="page-section info-page" aria-labelledby="about-project-title">
      <p className="eyebrow">Project overview</p>
      <h1 id="about-project-title">About This Project</h1>
      <p className="page-intro">
        This university project demonstrates a local, source-grounded AI advisor for Computer Engineering questions.
      </p>

      <div className="article-grid">
        <article className="info-panel">
          <h2>Project Purpose</h2>
          <p>
            The advisor helps prospective and current students ask focused questions about Computer Engineering education,
            skills, curriculum, career paths, and future technology topics.
          </p>
        </article>

        <article className="info-panel">
          <h2>Why RAG Is Used</h2>
          <p>
            Retrieval-Augmented Generation lets the system search a curated knowledge base first, then generate answers
            from retrieved passages. This supports citations, source cards, and insufficient-information behavior.
          </p>
        </article>

        <article className="info-panel">
          <h2>Knowledge Base</h2>
          <p>
            The project uses an approved source registry covering department information, curriculum, programming, AI,
            cybersecurity, careers, internships, employment, and related topics.
          </p>
        </article>

        <article className="info-panel">
          <h2>Local AI Model</h2>
          <p>
            The project is designed to perform LLM inference locally through Ollama using qwen2.5:3b instead of a
            commercial cloud LLM API.
          </p>
        </article>

        <article className="info-panel">
          <h2>Technology Stack</h2>
          <dl className="stack-list">
            <dt>Frontend</dt>
            <dd>React + Vite</dd>
            <dt>Backend</dt>
            <dd>FastAPI</dd>
            <dt>Retrieval</dt>
            <dd>ChromaDB</dd>
            <dt>Embeddings</dt>
            <dd>sentence-transformers/all-MiniLM-L6-v2</dd>
            <dt>Local LLM</dt>
            <dd>qwen2.5:3b through Ollama</dd>
          </dl>
        </article>

        <article className="info-panel limitation-panel">
          <h2>Limitations</h2>
          <ul className="clean-list">
            <li>Answers depend on available knowledge-base evidence.</li>
            <li>Unsupported questions may return insufficient information or out-of-scope responses.</li>
            <li>The advisor focuses on Computer Engineering topics.</li>
            <li>Local model responses may take several seconds.</li>
            <li>The backend keeps the last 8 turns of each session to understand follow-up questions.</li>
          </ul>
        </article>
      </div>
    </section>
  );
}

export default AboutProjectPage;
