import axios from "axios";
import { sanitizeInput, logError, performanceMonitor } from '../utils/errorHandler';

/**
 * High-level purpose: Production-ready API service with security enhancements
 * - Uses httpOnly cookies instead of localStorage for tokens
 * - Request/response sanitization and validation
 * - Proper error handling and logging
 * - Automatic credentials inclusion for cross-origin requests
 * - Rate limiting and request timeout protection
 */

// Environment-based API URL
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

// CSRF Token handling for Django API
const getCSRFToken = () => {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

// Input sanitization now handled by shared utility

// Create axios instance with enhanced config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // 15 second timeout
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
    // Removed X-Requested-With header - not needed for modern CSRF protection
    // Django's CSRF protection works with cookies and CSRF tokens, not this header
  },
  withCredentials: true, // Include httpOnly cookies for authentication
});

// Enhanced request interceptor with shared utilities
api.interceptors.request.use(
  (config) => {
    // Add CSRF token for non-GET requests
    const csrfToken = getCSRFToken();
    if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase())) {
      config.headers['X-CSRFToken'] = csrfToken;
    }

    // Sanitize request data using shared utility
    if (config.data) {
      if (typeof config.data === 'object') {
        const sanitized = {};
        for (const [key, value] of Object.entries(config.data)) {
          sanitized[key] = sanitizeInput(value);
        }
        config.data = sanitized;
      } else {
        config.data = sanitizeInput(config.data);
      }
    }

    // Add performance monitoring
    config.metadata = { timer: performanceMonitor.startTiming(`API_${config.method?.toUpperCase()}_${config.url}`) };

    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    logError(error, { context: 'axios_request_interceptor' });
    return Promise.reject(error);
  }
);

// Enhanced response interceptor with shared error handling
api.interceptors.response.use(
  (response) => {
    // Complete performance monitoring
    if (response.config.metadata?.timer) {
      response.config.metadata.timer.end();
    }
    
    console.log(`[API Response] ${response.status}`);

    // Sanitize string responses for XSS protection
    if (typeof response.data === "string") {
      response.data = sanitizeInput(response.data);
    }

    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Complete performance monitoring for failed requests
    if (originalRequest?.metadata?.timer) {
      originalRequest.metadata.timer.end();
    }

    // Log error using shared utility
    logError(error, {
      context: 'axios_response_interceptor',
      url: originalRequest?.url,
      method: originalRequest?.method,
    });

    // Handle specific error cases
    if (
      error.response?.status === 401 &&
      !originalRequest.url?.includes("/auth/")
    ) {
      // Unauthorized - redirect to login
      console.warn("Unauthorized access - redirecting to login");
      window.location.href = "/auth";
      return Promise.reject(error);
    }

    // Add user-friendly messages based on error type
    if (error.response?.status === 429) {
      error.userMessage = "Too many requests. Please wait a moment and try again.";
    } else if (error.response?.status >= 500) {
      error.userMessage = "Server is temporarily unavailable. Please try again later.";
    } else if (error.code === "ECONNABORTED") {
      error.userMessage = "Request timed out. Please check your connection and try again.";
    }

    return Promise.reject(error);
  }
);

// Initialize CSRF token on app load
const initializeCSRF = async () => {
  try {
    await api.get("/auth/csrf/");
  } catch (error) {
    console.warn("Failed to initialize CSRF token:", error);
  }
};

// Initialize CSRF token
initializeCSRF();

// Enhanced authentication API endpoints (validation moved to forms for better UX)
export const authAPI = {
  register: (userData) => {
    return api.post("/auth/register/", userData);
  },

  login: (credentials) => {
    return api.post("/auth/login/", credentials);
  },

  logout: () => api.post("/auth/logout/"),

  verifyAuth: () => api.get("/auth/verify/"),

  refreshToken: () => api.post("/auth/refresh/"),

  getCSRFToken: () => api.get("/auth/csrf/"),
};

// Subscription API endpoints
export const subscriptionAPI = {
  // Get all subscriptions for current user with pagination support
  getSubscriptions: (params = {}) => api.get("/subscriptions/", { params }),

  // Create new subscription
  createSubscription: (subscriptionData) => api.post("/subscriptions/", subscriptionData),

  // Delete subscription by ID
  deleteSubscription: (id) => api.delete(`/subscriptions/${id}/`),

  // Send email now for specific subscription
  sendNow: (id) => api.post(`/subscriptions/${id}/send-now/`),

  // Get subscription by ID (if needed)
  getSubscription: (id) => api.get(`/subscriptions/${id}/`),
};

export default api;
