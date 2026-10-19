function LoadingMessage({ metadata }) {
  const passages = metadata?.retrieved_context || [];
  const titles = [...new Set(passages.map((item) => item.title || item.source_name).filter(Boolean))];
  return (
    <div className="message-row assistant-row" aria-live="polite">
      <div className="message assistant-message loading-message">
        <span className="loading-spinner" aria-hidden="true" />
        <ol className="retrieval-steps">
          <li>Searching the knowledge base…</li>
          {metadata ? <li>Found {passages.length} passages from: {titles.join("; ") || "no matching sources"}</li> : null}
          {metadata?.llm_called ? <li>Writing the answer with the local model…</li> : null}
        </ol>
      </div>
    </div>
  );
}

export default LoadingMessage;
