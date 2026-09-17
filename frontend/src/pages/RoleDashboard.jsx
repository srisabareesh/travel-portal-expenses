import { useAuth } from "../context/AuthContext";

import EmployeeDashboard from "./EmployeeDashboard";
import ReviewerDashboard from "./ReviewerDashboard";


function RoleDashboard() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ padding: "30px" }}>
        <h2>Loading...</h2>
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ padding: "30px" }}>
        <h2>User information not available</h2>
        <p>Please log in again.</p>
      </div>
    );
  }

  // Employee
  if (user.role === "EMPLOYEE") {
    return <EmployeeDashboard />;
  }

  // Reviewer
  if (user.role === "REVIEWER") {
    return <ReviewerDashboard />;
  }

  // Manager
  if (user.role === "MANAGER") {
    return (
      <div style={{ padding: "30px" }}>
        <h1>Manager Dashboard</h1>
        <p>Welcome to the Manager Dashboard.</p>
      </div>
    );
  }

  // Admin
  if (user.role === "ADMIN") {
    return (
      <div style={{ padding: "30px" }}>
        <h1>Admin Dashboard</h1>
        <p>Welcome to the Admin Dashboard.</p>
      </div>
    );
  }

  // Unknown role
  return (
    <div style={{ padding: "30px" }}>
      <h1>Dashboard</h1>
      <p>
        Your user role could not be determined.
      </p>
      <p>
        Current role: {user.role || "No role returned"}
      </p>
    </div>
  );
}

export default RoleDashboard;