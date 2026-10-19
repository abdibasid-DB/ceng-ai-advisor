import SourceCard from "./SourceCard.jsx";

function statusTitle(status) {
  if (status === "insufficient_information") {
    return "Insufficient information";
  }
  if (status === "out_of_scope") {
    return "Out of scope";
  }
  if (status === "error") {
    return "Service message";
  }
  return null;
}

function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const title = !isUser ? statusTitle(message.status) : null;
  const showSources = !isUser && message.status === "answered" && message.sources?.length > 0;

  return (
    <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
      <article className={`message ${isUser ? "user-message" : "assistant-message"} status-${message.status || "plain"}`}>
        {!isUser && title ? <p className="message-status">{title}</p> : null}
        <div className="message-text">
          {(message.content || "").split("\n").map((line, index) => (
            <p key={`${message.id}-line-${index}`}>{line || "\u00a0"}</p>
          ))}
        </div>
        {!isUser && message.status === "answered" && message.answerWarnings?.includes("partial_answer") ? (
          <p className="message-status">My sources only cover part of your question.</p>
        ) : null}
        {!isUser && message.error ? <p className="message-error">{message.error}</p> : null}
        {showSources ? (
          <section className="sources-panel" aria-label="Supporting sources">
            <h3>Supporting sources</h3>
            <div className="source-list">
              {message.sources.map((source, index) => (
                <SourceCard key={`${message.id}-source-${source.source_id || index}`} source={source} index={index} />
              ))}
            </div>
          </section>
        ) : null}
      </article>
    </div>
  );
}

export default ChatMessage;
