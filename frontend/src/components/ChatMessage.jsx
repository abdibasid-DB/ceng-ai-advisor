import { useState } from "react";
import ReactMarkdown from "react-markdown";
import SourceCard from "./SourceCard.jsx";

// Transform Markdown text nodes only, leaving code and existing links intact.
function citationLinks(options) {
  return (tree) => {
    function visit(node) {
      if (!node.children || ["link", "linkReference", "code", "inlineCode"].includes(node.type)) return;
      node.children = node.children.flatMap((child) => {
        if (child.type !== "text") { visit(child); return [child]; }
        const parts = [];
        let offset = 0;
        for (const match of child.value.matchAll(/\[S\d+\]/g)) {
          const target = options.targets[match[0].slice(1, -1)];
          if (!target) continue;
          if (match.index > offset) parts.push({ type: "text", value: child.value.slice(offset, match.index) });
          parts.push({ type: "link", url: `#${target}`, children: [{ type: "text", value: match[0] }] });
          offset = match.index + match[0].length;
        }
        if (offset < child.value.length) parts.push({ type: "text", value: child.value.slice(offset) });
        return parts;
      });
    }
    visit(tree);
  };
}

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

function ChatMessage({ message, sourceRegistry = [], onExampleQuestion, isLoading = false }) {
  const [copyStatus, setCopyStatus] = useState("");
  const isUser = message.role === "user";
  const title = !isUser ? statusTitle(message.status) : null;
  const showSources = !isUser && message.status === "answered" && message.sources?.length > 0;
  const targets = {};
  if (showSources) message.sources.forEach((source, index) => {
    source.evidence_labels?.filter(Boolean).forEach((label) => {
      targets[label.replace(/[\[\]]/g, "")] = `${message.id}-source-${index}`;
    });
  });

  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(message.content || "");
      setCopyStatus("Copied");
    } catch { setCopyStatus("Copy failed. Select the answer to copy it manually."); }
  }

  return (
    <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
      <article className={`message ${isUser ? "user-message" : "assistant-message"} status-${message.status || "plain"}`}>
        {!isUser && title ? <p className="message-status">{title}</p> : null}
        <div className="message-text">
          {isUser ? <p>{message.content}</p> : (
            <ReactMarkdown remarkPlugins={[[citationLinks, { targets }]]} components={{
              a: ({ href, children }) => {
                const isCitation = Object.values(targets).some((target) => href === `#${target}`);
                return isCitation ? (
                  <a className="citation-badge" href={href} aria-label={`View source ${children}`}
                    onClick={(event) => {
                      event.preventDefault();
                      const card = document.getElementById(href.slice(1));
                      card?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                      card?.focus({ preventScroll: true });
                    }}>{children}</a>
                ) : <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
              },
            }}>{message.content || ""}</ReactMarkdown>
          )}
        </div>
        {!isUser && message.status === "help" && message.exampleQuestions?.length > 0 ? (
          <div className="example-grid" aria-label="Help example questions">
            {message.exampleQuestions.map((question) => (
              <button key={question} type="button" className="example-question"
                disabled={isLoading || !onExampleQuestion} onClick={() => onExampleQuestion(question)}>
                {question}
              </button>
            ))}
          </div>
        ) : null}
        {!isUser ? <div className="answer-actions">
          <button type="button" className="secondary-button" onClick={copyAnswer}>Copy answer</button>
          <span role="status">{copyStatus}</span>
        </div> : null}
        {!isUser && message.status === "answered" && message.answerWarnings?.includes("partial_answer") ? (
          <p className="message-status">My sources only cover part of your question.</p>
        ) : null}
        {!isUser && message.error ? <p className="message-error">{message.error}</p> : null}
        {showSources ? (
          <section className="sources-panel" aria-label="Supporting sources">
            <h3>Supporting sources</h3>
            <div className="source-list">
              {message.sources.map((source, index) => (
                <SourceCard key={`${message.id}-source-${source.source_id || index}`}
                  id={`${message.id}-source-${index}`}
                  source={{ ...source, publication_date: source.publication_date || sourceRegistry.find((item) => item.source_id === source.source_id)?.publication_date }} index={index} />
              ))}
            </div>
          </section>
        ) : null}
      </article>
    </div>
  );
}

export default ChatMessage;
