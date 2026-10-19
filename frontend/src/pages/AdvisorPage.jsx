import { useEffect, useMemo, useRef, useState } from "react";
import ChatInput from "../components/ChatInput.jsx";
import ChatMessage from "../components/ChatMessage.jsx";
import LoadingMessage from "../components/LoadingMessage.jsx";
import StatusIndicator from "../components/StatusIndicator.jsx";
import { EXAMPLE_QUESTIONS } from "../constants.js";
import { API_BASE_URL, getReadiness, sendQuestionStream } from "../services/api.js";

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
                    status: response.status,
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
            messages
              .filter((message) => !message.isStreaming)
              .map((message) => <ChatMessage key={message.id} message={message} />)
          )}
          {isLoading ? <LoadingMessage /> : null}
        </div>

        <ChatInput value={input} onChange={setInput} onSubmit={() => submitQuestion()} isLoading={isLoading} />
      </section>
    </section>
  );
}

export default AdvisorPage;
