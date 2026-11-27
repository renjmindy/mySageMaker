import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, streamMessage } from "../api";
import CitationsPanel from "../components/CitationsPanel";
import Composer from "../components/Composer";
import MessageList from "../components/MessageList";
import SessionList from "../components/SessionList";
import type { ChatSession, Citation, Message, User } from "../types";

interface Props {
  user: User;
  onLogout: () => void;
}

export default function Chat({ user, onLogout }: Props) {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState<{ content: string; citations: Citation[] } | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const streamAbort = useRef<AbortController | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await api.listSessions());
    } catch (e: any) {
      setErr(e?.message ?? "failed to load sessions");
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  // Load messages when the route's sessionId changes
  useEffect(() => {
    setMessages([]);
    setStreaming(null);
    setActiveCitation(null);
    if (!sessionId) return;
    let cancelled = false;
    (async () => {
      try {
        const ms = await api.listMessages(sessionId);
        if (!cancelled) setMessages(ms);
      } catch (e: any) {
        if (!cancelled) setErr(e?.message ?? "failed to load messages");
      }
    })();
    return () => {
      cancelled = true;
      streamAbort.current?.abort();
    };
  }, [sessionId]);

  async function newSession() {
    try {
      const s = await api.createSession();
      await refreshSessions();
      navigate(`/s/${s.id}`);
    } catch (e: any) {
      setErr(e?.message ?? "failed to create session");
    }
  }

  async function deleteSession(id: string) {
    try {
      await api.deleteSession(id);
      await refreshSessions();
      if (id === sessionId) navigate("/");
    } catch (e: any) {
      setErr(e?.message ?? "failed to delete");
    }
  }

  async function send(content: string) {
    if (!sessionId) {
      // no session yet — create one on the fly, then send
      const s = await api.createSession();
      await refreshSessions();
      navigate(`/s/${s.id}`);
      sendInto(s.id, content);
      return;
    }
    sendInto(sessionId, content);
  }

  function sendInto(sid: string, content: string) {
    // optimistic user bubble
    const optimistic: Message = {
      id: `tmp-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    setStreaming({ content: "", citations: [] });
    setErr(null);

    const ac = new AbortController();
    streamAbort.current?.abort();
    streamAbort.current = ac;

    streamMessage(
      sid,
      content,
      {
        onToken: (t) =>
          setStreaming((s) => (s ? { ...s, content: s.content + t } : s)),
        onCitation: (c) =>
          setStreaming((s) => (s ? { ...s, citations: [...s.citations, c] } : s)),
        onError: (msg) => {
          setErr(msg);
          setStreaming(null);
        },
        onDone: async () => {
          setStreaming(null);
          // refresh canonical messages from server (replaces optimistic + streaming)
          try {
            const ms = await api.listMessages(sid);
            setMessages(ms);
            await refreshSessions();
          } catch {
            /* ignore */
          }
        },
      },
      ac.signal,
    ).catch((e) => {
      if (ac.signal.aborted) return;
      setErr(e?.message ?? "stream failed");
      setStreaming(null);
    });
  }

  return (
    <div className="h-full flex">
      <SessionList
        sessions={sessions}
        user={user}
        onNewSession={newSession}
        onDelete={deleteSession}
        onLogout={onLogout}
      />

      <main className="flex-1 flex flex-col min-w-0">
        {err && (
          <div className="bg-red-500/20 text-red-200 text-xs px-4 py-2 border-b border-red-500/40">
            {err}
            <button onClick={() => setErr(null)} className="float-right">✕</button>
          </div>
        )}
        <MessageList
          messages={messages}
          streaming={streaming}
          onCitationClick={setActiveCitation}
        />
        <Composer disabled={!!streaming} onSend={send} />
      </main>

      <CitationsPanel citation={activeCitation} onClose={() => setActiveCitation(null)} />
    </div>
  );
}
