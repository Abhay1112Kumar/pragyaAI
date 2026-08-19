import { Bot } from "lucide-react";
import { useState } from "react";

import { authenticate } from "../services/api";

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const result = await authenticate(mode, username, password);
      onAuthenticated(result);
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Authentication failed. Check your username and password.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="auth-logo">
          <Bot size={28} />
        </div>

        <h1>PragyaAI</h1>
        <p>
          {mode === "login"
            ? "Sign in to your secure AI workspace."
            : "Create your PragyaAI account."}
        </p>

        <label>
          Username
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            minLength={3}
            maxLength={80}
            autoComplete="username"
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            maxLength={128}
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            required
          />
        </label>

        {error && <div className="auth-error">{error}</div>}

        <button type="submit" disabled={submitting}>
          {submitting
            ? "Please wait..."
            : mode === "login"
              ? "Sign In"
              : "Create Account"}
        </button>

        <button
          type="button"
          className="auth-mode-button"
          onClick={() => {
            setMode((current) =>
              current === "login" ? "register" : "login",
            );
            setError("");
          }}
        >
          {mode === "login"
            ? "Need an account? Register"
            : "Already registered? Sign in"}
        </button>

        {mode === "register" && (
          <small>The first account created becomes the administrator.</small>
        )}
      </form>
    </div>
  );
}
