import { fetchEventSource } from "@microsoft/fetch-event-source";
import type { ChatSession, Citation, Message, User } from "./types";

const BASE = ""; // same-origin via Vite proxy in dev, nginx in prod

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    credentials: "include",
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") msg = body.detail;
      else if (Array.isArray(body?.detail)) msg = body.detail.map((d: any) => d.msg).join("; ");
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // auth
  register: (email: string, password: string, display_name: string) =>
    j<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password, display_name }) }),
  login: (email: string, password: string) =>
    j<User>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => j<void>("/auth/logout", { method: "POST" }),
  me: () => j<User>("/auth/me"),

  // sessions
  listSessions: () => j<ChatSession[]>("/sessions"),
  createSession: (title?: string) =>
    j<ChatSession>("/sessions", { method: "POST", body: JSON.stringify({ title }) }),
  renameSession: (id: string, title: string) =>
    j<ChatSession>(`/sessions/${id}`, { method: "PATCH", body: JSON.stringify({ title }) }),
  deleteSession: (id: string) =>
    j<void>(`/sessions/${id}`, { method: "DELETE" }),
  listMessages: (id: string) => j<Message[]>(`/sessions/${id}/messages`),
};

export interface StreamHandlers {
  onToken: (text: string) => void;
  onCitation: (c: Citation) => void;
  onDone: (assistantMessageId: string) => void;
  onError: (message: string) => void;
}

/**
 * POST a user prompt and stream the assistant reply via SSE.
 * Backend emits events: `token`, `citation`, `done`, `error`.
 */
export async function streamMessage(
  sessionId: string,
  content: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  await fetchEventSource(`${BASE}/sessions/${sessionId}/messages`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ content }),
    signal,
    openWhenHidden: true,
    async onopen(res) {
      if (!res.ok) {
        const text = await res.text().catch(() => res.statusText);
        throw new Error(text || `${res.status}`);
      }
    },
    onmessage(ev) {
      if (ev.event === "token") handlers.onToken(ev.data);
      else if (ev.event === "citation") {
        try {
          handlers.onCitation(JSON.parse(ev.data));
        } catch {
          /* drop malformed citation */
        }
      } else if (ev.event === "error") handlers.onError(ev.data);
      else if (ev.event === "done") handlers.onDone(ev.data);
    },
    onerror(err) {
      handlers.onError(err instanceof Error ? err.message : String(err));
      throw err; // stop retrying
    },
  });
}
