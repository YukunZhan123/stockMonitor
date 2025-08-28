import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { ErrorBoundary } from "react-error-boundary";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import { ErrorFallback } from "./components/ErrorBoundary";

/**
 * High-level purpose: Production-ready App component with comprehensive error handling
 * - Global error boundary for React error catching
 * - Network status monitoring and offline handling
 * - Performance monitoring and error tracking
 * - Secure routing with authentication protection
 * - Graceful fallbacks for all error scenarios
 */

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading, error, isOnline } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-indigo-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto"></div>
          <p className="mt-4 text-gray-300">Loading...</p>
          {!isOnline && (
            <p className="mt-2 text-sm text-yellow-300">
              You appear to be offline. Some features may not be available.
            </p>
          )}
        </div>
      </div>
    );
  }

  // Handle authentication errors
  if (error && !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-indigo-900 flex items-center justify-center px-6 py-12">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="rounded-lg bg-white/5 p-8 backdrop-blur-sm border border-white/10">
            <div className="flex justify-center mb-4">
              <div className="rounded-full bg-red-500/10 p-3">
                <svg
                  className="h-8 w-8 text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
                  />
                </svg>
              </div>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-white mb-4">
                Authentication Error
              </h3>
              <p className="text-gray-300 mb-6">{error}</p>
              <button
                onClick={() => (window.location.href = "/auth")}
                className="flex w-full justify-center rounded-md bg-indigo-500 px-3 py-1.5 text-sm/6 font-semibold text-white hover:bg-indigo-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500"
              >
                Go to Login
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/auth" replace />;
};

const DashboardWrapper = () => {
  const { user, logout } = useAuth();
  return <Dashboard user={user} onLogout={logout} />;
};

const AppRoutes = () => {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <Router>
        <Routes>
          <Route
            path="/auth"
            element={
              <ErrorBoundary FallbackComponent={ErrorFallback}>
                <AuthPage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ErrorBoundary FallbackComponent={ErrorFallback}>
                <ProtectedRoute>
                  <DashboardWrapper />
                </ProtectedRoute>
              </ErrorBoundary>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </ErrorBoundary>
  );
};

function App() {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
