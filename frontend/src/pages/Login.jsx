import { useState } from "react";
import apiClient from "../api/client";
import { useAuth } from "../hooks/useAuth";
import { useNavigate } from "react-router-dom";

import { Button } from "../components/ui";
import { extractApiError } from "../lib/format";

function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const response = await apiClient.post("auth/login/", {
        username: username,
        password: password,
      });

      const { access, refresh } = response.data;

      await login(access, refresh);

      navigate("/dashboard");
    } catch (err) {
      setError(extractApiError(err, "Login failed. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <span className="app-sidebar-brand-mark" aria-hidden="true">
            ✈
          </span>
        </div>

        <h1 className="login-title">Onsite Travel Portal</h1>

        <p className="login-subtitle">
          Sign in to manage your business travel
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="stack">
            <div className="form-field">
              <label htmlFor="username">Username</label>

              <input
                id="username"
                className="input"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(event) =>
                  setUsername(event.target.value)
                }
                placeholder="Enter username"
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="password">Password</label>

              <input
                id="password"
                className="input"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="Enter password"
                required
              />
            </div>

            {error && (
              <div className="alert alert--error" role="alert">
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              block
              loading={loading}
            >
              {loading ? "Signing in…" : "Sign In"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Login;
