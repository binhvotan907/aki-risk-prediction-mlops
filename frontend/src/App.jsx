import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import PatientList from "./pages/PatientList";
import Predict from "./pages/Predict";
import PatientTimeline from "./pages/PatientTimeline";
import Monitoring from "./pages/Monitoring";
import ModelInfo from "./pages/ModelInfo";
import DriftDetection from "./pages/DriftDetection";
import Retraining from "./pages/Retraining";
import Account from "./pages/Account";
import UserManagement from "./pages/UserManagement";
import NotFound from "./pages/NotFound";
import AppLayout from "./components/AppLayout";

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("access_token");

  if (!token) {
    return <Navigate to="/login" />;
  }

  return children;
}

function AdminRoute({ children }) {
  const token = localStorage.getItem("access_token");
  const role = localStorage.getItem("role");

  if (!token) {
    return <Navigate to="/login" />;
  }

  if (role !== "admin") {
    return <Navigate to="/dashboard" />;
  }

  return children;
}

function DoctorRoute({ children }) {
  const token = localStorage.getItem("access_token");
  const role = localStorage.getItem("role");

  if (!token) {
    return <Navigate to="/login" />;
  }

  if (role !== "doctor") {
    return <Navigate to="/dashboard" />;
  }

  return children;
}

function WithLayout({ children }) {
  return <AppLayout>{children}</AppLayout>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" />} />

        <Route path="/login" element={<Login />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <WithLayout>
                <Dashboard />
              </WithLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/patients"
          element={
            <ProtectedRoute>
              <WithLayout>
                <PatientList />
              </WithLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/predict"
          element={
            <DoctorRoute>
              <WithLayout>
                <Predict />
              </WithLayout>
            </DoctorRoute>
          }
        />

        <Route
          path="/patient-timeline"
          element={
            <ProtectedRoute>
              <WithLayout>
                <PatientTimeline />
              </WithLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/model-info"
          element={
            <ProtectedRoute>
              <WithLayout>
                <ModelInfo />
              </WithLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/account"
          element={
            <ProtectedRoute>
              <WithLayout>
                <Account />
              </WithLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/monitoring"
          element={
            <AdminRoute>
              <WithLayout>
                <Monitoring />
              </WithLayout>
            </AdminRoute>
          }
        />

        <Route
          path="/drift"
          element={
            <AdminRoute>
              <WithLayout>
                <DriftDetection />
              </WithLayout>
            </AdminRoute>
          }
        />

        <Route
          path="/retraining"
          element={
            <AdminRoute>
              <WithLayout>
                <Retraining />
              </WithLayout>
            </AdminRoute>
          }
        />

        <Route
          path="/users"
          element={
            <AdminRoute>
              <WithLayout>
                <UserManagement />
              </WithLayout>
            </AdminRoute>
          }
        />

        <Route
          path="*"
          element={
            <ProtectedRoute>
              <WithLayout>
                <NotFound />
              </WithLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
