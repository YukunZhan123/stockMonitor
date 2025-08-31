import { useState } from 'react';

export default function StockCard({ 
  subscription, 
  onDelete, 
  onSendNow, 
  isAdmin = false,
  showActions = true,
  className = ""
}) {
  const [loading, setLoading] = useState(false);

  const handleSendNow = async () => {
    if (!onSendNow) return;
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
    <div className={`rounded-lg bg-white/5 p-6 backdrop-blur-sm border border-white/10 hover:bg-white/10 transition-colors ${className}`}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <h3 className="text-lg font-bold text-white">{subscription.stock_ticker}</h3>
            {isAdmin && subscription.user_username && (
              <span className="inline-flex items-center rounded-md bg-indigo-500/20 px-2 py-1 text-xs font-medium text-indigo-300 ring-1 ring-inset ring-indigo-500/30">
                {subscription.user_username}
              </span>
            )}
          </div>
          <p className="text-2xl font-semibold text-indigo-400">
            {subscription.price_display || 'Loading...'}
          </p>
        </div>
        
        {showActions && (
          <div className="flex space-x-2">
            {onSendNow && (
              <button
                onClick={handleSendNow}
                disabled={loading}
                className="rounded-md bg-indigo-500/20 px-2 py-1 text-xs font-medium text-indigo-300 hover:bg-indigo-500/30 disabled:opacity-50"
              >
                {loading ? 'Sending...' : 'Send Now'}
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => onDelete(subscription.id)}
                className="rounded-md bg-red-500/20 px-2 py-1 text-xs font-medium text-red-300 hover:bg-red-500/30"
              >
                Delete
              </button>
            )}
          </div>
        )}
      </div>
      
      <div className="space-y-1 text-sm text-gray-400">
        <p>Email: {subscription.email}</p>
        {isAdmin && subscription.user_email && subscription.user_email !== subscription.email && (
          <p>Owner: {subscription.user_email}</p>
        )}
        <p>Created: {new Date(subscription.created_at).toLocaleDateString()}</p>
      </div>
    </div>
  );
}