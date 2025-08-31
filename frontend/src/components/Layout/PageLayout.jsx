import PageHeader from './PageHeader';

export default function PageLayout({ 
  user, 
  onLogout, 
  title,
  showAddButton = true,
  onAddClick,
  headerActions,
  error,
  children 
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-indigo-900">
      <PageHeader 
        user={user}
        onLogout={onLogout}
        title={title}
        showAddButton={showAddButton}
        onAddClick={onAddClick}
      >
        {headerActions}
      </PageHeader>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Display */}
        {error && (
          <div className="mb-6 rounded-md bg-red-500/10 border border-red-500/20 px-4 py-3">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}
        
        {children}
      </main>
    </div>
  );
}