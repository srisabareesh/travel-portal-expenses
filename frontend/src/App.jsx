import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import Login from "./pages/Login";
import ProtectedRoute from "./routes/ProtectedRoute";
import AppShell from "./components/AppShell";

import CreateTravelRequest from "./pages/CreateTravelRequest";
import MyTravelRequests from "./pages/MyTravelRequests";
import TravelRequestDetails from "./pages/TravelRequestDetails";
import UploadDocument from "./pages/UploadDocument";
import ReviewerTravelRequests from "./pages/ReviewerTravelRequests";
import ReviewerTravelRequestDetails from "./pages/ReviewerTravelRequestDetails";
import ManagerTravelRequests from "./pages/ManagerTravelRequests";
import ManagerTravelRequestDetails from "./pages/ManagerTravelRequestDetails";
import RoleDashboard from "./pages/RoleDashboard";
import Notifications from "./pages/Notifications";
import AdminDashboard from "./pages/AdminDashboard";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={<Login />}
        />

        {/* Authenticated shell: every protected page renders inside
            the shared sidebar/topbar layout. */}
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route
            path="/dashboard"
            element={<RoleDashboard />}
          />

          <Route
            path="/notifications"
            element={<Notifications />}
          />

          <Route
            path="/travel-requests/create"
            element={<CreateTravelRequest />}
          />

          <Route
            path="/travel-requests"
            element={<MyTravelRequests />}
          />

          <Route
            path="/travel-requests/:id"
            element={<TravelRequestDetails />}
          />

          <Route
            path="/travel-requests/:id/documents/upload"
            element={<UploadDocument />}
          />

          <Route
            path="/reviewer/travel-requests"
            element={<ReviewerTravelRequests />}
          />

          <Route
            path="/reviewer/travel-requests/:id"
            element={<ReviewerTravelRequestDetails />}
          />

          <Route
            path="/manager/travel-requests"
            element={<ManagerTravelRequests />}
          />

          <Route
            path="/manager/travel-requests/:id"
            element={<ManagerTravelRequestDetails />}
          />

          <Route
            path="/admin"
            element={<AdminDashboard />}
          />
        </Route>

        <Route
          path="/"
          element={
            <Navigate
              to="/dashboard"
              replace
            />
          }
        />

        <Route
          path="*"
          element={
            <Navigate
              to="/dashboard"
              replace
            />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
