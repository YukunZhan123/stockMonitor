import { useState } from 'react';

export default function PageHeader({ 
  user, 
  onLogout, 
  title = "Stock Monitor",
  showAddButton = true,
  onAddClick,
  children 
}) {
  return (
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
              {title}
            </h1>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-300">
                Welcome, {user?.username || user?.email}
              </span>
              {user?.is_staff && (
                <span className="inline-flex items-center rounded-md bg-yellow-500/20 px-2 py-1 text-xs font-medium text-yellow-300 ring-1 ring-inset ring-yellow-500/30">
                  Admin
                </span>
              )}
            </div>
            
            {/* Custom action buttons */}
            {children}
            
            {showAddButton && (
              <button
                onClick={onAddClick}
                className="rounded-md bg-indigo-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500"
              >
                Add Subscription
              </button>
            )}
            
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
  );
}