/**
 * Production-ready error handling utility for the entire application
 *
 * Features:
 * - Centralized error categorization and logging
 * - Retry mechanisms with exponential backoff
 * - User-friendly error message generation
 * - Performance monitoring and analytics
 * - Network status awareness
 * - Integration ready for monitoring services (Sentry, DataDog, etc.)
 * - Consistent error handling across all components
 */

// Error categories for consistent handling
export const ERROR_TYPES = {
  NETWORK_ERROR: "NETWORK_ERROR",
  AUTH_FAILED: "AUTH_FAILED",
  SERVER_ERROR: "SERVER_ERROR",
  TIMEOUT: "TIMEOUT",
  VALIDATION_ERROR: "VALIDATION_ERROR",
  RATE_LIMITED: "RATE_LIMITED",
  FORBIDDEN: "FORBIDDEN",
  NOT_FOUND: "NOT_FOUND",
  UNKNOWN: "UNKNOWN",
};

// User-friendly error messages mapping
const ERROR_MESSAGES = {
  [ERROR_TYPES.NETWORK_ERROR]:
    "Please check your internet connection and try again.",
  [ERROR_TYPES.AUTH_FAILED]:
    "Invalid credentials. Please check your email and password.",
  [ERROR_TYPES.SERVER_ERROR]:
    "Server is temporarily unavailable. Please try again later.",
  [ERROR_TYPES.TIMEOUT]: "Request timed out. Please try again.",
  [ERROR_TYPES.VALIDATION_ERROR]: "Please check your input and try again.",
  [ERROR_TYPES.RATE_LIMITED]:
    "Too many requests. Please wait a moment and try again.",
  [ERROR_TYPES.FORBIDDEN]: "You don't have permission to perform this action.",
  [ERROR_TYPES.NOT_FOUND]: "The requested resource was not found.",
  [ERROR_TYPES.UNKNOWN]: "An unexpected error occurred. Please try again.",
};

/**
 * Categorize errors based on type, status, and context
 */
export const categorizeError = (error) => {
  // Network/connection errors
  if (!navigator.onLine) {
    return ERROR_TYPES.NETWORK_ERROR;
  }

  if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
    return ERROR_TYPES.TIMEOUT;
  }

  if (
    error.code === "NETWORK_ERROR" ||
    error.message?.includes("Network Error")
  ) {
    return ERROR_TYPES.NETWORK_ERROR;
  }

  // HTTP status-based categorization
  const status = error.response?.status;
  if (status) {
    if (status === 401) return ERROR_TYPES.AUTH_FAILED;
    if (status === 403) return ERROR_TYPES.FORBIDDEN;
    if (status === 404) return ERROR_TYPES.NOT_FOUND;
    if (status === 429) return ERROR_TYPES.RATE_LIMITED;
    if (status === 400 || status === 422) return ERROR_TYPES.VALIDATION_ERROR;
    if (status >= 500) return ERROR_TYPES.SERVER_ERROR;
  }

  return ERROR_TYPES.UNKNOWN;
};

/**
 * Enhanced error logging with structured data
 */
export const logError = (error, context = {}) => {
  const timestamp = new Date().toISOString();
  const errorType = categorizeError(error);

  const errorInfo = {
    timestamp,
    type: errorType,
    message: error.message || error.userMessage || "Unknown error",
    status: error.response?.status,
    statusText: error.response?.statusText,
    url: error.config?.url || context.operation,
    method: error.config?.method?.toUpperCase(),
    stack: error.stack,
    context,
    userAgent: navigator.userAgent,
    pathname: window.location.pathname,
    search: window.location.search,
    referrer: document.referrer,
  };

  // Console logging in development
  if (import.meta.env.DEV) {
    console.group(`[Error] ${errorType}`);
    console.error("Error Details:", errorInfo);
    console.error("Original Error:", error);
    console.groupEnd();
  }

  // Production monitoring integration
  if (import.meta.env.PROD) {
    // TODO: Integrate with monitoring services
    // Example integrations:
    // Sentry.captureException(error, { tags: { type: errorType }, extra: errorInfo });
    // window.gtag?.('event', 'exception', { description: errorInfo.message });
    // analyticsService.trackError(errorInfo);
  }

  return errorInfo;
};

/**
 * Retry mechanism with exponential backoff
 */
