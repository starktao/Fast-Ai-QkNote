async function fetchJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.detail || "request failed";
    throw new Error(message);
  }
  return data;
}

export function getConfig() {
  return fetchJson("/api/config");
}

export function saveConfig(payload) {
  return fetchJson("/api/config", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createSession(payload) {
  return fetchJson("/api/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listSessions() {
  return fetchJson("/api/sessions");
}

export function getSession(sessionId) {
  return fetchJson(`/api/sessions/${sessionId}`);
}

export function deleteSession(sessionId) {
  return fetchJson(`/api/sessions/${sessionId}`, {
    method: "DELETE",
  });
}
