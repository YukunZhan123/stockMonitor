import { useEffect } from 'react';
import { logError } from '../utils/errorHandler';

/**
 * Error fallback component for react-error-boundary
 * Uses the same dark theme design system as auth pages
 */
export const ErrorFallback = ({ error, resetErrorBoundary }) => {
  useEffect(() => {
    logError(error, { component: 'ErrorFallback', type: 'react_error_boundary' });
  }, [error]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-indigo-900 flex items-center justify-center px-6 py-12">
      <div className="sm:mx-auto sm:w-full sm:max-w-lg">
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <img 
            src="https://tailwindcss.com/plus-assets/img/logos/mark.svg?color=indigo&shade=500" 
            alt="Company" 
            className="mx-auto h-10 w-auto" 
          />
          <h2 className="mt-6 text-center text-2xl/9 font-bold tracking-tight text-white">
            Something went wrong
          </h2>
        </div>

        {/* Error Card */}
        <div className="rounded-lg bg-white/5 p-8 backdrop-blur-sm border border-white/10">
          {/* Error Icon */}
          <div className="flex justify-center mb-6">
            <div className="rounded-full bg-red-500/10 p-3">
              <svg 
                className="h-8 w-8 text-red-400" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" 
                />
              </svg>
            </div>
          </div>

          {/* Error Message */}
          <div className="text-center mb-6">
            <p className="text-gray-100 mb-4">
              We encountered an unexpected error. This has been logged and our team will investigate.
            </p>
            
            {/* Error Details (in development) */}
            {process.env.NODE_ENV === 'development' && (
              <details className="mt-4 text-left">
                <summary className="text-sm text-gray-300 cursor-pointer hover:text-white">
                  Error Details (Development Only)
                </summary>
                <div className="mt-2 p-3 bg-black/30 rounded border border-white/10 text-xs text-red-300 overflow-auto">
                  <pre>{error.message}</pre>
                  {error.stack && (
                    <pre className="mt-2 text-gray-400">{error.stack}</pre>
                  )}
                </div>
              </details>
            )}
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            <button
              onClick={resetErrorBoundary}
              className="flex w-full justify-center rounded-md bg-indigo-500 px-3 py-1.5 text-sm/6 font-semibold text-white hover:bg-indigo-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500"
            >
              Try Again
            </button>
            
            <button
              onClick={() => window.location.href = '/'}
              className="flex w-full justify-center rounded-md bg-white/10 px-3 py-1.5 text-sm/6 font-semibold text-white hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Go to Dashboard
            </button>
          </div>
        </div>

        {/* Support Info */}
        <p className="mt-8 text-center text-sm/6 text-gray-400">
          Need help?{" "}
          <a 
            href="mailto:support@company.com" 
            className="font-semibold text-indigo-400 hover:text-indigo-300"
          >
            Contact Support
          </a>
        </p>
      </div>
    </div>
  );
};