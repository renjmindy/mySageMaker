import { Navigate, Route, Routes } from "react-router-dom";
import Login from "./routes/Login";
import Chat from "./routes/Chat";
import { useAuth } from "./hooks/useAuth";

export default function App() {
  const auth = useAuth();

  if (auth.state.status === "loading") {
    return (
      <div className="h-full grid place-items-center text-ink-400 text-sm">loading…</div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
          auth.state.status === "authed" ? (
            <Navigate to="/" replace />
          ) : (
            <Login onLogin={auth.login} onRegister={auth.register} />
          )
        }
      />
      <Route
        path="/"
        element={
          auth.state.status === "authed" ? (
            <Chat user={auth.state.user} onLogout={auth.logout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route
        path="/s/:sessionId"
        element={
          auth.state.status === "authed" ? (
            <Chat user={auth.state.user} onLogout={auth.logout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
