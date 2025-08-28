import { useState, useEffect } from "react";
import { subscriptionAPI } from "../services/api";
import TestError from "../components/TestError"; // TEMPORARY FOR TESTING

export default function Dashboard({ user, onLogout }) {
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [showAddForm, setShowAddForm] = useState(false);
  const itemsPerPage = 9; // 3x3 grid

  // Load subscriptions from API with pagination support
  useEffect(() => {
    const loadSubscriptions = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const params = {
          page: currentPage,
          page_size: itemsPerPage
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
        setError('Failed to load subscriptions. Please try again.');
        setSubscriptions([]);
        setTotalCount(0);
      } finally {
        setLoading(false);
      }
    };

    loadSubscriptions();
  }, [currentPage]); // Reload when page changes

  // Pagination logic - use server-side pagination
  const totalPages = Math.ceil(totalCount / itemsPerPage);
  const currentSubscriptions = subscriptions; // Already paginated by server

  const handleAddSubscription = (newSubscription) => {
    // Add new subscription to the beginning of the list
    setSubscriptions((prev) => [newSubscription, ...prev]);
    setTotalCount((prev) => prev + 1);
    setShowAddForm(false);
    setError(null); // Clear any previous errors
  };

  const handleDeleteSubscription = async (id) => {
    try {
      await subscriptionAPI.deleteSubscription(id);
      setSubscriptions((prev) => prev.filter((sub) => sub.id !== id));
      setTotalCount((prev) => prev - 1);
      setError(null); // Clear any previous errors
    } catch (error) {
      // Error is already logged by API interceptor, just handle user feedback
      setError('Failed to delete subscription. Please try again.');
    }
  };

  const handleSendNow = async (subscription) => {
    try {
      await subscriptionAPI.sendNow(subscription.id);
      // Clear any previous errors on success
      setError(null);
      // Could add success notification here
    } catch (error) {
      // Error is already logged by API interceptor, just handle user feedback
      setError('Failed to send notification. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-indigo-900">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <img 
                src="https://tailwindcss.com/plus-assets/img/logos/mark.svg?color=indigo&shade=500" 
                alt="Company" 
                className="h-8 w-auto" 
              />
              <h1 className="text-xl font-bold tracking-tight text-white">
                Stock Monitor
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-300">
                Welcome, {user?.username || user?.email}
              </span>
              <button
                onClick={() => setShowAddForm(true)}
                className="rounded-md bg-indigo-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500"
              >
                Add Subscription
              </button>
              <button
                onClick={onLogout}
                className="rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* TEMPORARY: Test Error Boundary */}
        <TestError />
        
        {/* Error Display */}
        {error && (
          <div className="mb-6 rounded-md bg-red-500/10 border border-red-500/20 px-4 py-3">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}
        
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto"></div>
              <p className="mt-4 text-gray-300">Loading subscriptions...</p>
            </div>
          </div>
        ) : subscriptions.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">No subscriptions yet</h3>
            <p className="text-gray-400 mb-6">Start monitoring stocks by creating your first subscription</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="rounded-md bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-400"
            >
              Add Your First Subscription
            </button>
          </div>
        ) : (
          <>
            {/* Stock Cards Grid - 3x3 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
              {currentSubscriptions.map((subscription) => (
                <StockCard
                  key={subscription.id}
                  subscription={subscription}
                  onDelete={handleDeleteSubscription}
                  onSendNow={handleSendNow}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center space-x-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`rounded-md px-3 py-1.5 text-sm font-semibold ${
                      currentPage === page
                        ? 'bg-indigo-500 text-white'
                        : 'bg-white/10 text-white hover:bg-white/20'
                    }`}
                  >
                    {page}
                  </button>
                ))}
                
                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {/* Add Subscription Modal */}
      {showAddForm && (
        <AddSubscriptionModal
          onClose={() => setShowAddForm(false)}
          onAdd={handleAddSubscription}
        />
      )}
    </div>
  );
}

// Stock Card Component
function StockCard({ subscription, onDelete, onSendNow }) {
  const [loading, setLoading] = useState(false);

  const handleSendNow = async () => {
    setLoading(true);
    await onSendNow(subscription);
    setLoading(false);
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(price);
  };

  return (
    <div className="rounded-lg bg-white/5 p-6 backdrop-blur-sm border border-white/10 hover:bg-white/10 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-white">{subscription.stock_ticker}</h3>
          <p className="text-2xl font-semibold text-indigo-400">
            {subscription.price_display || 'Loading...'}
          </p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={handleSendNow}
            disabled={loading}
            className="rounded-md bg-indigo-500/20 px-2 py-1 text-xs font-medium text-indigo-300 hover:bg-indigo-500/30 disabled:opacity-50"
          >
            {loading ? 'Sending...' : 'Send Now'}
          </button>
          <button
            onClick={() => onDelete(subscription.id)}
            className="rounded-md bg-red-500/20 px-2 py-1 text-xs font-medium text-red-300 hover:bg-red-500/30"
          >
            Delete
          </button>
        </div>
      </div>
      
      <div className="space-y-1 text-sm text-gray-400">
        <p>Email: {subscription.email}</p>
        <p>Created: {new Date(subscription.created_at).toLocaleDateString()}</p>
      </div>
    </div>
  );
}

// Add Subscription Modal Component
function AddSubscriptionModal({ onClose, onAdd }) {
  const [formData, setFormData] = useState({
    stock_ticker: '',
    email: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newErrors = {};

    if (!formData.stock_ticker.trim()) {
      newErrors.stock_ticker = 'Stock ticker is required';
    }
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setLoading(true);
    try {
      const response = await subscriptionAPI.createSubscription(formData);
      onAdd(response.data);
    } catch (error) {
      // Error is already logged by API interceptor
      if (error.response?.status === 400) {
        setErrors(error.response.data);
      } else {
        setErrors({ general: 'Failed to create subscription. Please try again.' });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-gray-900/95 backdrop-blur border border-white/20 rounded-lg p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-white">Add Subscription</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {errors.general && (
          <div className="mb-4 rounded-md bg-red-500/10 border border-red-500/20 px-4 py-3">
            <p className="text-sm text-red-300">{errors.general}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm/6 font-medium text-gray-100 mb-2">
              Stock Ticker
            </label>
            <input
              type="text"
              name="stock_ticker"
              value={formData.stock_ticker}
              onChange={handleChange}
              className={`block w-full rounded-md bg-white/5 px-3 py-1.5 text-base text-white outline-1 -outline-offset-1 placeholder:text-gray-500 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-500 sm:text-sm/6 ${
                errors.stock_ticker ? 'outline-red-500/50' : 'outline-white/10'
              }`}
              placeholder="e.g., AAPL"
            />
            {errors.stock_ticker && (
              <p className="mt-1 text-sm text-red-300">{errors.stock_ticker}</p>
            )}
          </div>

          <div>
            <label className="block text-sm/6 font-medium text-gray-100 mb-2">
              Email Address
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className={`block w-full rounded-md bg-white/5 px-3 py-1.5 text-base text-white outline-1 -outline-offset-1 placeholder:text-gray-500 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-500 sm:text-sm/6 ${
                errors.email ? 'outline-red-500/50' : 'outline-white/10'
              }`}
              placeholder="your@email.com"
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-300">{errors.email}</p>
            )}
          </div>

          <div className="flex space-x-3 pt-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-md bg-indigo-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Subscription'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/20"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}