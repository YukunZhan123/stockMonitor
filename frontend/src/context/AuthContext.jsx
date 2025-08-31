import { createContext, useContext, useState, useEffect } from "react";
import { authAPI } from "../services/api";
import {
  ERROR_TYPES,
  logError,
  categorizeError,
  withRetry,
  getUserFriendlyMessage,
  networkMonitor,
  performanceMonitor,
} from "../utils/errorHandler";

/**
 * High-level purpose: Production-ready authentication context with comprehensive error handling
 * - Uses httpOnly cookies for secure token storage
 * - Implements retry mechanisms for network failures
 * - Provides structured error logging and user notifications
 * - Handles connection timeouts and server errors gracefully
 * - Maintains authentication state with fallback strategies
 *
 * Production enhancements:
 * - Structured error logging with error types and context
 * - Retry logic for transient network failures
 * - User-friendly error messages with fallback handling
 * - Performance monitoring and request timing
 * - Graceful degradation for offline scenarios
 */

const AuthContext = createContext();

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

const secureStorage = {
  // Check authentication with retry and comprehensive error handling
  checkAuth: async () => {
    try {
      return await withRetry(async () => {
        const response = await authAPI.verifyAuth();
        return response.data.user;
      });
    } catch (error) {
      const errorInfo = logError(error, { operation: "checkAuth" });

      // Return null for auth failures, but log other errors
      if (errorInfo.type !== ERROR_TYPES.AUTH_FAILED) {
        // Only log in development
        if (import.meta.env.DEV) {
          console.warn("Auth check failed:", errorInfo.message);
        }
      }

      return null;
    }
  },

  // Clear authentication with proper error handling
  clearAuth: async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      logError(error, { operation: "clearAuth" });
    }
  },
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOnline, setIsOnline] = useState(networkMonitor.isOnline);

  // Monitor network status for graceful degradation
  useEffect(() => {
    const unsubscribe = networkMonitor.addListener((status) => {
      setIsOnline(status === "online");
      if (status === "online") {
        setError(null); // Clear network errors when back online
      } else {
        setError(
          "You are currently offline. Some features may not be available."
        );
      }
    });

    return unsubscribe;
  }, []);

  // Check for existing authentication on app startup with enhanced error handling
  useEffect(() => {
    const checkExistingAuth = async () => {
      if (!isOnline) {
        setLoading(false);
        setError("Unable to verify authentication while offline");
        return;
      }

      try {
        const timer = performanceMonitor.startTiming("initialAuthCheck");
        const userData = await secureStorage.checkAuth();
        timer.end();

        if (userData) {
          setUser(userData);
          setError(null);
        }
      } catch (error) {
        logError(error, { operation: "initialAuthCheck" });

        // Get user-friendly error message
        const userMessage = getUserFriendlyMessage(error, {
          [ERROR_TYPES.TIMEOUT]:
            "Authentication check timed out. Please refresh the page.",
          [ERROR_TYPES.SERVER_ERROR]:
            "Server is temporarily unavailable. Please try again later.",
          [ERROR_TYPES.NETWORK_ERROR]:
            "Network connection failed. Please check your internet connection.",
        });

        // Only show error for non-auth failures
        const errorType = categorizeError(error);
        if (errorType !== ERROR_TYPES.AUTH_FAILED) {
          setError(userMessage);
        }
      } finally {
        setLoading(false);
      }
    };

    checkExistingAuth();
  }, [isOnline]);

  const login = async (email, password) => {
    setError(null);

    if (!isOnline) {
      const offlineError =
        "Cannot log in while offline. Please check your connection.";
      setError(offlineError);
      return { success: false, error: offlineError };
    }

    try {
      const response = await withRetry(async () => {
        return await authAPI.login({ email, password });
      });

      const { user } = response.data;
      setUser(user);
      setError(null);

      return { success: true, user };
    } catch (error) {
      logError(error, { operation: "login", email });

      // Handle validation errors with field-specific messages
      if (error.response?.status === 400 && error.response?.data) {
        return { success: false, fieldErrors: error.response.data };
      }

      const userMessage = getUserFriendlyMessage(error, {
        [ERROR_TYPES.AUTH_FAILED]:
          error.response?.data?.error ||
          error.response?.data?.detail ||
          "Invalid email or password",
      });

      setError(userMessage);
      return { success: false, error: userMessage };
    }
  };

  const register = async (userData) => {
    setError(null);

    if (!isOnline) {
      const offlineError =
        "Cannot register while offline. Please check your connection.";
      setError(offlineError);
      return { success: false, error: offlineError };
    }

    try {
      const response = await withRetry(async () => {
        return await authAPI.register(userData);
      });

      const { user } = response.data;
      setUser(user);
      setError(null);

      return { success: true, user };
    } catch (error) {
      logError(error, { operation: "register", email: userData.email });

      // Handle validation errors with field-specific messages
      if (error.response?.status === 400 && error.response?.data) {
        return { success: false, fieldErrors: error.response.data };
      }

      const userMessage = getUserFriendlyMessage(error);
      setError(userMessage);
      return { success: false, error: userMessage };
    }
  };

  const logout = async () => {
    try {
      // Always clear user state first for immediate UI feedback
      setUser(null);
      setError(null);

      // Attempt to clear server-side session
      if (isOnline) {
        await secureStorage.clearAuth();

        // Force a small delay to ensure cookies are cleared before next login attempt
        await new Promise((resolve) => setTimeout(resolve, 100));
      } else {
        // In offline mode, just log the intent
        console.info(
          "Logout requested while offline - cleared local state only"
        );
      }
    } catch (error) {
      logError(error, { operation: "logout" });
    }
  };

  const value = {
    user,
    loading,
    error,
    isOnline,
    login,
    register,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.is_staff || false,
    clearError: () => setError(null),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
