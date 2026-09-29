import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { LoadingState } from "../components/ui";

function ProtectedRoute({ children }) {
  const {
    isAuthenticated,
    loading,
  } = useAuth();

  if (loading) {
    return <LoadingState label="Checking your session…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default ProtectedRoute;
