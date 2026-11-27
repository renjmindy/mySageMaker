import { Link, useParams } from "react-router-dom";
import type { ChatSession, User } from "../types";

interface Props {
  sessions: ChatSession[];
  user: User;
  onNewSession: () => void;
  onDelete: (id: string) => void;
  onLogout: () => void;
}

export default function SessionList({
  sessions,
  user,
  onNewSession,
  onDelete,
  onLogout,
}: Props) {
  const { sessionId } = useParams();
  return (
    <aside className="w-72 shrink-0 bg-ink-800 border-r border-ink-700 flex flex-col">
      <div className="p-3 border-b border-ink-700">
        <button
          onClick={onNewSession}
          className="w-full bg-ink-100 text-ink-900 rounded py-2 text-sm font-medium"
        >
          + New chat
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 && (
          <div className="text-xs text-ink-400 p-2">No conversations yet.</div>
        )}
        {sessions.map((s) => {
          const active = s.id === sessionId;
          return (
            <div
              key={s.id}
              className={`group flex items-center rounded px-2 py-1.5 text-sm ${
                active ? "bg-ink-700 text-ink-50" : "hover:bg-ink-700/60 text-ink-200"
              }`}
            >
              <Link to={`/s/${s.id}`} className="flex-1 truncate">
                {s.title || "Untitled"}
              </Link>
              <button
                onClick={() => {
                  if (confirm("Delete this conversation?")) onDelete(s.id);
                }}
                title="Delete"
                className="opacity-0 group-hover:opacity-100 text-ink-400 hover:text-red-400 ml-2"
              >
                ✕
              </button>
            </div>
          );
        })}
      </nav>

      <div className="p-3 border-t border-ink-700 text-xs text-ink-400 flex items-center justify-between">
        <span className="truncate">{user.display_name}</span>
        <button onClick={onLogout} className="hover:text-ink-100">
          Sign out
        </button>
      </div>
    </aside>
  );
}
