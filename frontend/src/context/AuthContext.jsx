import { useEffect, useState } from "react";

import apiClient from "../api/client";

import { AuthContext } from "./auth-context.js";

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    Boolean(localStorage.getItem("access_token"))
  );

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");

    setIsAuthenticated(false);
    setUser(null);
  };

  const fetchCurrentUser = async () => {
    try {
      const response = await apiClient.get("auth/me/");

      setUser(response.data);
      setIsAuthenticated(true);

    } catch (error) {
      console.error(
        "Unable to fetch current user:",
        error
      );

      logout();

    } finally {
      setLoading(false);
    }
  };

  const login = async (
    accessToken,
    refreshToken
  ) => {
    localStorage.setItem(
      "access_token",
      accessToken
    );

    localStorage.setItem(
      "refresh_token",
      refreshToken
    );

    setIsAuthenticated(true);

    try {
      const response = await apiClient.get(
        "auth/me/"
      );

      setUser(response.data);

    } catch (error) {
      console.error(
        "Unable to fetch current user after login:",
        error
      );

      logout();

      throw error;
    }
  };

  useEffect(() => {
    const token =
      localStorage.getItem("access_token");

    if (token) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- bootstraps auth state once on mount
      void fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
