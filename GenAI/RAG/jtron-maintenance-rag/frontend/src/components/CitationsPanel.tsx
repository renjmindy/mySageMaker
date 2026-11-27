import type { Citation } from "../types";

interface Props {
  citation: Citation | null;
  onClose: () => void;
}

export default function CitationsPanel({ citation, onClose }: Props) {
  if (!citation) return null;
  return (
    <aside className="w-80 shrink-0 bg-ink-800 border-l border-ink-700 flex flex-col">
      <div className="p-3 border-b border-ink-700 flex items-center justify-between">
        <div className="text-sm font-medium">Source</div>
        <button onClick={onClose} className="text-ink-400 hover:text-ink-100 text-sm">
          ✕
        </button>
      </div>
      <div className="p-4 space-y-3 overflow-y-auto">
        <div>
          <div className="text-xs text-ink-400">Document</div>
          <div className="text-sm break-all">{citation.source || "—"}</div>
        </div>
        {citation.page != null && (
          <div>
            <div className="text-xs text-ink-400">Page</div>
            <div className="text-sm">{citation.page}</div>
          </div>
        )}
        {citation.score != null && (
          <div>
            <div className="text-xs text-ink-400">Score</div>
            <div className="text-sm">{citation.score.toFixed(3)}</div>
          </div>
        )}
        {citation.snippet && (
          <div>
            <div className="text-xs text-ink-400 mb-1">Snippet</div>
            <div className="text-sm whitespace-pre-wrap bg-ink-900 border border-ink-700 rounded p-3 leading-relaxed">
              {citation.snippet}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
