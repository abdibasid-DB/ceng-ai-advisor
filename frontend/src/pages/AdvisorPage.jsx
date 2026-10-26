import { useEffect, useMemo, useRef, useState } from "react";
import ChatInput from "../components/ChatInput.jsx";
import ChatMessage from "../components/ChatMessage.jsx";
import LoadingMessage from "../components/LoadingMessage.jsx";
import StatusIndicator from "../components/StatusIndicator.jsx";
import { EXAMPLE_QUESTIONS } from "../constants.js";
import { API_BASE_URL, getReadiness, getSources, sendQuestionStream } from "../services/api.js";

function createMessage(role, content, extra = {}) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
    createdAt: new Date().toISOString(),
    ...extra,
  };
}

function createSessionId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normalizeError(error) {
  if (error?.name === "TypeError") {
    return "The advisor service is currently unavailable. Please make sure the local backend and Ollama are running.";
  }
  return error?.message || "The advisor service could not process the request.";
}

function createConversation() {
  return { id: createSessionId(), sessionId: createSessionId(), messages: [] };
}

function restoreHistory() {
  try {
    const saved = JSON.parse(sessionStorage.getItem("advisor-conversations"));
    if (saved?.conversations?.length && saved.conversations.every((item) =>
      typeof item.id === "string" && typeof item.sessionId === "string" && Array.isArray(item.messages))) {
      return {
        activeId: saved.conversations.some((item) => item.id === saved.activeId) ? saved.activeId : saved.conversations[0].id,
        conversations: saved.conversations.map((item) => ({ ...item, messages: item.messages.map((message) =>
          message.isStreaming ? { ...message, isStreaming: false, status: "error", content: "This reply was interrupted. Please send your question again." } : { ...message, revealStartedAt: undefined }),
        })),
      };
    }
  } catch { /* Start fresh when browser storage is unavailable or invalid. */ }
  const conversation = createConversation();
  return { conversations: [conversation], activeId: conversation.id };
}

