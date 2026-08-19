import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  timeout: 120000,
});

const API_BASE_URL = "http://127.0.0.1:8000/api/v1";
let accessToken = null;

export function setAccessToken(token) {
  accessToken = token || null;

  if (accessToken) {
    api.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

export async function authenticate(mode, username, password) {
  const endpoint = mode === "register" ? "/auth/register" : "/auth/login";
  const response = await api.post(endpoint, { username, password });
  return response.data;
}

export async function streamMessage(
  message,
  conversationId,
  documentId = null,
  { onToken, onMetadata } = {},
) {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(accessToken
        ? { Authorization: `Bearer ${accessToken}` }
        : {}),
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      document_id: documentId,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(
      errorBody?.detail || `Chat request failed (${response.status}).`,
    );
  }

  if (!response.body) {
    throw new Error("Streaming is not supported by this browser.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let metadata = null;

  function processEvent(rawEvent) {
    let eventName = "message";
    const dataLines = [];

    for (const line of rawEvent.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    if (dataLines.length === 0) {
      return;
    }

    const data = JSON.parse(dataLines.join("\n"));

    if (eventName === "token") {
      onToken?.(data.content ?? "");
    } else if (eventName === "metadata") {
      metadata = data;
      onMetadata?.(data);
    } else if (eventName === "error") {
      throw new Error(data.detail || "The response stream failed.");
    }
  }

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replaceAll("\r\n", "\n");

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const event of events) {
      if (event.trim()) {
        processEvent(event);
      }
    }

    if (done) {
      if (buffer.trim()) {
        processEvent(buffer);
      }
      break;
    }
  }

  return metadata;
}

export async function uploadDocument(file, onUploadProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(
    "/documents/upload",
    formData,
    {
      onUploadProgress,
    },
  );

  return response.data;
}

export default api;
