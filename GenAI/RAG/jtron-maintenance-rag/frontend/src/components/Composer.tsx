import { KeyboardEvent, useState } from "react";

interface Props {
  disabled?: boolean;
  onSend: (content: string) => void;
}

export default function Composer({ disabled, onSend }: Props) {
  const [text, setText] = useState("");

  function send() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="border-t border-ink-700 p-3 bg-ink-800">
      <div className="flex gap-2 items-end">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          rows={1}
          placeholder={disabled ? "waiting…" : "Ask about the maintenance docs (Enter to send, Shift+Enter for newline)"}
          disabled={disabled}
          className="flex-1 resize-none bg-ink-900 border border-ink-700 rounded px-3 py-2 text-sm outline-none focus:border-ink-400 max-h-40"
          style={{ minHeight: "2.5rem" }}
        />
        <button
          onClick={send}
          disabled={disabled || !text.trim()}
          className="bg-ink-100 text-ink-900 rounded px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
