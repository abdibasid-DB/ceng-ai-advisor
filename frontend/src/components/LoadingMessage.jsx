function LoadingMessage() {
  return (
    <div className="message-row assistant-row" aria-live="polite">
      <div className="message assistant-message loading-message">
        <span className="loading-spinner" aria-hidden="true" />
        <span>Searching the knowledge base and generating an answer...</span>
      </div>
    </div>
  );
}

export default LoadingMessage;
