import { FormEvent, useState } from "react";

interface Props {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, display_name: string) => Promise<void>;
}

export default function Login({ onLogin, onRegister }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      if (mode === "login") await onLogin(email, password);
      else await onRegister(email, password, displayName || email.split("@")[0]);
    } catch (ex: any) {
      setErr(ex?.message ?? "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="h-full grid place-items-center p-6">
      <form
        onSubmit={submit}
        className="w-full max-w-sm bg-ink-800 border border-ink-700 rounded-xl p-6 space-y-4 shadow-xl"
      >
        <div>
          <div className="text-lg font-semibold">Jtron Maintenance RAG</div>
          <div className="text-xs text-ink-400">
            {mode === "login" ? "Sign in to continue" : "Create an account"}
          </div>
        </div>

        {mode === "register" && (
          <label className="block">
            <div className="text-xs text-ink-300 mb-1">Display name</div>
            <input
              className="w-full bg-ink-900 border border-ink-700 rounded px-3 py-2 text-sm outline-none focus:border-ink-400"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Jtron"
            />
          </label>
        )}

        <label className="block">
          <div className="text-xs text-ink-300 mb-1">Email</div>
          <input
            type="email"
            autoComplete="email"
            className="w-full bg-ink-900 border border-ink-700 rounded px-3 py-2 text-sm outline-none focus:border-ink-400"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>

        <label className="block">
          <div className="text-xs text-ink-300 mb-1">Password</div>
          <input
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            className="w-full bg-ink-900 border border-ink-700 rounded px-3 py-2 text-sm outline-none focus:border-ink-400"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>

        {err && <div className="text-xs text-red-400">{err}</div>}

        <button
          type="submit"
          disabled={busy}
          className="w-full bg-ink-100 text-ink-900 rounded py-2 text-sm font-medium disabled:opacity-60"
        >
          {busy ? "…" : mode === "login" ? "Sign in" : "Create account"}
        </button>

        <button
          type="button"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
          className="w-full text-xs text-ink-400 hover:text-ink-200"
        >
          {mode === "login" ? "Need an account? Register" : "Have an account? Sign in"}
        </button>
      </form>
    </div>
  );
}
