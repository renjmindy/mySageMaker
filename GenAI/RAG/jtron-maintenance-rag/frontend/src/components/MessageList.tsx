import { useEffect, useRef } from "react";
import type { Citation, Message } from "../types";

interface Props {
  messages: Message[];
  streaming?: { content: string; citations: Citation[] } | null;
  onCitationClick?: (c: Citation) => void;
}

export default function MessageList({ messages, streaming, onCitationClick }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming?.content]);

  if (messages.length === 0 && !streaming) {
    return (
      <div className="flex-1 grid place-items-center text-ink-400 text-sm p-6 text-center">
        Ask something about the maintenance docs to get started.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((m) => (
        <Bubble
          key={m.id}
          role={m.role}
          content={m.content}
          citations={m.citations}
          onCitationClick={onCitationClick}
        />
      ))}
      {streaming && (
        <Bubble
          role="assistant"
          content={streaming.content || "…"}
          citations={streaming.citations}
          onCitationClick={onCitationClick}
          pending
        />
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function Bubble({
  role,
  content,
  citations,
  onCitationClick,
  pending,
}: {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  onCitationClick?: (c: Citation) => void;
  pending?: boolean;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
          isUser ? "bg-ink-100 text-ink-900" : "bg-ink-700 text-ink-50"
        } ${pending ? "animate-pulse" : ""}`}
      >
        {content}
        {!isUser && citations && citations.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {citations.map((c, i) => (
              <button
                key={i}
                onClick={() => onCitationClick?.(c)}
                className="text-[11px] bg-ink-800 hover:bg-ink-600 border border-ink-600 rounded px-2 py-0.5"
                title={c.snippet ?? ""}
              >
                {c.source}
                {c.page ? ` · p.${c.page}` : ""}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