export const withRetry = async (operation, options = {}) => {
  const {
    maxRetries = 2,
    initialDelay = 1000,
    maxDelay = 10000,
    backoffFactor = 2,
    retryCondition = (error) => {
      const type = categorizeError(error);
      return [
        ERROR_TYPES.NETWORK_ERROR,
        ERROR_TYPES.TIMEOUT,
        ERROR_TYPES.SERVER_ERROR,
      ].includes(type);
    },
  } = options;

  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      // Log the attempt
      logError(error, {
        attempt: attempt + 1,
        maxRetries: maxRetries + 1,
        retrying: attempt < maxRetries,
      });

      // Check if we should retry
      if (attempt < maxRetries && retryCondition(error)) {
        const delay = Math.min(
          initialDelay * Math.pow(backoffFactor, attempt),
          maxDelay
        );

        console.log(
          `Retrying in ${delay}ms... (attempt ${attempt + 1}/${maxRetries + 1})`
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
        continue;
      }

      throw error;
    }
  }

  throw lastError;
};

/**
 * Get user-friendly error message
 */
export const getUserFriendlyMessage = (error, customMessages = {}) => {
  const errorType = categorizeError(error);

  // Check for custom message first
  if (customMessages[errorType]) {
    return customMessages[errorType];
  }

  // Check for server-provided user message
  if (error.userMessage) {
    return error.userMessage;
  }

  // Check for specific API error messages
  if (error.response?.data) {
    const data = error.response.data;

    // Handle validation errors with field-specific messages
    if (errorType === ERROR_TYPES.VALIDATION_ERROR) {
      if (typeof data === "object") {
        const firstError = Object.values(data)[0];
        if (Array.isArray(firstError)) {
          return firstError[0];
        }
        if (typeof firstError === "string") {
          return firstError;
        }
      }
    }

    // Handle detail messages
    if (data.detail) {
      return data.detail;
    }

    // Handle error messages
    if (data.error) {
      return data.error;
    }

    // Handle message field
    if (data.message) {
      return data.message;
    }
  }

  // Fall back to default message
  return ERROR_MESSAGES[errorType] || ERROR_MESSAGES[ERROR_TYPES.UNKNOWN];
};

/**
 * Network status monitoring utility
 */
export class NetworkMonitor {
  constructor() {
    this.isOnline = navigator.onLine;
    this.listeners = new Set();

    this.boundHandleOnline = this.handleOnline.bind(this);
    this.boundHandleOffline = this.handleOffline.bind(this);

    // Listen for network status changes
    window.addEventListener("online", this.boundHandleOnline);
    window.addEventListener("offline", this.boundHandleOffline);
  }

  handleOnline() {
    this.isOnline = true;
    this.notifyListeners("online");
  }

  handleOffline() {
    this.isOnline = false;
    this.notifyListeners("offline");
  }

  addListener(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  notifyListeners(status) {
    this.listeners.forEach((callback) => callback(status));
  }

  destroy() {
    window.removeEventListener("online", this.boundHandleOnline);
    window.removeEventListener("offline", this.boundHandleOffline);
    this.listeners.clear();
  }
}

// Global network monitor instance
export const networkMonitor = new NetworkMonitor();

/**
 * Performance monitoring utilities
 */
export const performanceMonitor = {
  startTiming: (operation) => {
    return {
      operation,
      startTime: performance.now(),
      end: function () {
        const duration = performance.now() - this.startTime;

        if (duration > 5000) {
          console.warn(
            `Slow operation detected: ${this.operation} took ${duration.toFixed(
              2
            )}ms`
          );
        }

        // TODO: Send to analytics in production
        // analyticsService.trackTiming(this.operation, duration);

        return duration;
      },
    };
  },
};

// Removed createErrorInfo - now handled by react-error-boundary fallback components

/**
 * Input sanitization utilities
 */
export const sanitizeInput = (value) => {
  if (typeof value === "string") {
    return value
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
      .replace(/javascript:/gi, "")
      .replace(/on\w+=/gi, "")
      .trim();
  }
  return value;
};

/**
 * Validation utilities
 */
export const validators = {
  email: (value) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value);
  },

  strongPassword: (value) => {
    return (
      value.length >= 8 &&
      /[A-Z]/.test(value) &&
      /[a-z]/.test(value) &&
      /\d/.test(value)
    );
  },

  username: (value) => {
    return (
      /^[a-zA-Z0-9_-]+$/.test(value) && value.length >= 3 && value.length <= 30
    );
  },
};

export default {
  ERROR_TYPES,
  categorizeError,
  logError,
  withRetry,
  getUserFriendlyMessage,
  networkMonitor,
  performanceMonitor,
  sanitizeInput,
  validators,
};