function AdvisorPage({ questionRequest }) {
  const [history, setHistory] = useState(restoreHistory);
  const activeConversation = history.conversations.find((item) => item.id === history.activeId);
  const messages = activeConversation.messages;
  const [sourceRegistry, setSourceRegistry] = useState([]);
  const [storageWarning, setStorageWarning] = useState("");
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [readiness, setReadiness] = useState("checking");
  const [readinessDetail, setReadinessDetail] = useState("");
  const conversationRef = useRef(null);
  const busyRef = useRef(false);
  const requestRef = useRef(null);

  useEffect(() => {
    try {
      sessionStorage.setItem("advisor-conversations", JSON.stringify(history));
      setStorageWarning("");
    } catch {
      setStorageWarning("Conversation history is available until this page is reloaded; browser session storage is unavailable.");
    }
  }, [history]);

  useEffect(() => {
    getSources().then((data) => setSourceRegistry(data.sources || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!questionRequest || questionRequest.id === requestRef.current || busyRef.current) return;
    requestRef.current = questionRequest.id;
    const conversation = startNewConversation();
    submitQuestion(questionRequest.question, conversation);
  }, [questionRequest, isLoading]);

  const hasMessages = messages.length > 0;

  const statusHint = useMemo(() => {
    if (readiness === "ready") {
      return `Connected to ${API_BASE_URL || window.location.origin}`;
    }
    if (readiness === "checking") {
      return "Checking local backend readiness...";
    }
    return readinessDetail || "Backend or Ollama is not ready. You can retry after starting local services.";
  }, [readiness, readinessDetail]);

  async function checkReadiness() {
    setReadiness("checking");
    setReadinessDetail("");
    try {
      const data = await getReadiness();
      if (data.status === "ready") {
        setReadiness("ready");
        setReadinessDetail("");
      } else {
        setReadiness("degraded");
        setReadinessDetail("Backend responded, but one or more local RAG components are unavailable.");
      }
    } catch (error) {
      setReadiness("unavailable");
      setReadinessDetail(normalizeError(error));
    }
  }

  useEffect(() => {
    checkReadiness();
  }, []);

  useEffect(() => {
    conversationRef.current?.scrollTo({
      top: conversationRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading, history.activeId]);

  async function submitQuestion(questionText = input, targetConversation = activeConversation) {
    const question = questionText.trim();
    if (!question || busyRef.current) {
      return;
    }
    busyRef.current = true;
    const sessionId = targetConversation.sessionId;
    function updateConversation(update) {
      setHistory((current) => ({ ...current, conversations: current.conversations.map((item) =>
        item.id === targetConversation.id ? update(item) : item) }));
    }
    function setMessages(update) {
      updateConversation((item) => ({ ...item, messages: update(item.messages) }));
    }
    function setSessionId(nextId) {
      updateConversation((item) => ({ ...item, sessionId: nextId }));
    }

    const userMessage = createMessage("user", question);
    const assistantMessage = createMessage("assistant", "", {
      status: "streaming",
      sources: [],
      retrievedContext: [],
      timing: {},
      error: null,
      isStreaming: true,
    });
    setMessages((current) => [...current, userMessage, assistantMessage]);
    setInput("");
    setIsLoading(true);

    try {
      let receivedFinal = false;
      await sendQuestionStream(question, sessionId, false, {
        onMetadata: (metadata) => {
          if (metadata.session_id && metadata.session_id !== sessionId) {
            setSessionId(metadata.session_id);
          }
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessage.id
                ? {
                    ...message,
                    retrievalMetadata: metadata.retrieval_metadata || {},
                    retrievedContext: metadata.retrieved_context || [],
                    progressMetadata: metadata,
                  }
                : message,
            ),
          );
        },
        // Raw model tokens are an unvalidated draft. They only signal progress;
        // the visible answer is the validated text delivered by the final event.
        onToken: () => {},
        onFinal: (response) => {
          receivedFinal = true;
          if (response.session_id && response.session_id !== sessionId) {
            setSessionId(response.session_id);
          }
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessage.id
                ? {
                    ...message,
                    content: response.answer || "",
                    revealStartedAt: Date.now(),
                    status: response.status,
                    exampleQuestions: response.example_questions || [],
                    answeredAs: response.answered_as || null,
                    sources: response.sources || [],
                    retrievedContext: response.retrieved_context || [],
                    retrievalMetadata: response.retrieval_metadata || {},
                    citationMetadata: response.citation_metadata || {},
                    answerWarnings: response.answer_warnings || [],
                    timing: response.timing || {},
                    model: response.model || null,
                    error: response.error || null,
                    isStreaming: false,
                  }
                : message,
            ),
          );
        },
      });
      if (!receivedFinal) {
        throw new Error("The advisor stream ended before a verified answer was produced.");
      }
    } catch (error) {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessage.id
            ? {
                ...message,
                content: normalizeError(error),
                status: "error",
                sources: [],
                error: null,
                isStreaming: false,
              }
            : message,
        ),
      );
    } finally {
      busyRef.current = false;
      setIsLoading(false);
    }
  }

  function startNewConversation() {
    const conversation = createConversation();
    setHistory((current) => ({ activeId: conversation.id, conversations: [conversation, ...current.conversations] }));
    setInput("");
    return conversation;
  }

  return (
    <section className="page-section advisor-page" aria-labelledby="advisor-title">
      <div className="advisor-heading">
        <div>
          <p className="eyebrow">AI Advisor</p>
          <h1 id="advisor-title">Ask the Computer Engineering Advisor</h1>
          <p className="hero-copy">
            Ask about Computer Engineering education, curriculum, careers, skills, technologies, internships, and future paths.
          </p>
        </div>
        <div className="hero-actions">
          <StatusIndicator status={readiness} onRetry={checkReadiness} />
          <button type="button" className="secondary-button" onClick={startNewConversation}>
            New Conversation
          </button>
        </div>
      </div>

      {storageWarning ? <p role="status">{storageWarning}</p> : null}
      <details className="advisor-purpose">
        <summary>About this advisor · How it works</summary>
        <div className="advisor-purpose-content">
          <p>A local RAG (retrieval-augmented generation) assistant for prospective OSTİM Computer Engineering students.</p>
          <ol>
            <li>Search the knowledge base for your question.</li>
            <li>Find relevant passages.</li>
            <li>A local open-source model writes the answer.</li>
            <li>Sources are shown so you can check the evidence.</li>
          </ol>
          <p>It runs locally with an open-source model and no commercial AI API. When it does not have enough information, it says so.</p>
        </div>
      </details>
      <div className="advisor-workspace">
        <aside className="history-panel" aria-label="Conversation history">
          <h2>Conversations</h2>
          <p>Saved in this browser session</p>
          <ul>
            {history.conversations.map((item) => (
              <li key={item.id}>
                <button type="button" aria-current={item.id === history.activeId ? "true" : undefined}
                  onClick={() => { setHistory((current) => ({ ...current, activeId: item.id })); setInput(""); }}>
                  {item.messages.find((message) => message.role === "user")?.content || "New conversation"}
                  {item.messages.some((message) => message.isStreaming) ? " · Answering…" : ""}
                </button>
              </li>
            ))}
          </ul>
        </aside>
      <section className="chat-card" aria-label="Computer Engineering advisor chatbot">
        <div className="chat-toolbar">
          <div>
            <h2>Advisor Chat</h2>
            <p>{statusHint}</p>
          </div>
        </div>

        <div className="conversation" ref={conversationRef}>
          {!hasMessages ? (
            <section className="empty-state">
              <h3>Start with a question</h3>
              <p>
                Answers are generated from the local knowledge base. This session keeps recent context for follow-up
                questions while retrieved sources remain the factual evidence.
              </p>
              <div className="example-grid" aria-label="Example questions">
                {EXAMPLE_QUESTIONS.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => submitQuestion(question)}
                    disabled={isLoading}
                    className="example-question"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </section>
          ) : (
            messages.map((message) => message.isStreaming
              ? <LoadingMessage key={message.id} metadata={message.progressMetadata} />
              : <ChatMessage key={message.id} message={message} sourceRegistry={sourceRegistry}
                  onExampleQuestion={(question) => submitQuestion(question)} isLoading={isLoading} />)
          )}
        </div>

        <ChatInput value={input} onChange={setInput} onSubmit={() => submitQuestion()} isLoading={isLoading} />
      </section>
      </div>
    </section>
  );
}

export default AdvisorPage;
