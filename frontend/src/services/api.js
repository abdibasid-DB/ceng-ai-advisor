const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || DEFAULT_API_BASE_URL;

async function parseJsonResponse(response) {
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("The advisor service returned an unreadable response.");
  }

  if (!response.ok) {
    if (response.status === 422) {
      throw new Error("Please enter a valid question before sending.");
    }
    if (response.status === 503) {
      throw new Error(data?.error || "The advisor service is currently unavailable.");
    }
    throw new Error("The advisor service could not process the request.");
  }

  return data;
}

export async function sendQuestion(question, sessionId, resetSession = false) {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      session_id: sessionId || undefined,
      reset_session: resetSession,
    }),
  });

  return parseJsonResponse(response);
}

export async function sendQuestionStream(question, sessionId, resetSession = false, handlers = {}) {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/x-ndjson",
    },
    body: JSON.stringify({
      question,
      session_id: sessionId || undefined,
      reset_session: resetSession,
    }),
  });

  if (!response.ok) {
    let data = null;
    try {
      data = await response.json();
    } catch {
      // Fall through to generic error.
    }
    throw new Error(data?.error || "The advisor service could not start a streaming response.");
  }
  if (!response.body) {
    throw new Error("The advisor service did not return a readable stream.");
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";

  function dispatch(line) {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.event === "metadata") handlers.onMetadata?.(event.data);
    else if (event.event === "token") handlers.onToken?.(event.data?.text || "");
    else if (event.event === "final") handlers.onFinal?.(event.data);
    else if (event.event === "error") {
      handlers.onError?.(event.data);
      throw new Error(event.data?.error || event.data?.message || "The advisor stream failed.");
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) dispatch(line);
    }
    dispatch(buffer);
  } finally {
    reader.releaseLock();
  }
}

export async function getReadiness() {
  const response = await fetch(`${API_BASE_URL}/api/v1/readiness`);
  return parseJsonResponse(response);
}

export async function getSources() {
  const response = await fetch(`${API_BASE_URL}/api/v1/sources`);
  return parseJsonResponse(response);
}
