import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import Login from "./pages/Login";
import RoleDashboard from "./pages/RoleDashboard";
import ProtectedRoute from "./routes/ProtectedRoute";
import CreateTravelRequest from "./pages/CreateTravelRequest";
import MyTravelRequests from "./pages/MyTravelRequests";
import TravelRequestDetails from "./pages/TravelRequestDetails";
import UploadDocument from "./pages/UploadDocument";
import ReviewerTravelRequests from "./pages/ReviewerTravelRequests";
import ReviewerTravelRequestDetails from "./pages/ReviewerTravelRequestDetails";
import ManagerDashboard from "./pages/ManagerDashboard";
import ManagerTravelRequests from "./pages/ManagerTravelRequests";
import ManagerTravelRequestDetails from "./pages/ManagerTravelRequestDetails";

function App() {
  return (
    <BrowserRouter>
      <Routes>

        <Route
          path="/login"
          element={<Login />}
        />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <RoleDashboard />
            </ProtectedRoute>
          }
        />

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
          path="/travel-requests/create"
          element={
            <ProtectedRoute>
              <CreateTravelRequest />
            </ProtectedRoute>
          }
        />
        <Route
          path="/travel-requests"
          element={
            <ProtectedRoute>
              <MyTravelRequests />
            </ProtectedRoute>
          }
        />
        <Route
          path="/travel-requests/:id"
          element={
          <ProtectedRoute>
            <TravelRequestDetails />
          </ProtectedRoute>
          }
        />

        <Route
          path="/travel-requests/:id/documents/upload"
          element={
          <ProtectedRoute>
            <UploadDocument />
          </ProtectedRoute>
          }
        />
        <Route
          path="/reviewer/travel-requests"
          element={
          <ProtectedRoute>
            <ReviewerTravelRequests />
          </ProtectedRoute>
          }
        />
        <Route
          path="/reviewer/travel-requests/:id"
          element={
            <ProtectedRoute>
              <ReviewerTravelRequestDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="/manager"
          element={
            <ProtectedRoute>
              <ManagerDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/manager/travel-requests"
          element={<ManagerTravelRequests />}
        />

        <Route
          path="/manager/travel-requests/:id"
          element={<ManagerTravelRequestDetails />}
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;