import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import SourceCard from "./SourceCard.jsx";

const REVEAL_DURATION = 1600;

// Only messages created by onFinal carry a reveal timestamp. Stored history
// renders immediately, and raw model tokens never reach this component.
function useFinalAnswerReveal(message) {
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [progress, setProgress] = useState(() => message.revealStartedAt
    ? Math.min(1, (Date.now() - message.revealStartedAt) / REVEAL_DURATION) : 1);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (reducedMotion) { setProgress(1); return; }
    if (!message.revealStartedAt || progress >= 1) return;
    let frame;
    function tick() {
      const next = Math.min(1, (Date.now() - message.revealStartedAt) / REVEAL_DURATION);
      setProgress(next);
      if (next < 1) frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [message.revealStartedAt, reducedMotion, progress >= 1]);
  const animating = !reducedMotion && progress < 1;
  const characters = Array.from(message.content || "");
  return { animating, text: animating ? characters.slice(0, Math.floor(characters.length * progress)).join("") : message.content || "",
    skip: () => setProgress(1) };
}

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
  const reveal = useFinalAnswerReveal(message);
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
        {reveal.animating && !isUser ? <button type="button" className="skip-animation secondary-button" onClick={reveal.skip}>Skip animation</button> : null}
        {reveal.animating && !isUser ? <span className="sr-only">{message.content}</span> : null}
        <div className="message-text" data-animating={reveal.animating && !isUser}
          aria-hidden={reveal.animating && !isUser ? true : undefined}
          onClick={reveal.animating ? reveal.skip : undefined}>
          {isUser ? <p>{message.content}</p> : (
            <ReactMarkdown remarkPlugins={[[citationLinks, { targets }]]} rehypePlugins={[[rehypeHighlight, { detect: false }]]} components={{
              a: ({ href, children }) => {
                const isCitation = Object.values(targets).some((target) => href === `#${target}`);
                return isCitation ? (
                  <a className="citation-badge" href={href} aria-label={`View source ${children}`}
                    onClick={(event) => {
                      event.preventDefault();
                      const card = document.getElementById(href.slice(1));
                      card?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "nearest" });
                      card?.focus({ preventScroll: true });
                    }}>{children}</a>
                ) : <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
              },
            }}>{reveal.text}</ReactMarkdown>
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
