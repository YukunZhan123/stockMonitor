import { useState } from "react";
import PageLayout from "../components/Layout/PageLayout";
import StockCard from "../components/StockCard/StockCard";
import LoadingSpinner from "../components/UI/LoadingSpinner";
import EmptyState from "../components/UI/EmptyState";
import Pagination from "../components/UI/Pagination";
import AddSubscriptionModal from "../components/AddSubscriptionModal/AddSubscriptionModal";
import useSubscriptions from "../hooks/useSubscriptions";
import { subscriptionAPI } from "../services/api";
import TestError from "../components/TestError"; // TEMPORARY FOR TESTING

export default function Dashboard({ user, onLogout }) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [viewMode, setViewMode] = useState("grid"); // Start with grid for all users
  const [refreshingPrices, setRefreshingPrices] = useState(false);
  const isAdmin = user?.is_staff;

  const {
    subscriptions,
    loading,
    error,
    currentPage,
    totalPages,
    addSubscription,
    deleteSubscription,
    sendNow,
    refreshSubscriptions,
    setError,
    setCurrentPage,
  } = useSubscriptions({
    isAdmin,
    itemsPerPage: isAdmin ? 20 : 6, // More items for admin view
  });

  const handleAddSubscription = (newSubscription) => {
    addSubscription(newSubscription);
    setShowAddForm(false);
  };

  const handleDeleteSubscription = async (id) => {
    if (
      isAdmin &&
      !confirm("Are you sure you want to delete this subscription?")
    ) {
      return;
    }
    await deleteSubscription(id);
  };

  const handleSendNow = async (subscription) => {
    await sendNow(subscription);
  };

  const handleRefreshPrices = async () => {
    setRefreshingPrices(true);
    try {
      const response = await subscriptionAPI.refreshPrices();
      const result = response.data;
      // Show success message briefly
      setError(null);
      refreshSubscriptions();

      // Optional: Show a brief success message instead of alert
      console.log(`Refreshed prices for ${result.updated_count} subscriptions`);
    } catch (error) {
      setError("Failed to refresh prices. Please try again.");
    } finally {
      setRefreshingPrices(false);
    }
  };

  const headerActions = (
    <>
      <button
        onClick={handleRefreshPrices}
        disabled={refreshingPrices}
        className="rounded-md bg-green-500/20 px-3 py-1.5 text-sm font-semibold text-green-300 hover:bg-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
      >
        {refreshingPrices && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-green-300"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        )}
        <span>{refreshingPrices ? "Refreshing..." : "Refresh Prices"}</span>
      </button>
      <button
        onClick={() => setViewMode(viewMode === "grid" ? "list" : "grid")}
        className="rounded-md bg-blue-500/20 px-3 py-1.5 text-sm font-semibold text-blue-300 hover:bg-blue-500/30"
      >
        {viewMode === "grid" ? "List View" : "Grid View"}
      </button>
    </>
  );

  return (
    <PageLayout
      user={user}
      onLogout={onLogout}
      title={isAdmin ? "Admin Dashboard" : "Stock Monitor"}
      onAddClick={() => setShowAddForm(true)}
      headerActions={headerActions}
      error={error}
    >
      {isAdmin && <TestError />}
      {loading ? (
        <LoadingSpinner message="Loading subscriptions..." />
      ) : subscriptions.length === 0 ? (
        <EmptyState
          title={isAdmin ? "No subscriptions found" : "No subscriptions yet"}
          description={
            isAdmin
              ? "No users have created stock subscriptions yet."
              : "Start monitoring stocks by creating your first subscription"
          }
          actionLabel={isAdmin ? null : "Add Your First Subscription"}
          onAction={isAdmin ? null : () => setShowAddForm(true)}
        />
      ) : (
        <>
          {/* Admin Tab Navigation */}
          {isAdmin && (
            <div className="mb-6">
              <div className="border-b border-white/20">
                <nav className="-mb-px flex space-x-8">
                  <button className="py-2 px-1 border-b-2 border-indigo-500 text-indigo-400 font-medium text-sm">
                    All Subscriptions ({subscriptions.length})
                  </button>
                </nav>
              </div>
            </div>
          )}

          {/* Adaptive Layout: Grid for users, List/Grid toggle for admins */}
          {viewMode === "grid" ? (
            <div
              className={`grid gap-6 mb-8 ${
                isAdmin
                  ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-4" // 4 columns for admin
                  : "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" // 3 columns for users
              }`}
            >
              {subscriptions.map((subscription) => (
                <StockCard
                  key={subscription.id}
                  subscription={subscription}
                  onDelete={handleDeleteSubscription}
                  onSendNow={isAdmin ? null : handleSendNow} // No send now for admin in grid
                  isAdmin={isAdmin}
                />
              ))}
            </div>
          ) : (
            /* List View for All Users */
            <div className="space-y-4 mb-8">
              {subscriptions.map((subscription) => (
                <div
                  key={subscription.id}
                  className="rounded-lg bg-white/5 p-4 backdrop-blur-sm border border-white/10"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div>
                        <div className="flex items-center space-x-2">
                          <h3 className="text-lg font-bold text-white">
                            {subscription.stock_ticker}
                          </h3>
                          {isAdmin && subscription.user_username && (
                            <span className="inline-flex items-center rounded-md bg-indigo-500/20 px-2 py-1 text-xs font-medium text-indigo-300 ring-1 ring-inset ring-indigo-500/30">
                              {subscription.user_username}
                            </span>
                          )}
                        </div>
                        {isAdmin && (
                          <p className="text-sm text-gray-400">
                            User:{" "}
                            {subscription.user_username ||
                              subscription.user_email}
                          </p>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold text-indigo-400">
                          {subscription.price_display || "Loading..."}
                        </p>
                        <p className="text-sm text-gray-400">
                          Email: {subscription.email}
                        </p>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      {!isAdmin && (
                        <button
                          onClick={() => handleSendNow(subscription)}
                          className="rounded-md bg-indigo-500/20 px-3 py-1.5 text-sm font-medium text-indigo-300 hover:bg-indigo-500/30"
                        >
                          Send Now
                        </button>
                      )}
                      <button
                        onClick={() =>
                          handleDeleteSubscription(subscription.id)
                        }
                        className="rounded-md bg-red-500/20 px-3 py-1.5 text-sm font-medium text-red-300 hover:bg-red-500/30"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-gray-500">
                    Created:{" "}
                    {new Date(subscription.created_at).toLocaleDateString()}
                    {isAdmin && ` • ID: ${subscription.id}`}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
          />
        </>
      )}
      {/* Add Subscription Modal */}
      {showAddForm && (
        <AddSubscriptionModal
          onClose={() => setShowAddForm(false)}
          onAdd={handleAddSubscription}
        />
      )}
    </PageLayout>
  );
}
