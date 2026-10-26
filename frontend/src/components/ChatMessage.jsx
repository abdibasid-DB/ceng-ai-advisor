import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import SourceCard from "./SourceCard.jsx";

// Typing reveal for the final, validated answer (raw model tokens never reach
// this component). Words appear at a steady pace, like a chat assistant typing;
// very long answers speed up so the reveal never takes more than MAX_REVEAL_MS.
const WORD_MS = 35;
const MIN_REVEAL_MS = 1200;
const MAX_REVEAL_MS = 8000;
const MAX_FRAME_STEP_MS = 100;

// Messages whose reveal has finished or been skipped in this page session.
// Switching conversations remounts ChatMessage; these must not type out again.
const revealedMessageIds = new Set();

function splitWords(content) {
  return content.match(/\s*\S+/g) || [];
}

// Only messages created by onFinal carry revealStartedAt. Stored history
// (after a reload) has it removed and renders immediately.
function useFinalAnswerReveal(message) {
  const content = message.content || "";
  const words = useMemo(() => splitWords(content), [content]);
  const duration = Math.min(MAX_REVEAL_MS, Math.max(MIN_REVEAL_MS, words.length * WORD_MS));
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [shown, setShown] = useState(() =>
    message.revealStartedAt && !revealedMessageIds.has(message.id) ? 0 : words.length);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  const animating = !reducedMotion && words.length > 0 && shown < words.length;

  useEffect(() => {
    if (!animating) {
      if (message.revealStartedAt) revealedMessageIds.add(message.id);
      return undefined;
    }
    // Progress counts only time the page is actually painting: requestAnimationFrame
    // pauses while the tab or window is hidden, and each frame adds at most
    // MAX_FRAME_STEP_MS. An answer that arrives while the student looks elsewhere
    // therefore still types out when they come back, instead of being finished.
    let frame;
    let last;
    let elapsed = (shown / words.length) * duration;
    function tick(now) {
      if (last !== undefined) elapsed += Math.min(MAX_FRAME_STEP_MS, Math.max(0, now - last));
      last = now;
      const next = Math.min(words.length, Math.ceil((elapsed / duration) * words.length));
      setShown((current) => Math.max(current, next));
      if (next < words.length) frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // `shown` is read only to resume after a remount; adding it would restart every frame.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [animating, words, duration, message.id, message.revealStartedAt]);

  return {
    animating,
    text: animating ? words.slice(0, shown).join("") : content,
    skip: () => { revealedMessageIds.add(message.id); setShown(words.length); },
  };
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
  const textRef = useRef(null);
  // Keep the typing text in view, unless the student has scrolled up to read.
  useEffect(() => {
    if (!reveal.animating) return;
    const container = textRef.current?.closest(".conversation");
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distanceFromBottom < 160) container.scrollTop = container.scrollHeight;
  }, [reveal.text, reveal.animating]);
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
        {!isUser && message.answeredAs ? <p className="answered-as">Answered as: {message.answeredAs}</p> : null}
        {reveal.animating && !isUser ? <span className="sr-only">{message.content}</span> : null}
        <div ref={textRef} className="message-text" data-animating={reveal.animating && !isUser}
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
        {reveal.animating && !isUser ? <button type="button" className="skip-animation" onClick={reveal.skip}>Skip animation</button> : null}
        {!isUser && !reveal.animating && message.status === "help" && message.exampleQuestions?.length > 0 ? (
          <div className="example-grid" aria-label="Help example questions">
            {message.exampleQuestions.map((question) => (
              <button key={question} type="button" className="example-question"
                disabled={isLoading || !onExampleQuestion} onClick={() => onExampleQuestion(question)}>
                {question}
              </button>
            ))}
          </div>
        ) : null}
        {!isUser && !reveal.animating ? <div className="answer-actions">
          <button type="button" className="secondary-button" onClick={copyAnswer}>Copy answer</button>
          <span role="status">{copyStatus}</span>
        </div> : null}
        {!isUser && message.status === "answered" && message.answerWarnings?.includes("partial_answer") ? (
          <p className="message-status">My sources only cover part of your question.</p>
        ) : null}
        {!isUser && message.error ? <p className="message-error">{message.error}</p> : null}
        {showSources && !reveal.animating ? (
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
