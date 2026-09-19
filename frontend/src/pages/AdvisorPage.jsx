import { useEffect, useMemo, useRef, useState } from "react";
import ChatInput from "../components/ChatInput.jsx";
import ChatMessage from "../components/ChatMessage.jsx";
import LoadingMessage from "../components/LoadingMessage.jsx";
import StatusIndicator from "../components/StatusIndicator.jsx";
import { EXAMPLE_QUESTIONS } from "../constants.js";
import { API_BASE_URL, getReadiness, sendQuestion } from "../services/api.js";

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

function AdvisorPage() {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(createSessionId);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [readiness, setReadiness] = useState("checking");
  const [readinessDetail, setReadinessDetail] = useState("");
  const conversationRef = useRef(null);

  const hasMessages = messages.length > 0;

  const statusHint = useMemo(() => {
    if (readiness === "ready") {
      return `Connected to ${API_BASE_URL}`;
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
  }, [messages, isLoading]);

  async function submitQuestion(questionText = input) {
    const question = questionText.trim();
    if (!question || isLoading) {
      return;
    }

    const userMessage = createMessage("user", question);
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await sendQuestion(question, sessionId);
      if (response.session_id && response.session_id !== sessionId) {
        setSessionId(response.session_id);
      }
      const assistantMessage = createMessage("assistant", response.answer, {
        status: response.status,
        sources: response.sources || [],
        retrievedContext: response.retrieved_context || [],
        timing: response.timing || {},
        error: response.error || null,
      });
      setMessages((current) => [...current, assistantMessage]);
    } catch (error) {
      const assistantMessage = createMessage("assistant", normalizeError(error), {
        status: "error",
        sources: [],
        error: null,
      });
      setMessages((current) => [...current, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  function startNewConversation() {
    setMessages([]);
    setInput("");
    setSessionId(createSessionId());
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
          <button type="button" className="secondary-button" onClick={startNewConversation} disabled={!hasMessages && !input}>
            New Conversation
          </button>
        </div>
      </div>

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
            messages.map((message) => <ChatMessage key={message.id} message={message} />)
          )}
          {isLoading ? <LoadingMessage /> : null}
        </div>

        <ChatInput value={input} onChange={setInput} onSubmit={() => submitQuestion()} isLoading={isLoading} />
      </section>
    </section>
  );
}

export default AdvisorPage;
