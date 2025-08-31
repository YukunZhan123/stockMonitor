import { useState } from 'react';
import { subscriptionAPI } from '../../services/api';

export default function AddSubscriptionModal({ onClose, onAdd }) {
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
        const errorData = error.response.data;
        
        // Handle Django REST Framework errors
        const processedErrors = {};
        
        for (const [key, value] of Object.entries(errorData)) {
          if (key === 'non_field_errors') {
            processedErrors.general = Array.isArray(value) ? value[0] : value;
          } else {
            // Handle field-specific errors (may be arrays)
            processedErrors[key] = Array.isArray(value) ? value[0] : value;
          }
        }
        
        setErrors(processedErrors);
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