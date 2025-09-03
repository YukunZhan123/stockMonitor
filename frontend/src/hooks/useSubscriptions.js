import { useState, useEffect } from "react";
import { subscriptionAPI } from "../services/api";

export default function useSubscriptions({
  itemsPerPage = 6,
  autoLoad = true,
} = {}) {
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const totalPages = Math.ceil(totalCount / itemsPerPage);

  const loadSubscriptions = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = {
        page: currentPage,
        page_size: itemsPerPage,
      };

      const response = await subscriptionAPI.getSubscriptions(params);

      // Handle both paginated and non-paginated responses
      if (response.data.results) {
        // Paginated response from DRF
        setSubscriptions(response.data.results);
        setTotalCount(response.data.count || 0);
      } else {
        // Non-paginated response (fallback)
        setSubscriptions(response.data);
        setTotalCount(response.data.length);
      }
    } catch (error) {
      // Error is already logged by API interceptor
      setError("Failed to load subscriptions. Please try again.");
      setSubscriptions([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  };

  const addSubscription = (newSubscription) => {
    // Refresh the entire list to maintain proper pagination
    setTotalCount((prev) => prev + 1);
    setError(null);
    loadSubscriptions(); // Reload to get proper paginated results
  };

  const deleteSubscription = async (id) => {
    try {
      await subscriptionAPI.deleteSubscription(id);
      
      // Remove from local state
      setSubscriptions((prev) => prev.filter((sub) => sub.id !== id));
      setTotalCount((prev) => prev - 1);
      
      // Handle pagination edge case: if current page becomes empty, go to previous page
      const newTotalCount = totalCount - 1;
      const newTotalPages = Math.ceil(newTotalCount / itemsPerPage);
      
      if (currentPage > newTotalPages && newTotalPages > 0) {
        setCurrentPage(newTotalPages);
      } else if (subscriptions.length === 1 && currentPage > 1) {
        // If this was the last item on the current page (and not page 1), go to previous page
        setCurrentPage(currentPage - 1);
      } else {
        // Refresh current page to fill empty slots
        setTimeout(() => loadSubscriptions(), 100);
      }
      
      setError(null); // Clear any previous errors
    } catch (error) {
      // Error is already logged by API interceptor, just handle user feedback
      setError("Failed to delete subscription. Please try again.");
    }
  };

  const sendNow = async (subscription) => {
    try {
      await subscriptionAPI.sendNow(subscription.id);
      // Clear any previous errors on success
      setError(null);
      // Could add success notification here
    } catch (error) {
      // Error is already logged by API interceptor, just handle user feedback
      setError("Failed to send notification. Please try again.");
    }
  };

  const refreshSubscriptions = () => {
    loadSubscriptions();
  };

  // Auto-load subscriptions when component mounts or page changes
  useEffect(() => {
    if (autoLoad) {
      loadSubscriptions();
    }
  }, [currentPage, autoLoad]);

  return {
    // Data
    subscriptions,
    totalCount,
    totalPages,

    // State
    loading,
    error,
    currentPage,

    // Actions
    loadSubscriptions,
    addSubscription,
    deleteSubscription,
    sendNow,
    refreshSubscriptions,
    setError,
    setCurrentPage,
  };
}
