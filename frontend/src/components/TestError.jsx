import { useState } from 'react';

export default function TestError() {
  const [throwError, setThrowError] = useState(false);

  if (throwError) {
    throw new Error('Test error for ErrorBoundary!');
  }

  return (
    <div className="p-4">
      <h2 className="text-white mb-4">Error Boundary Test</h2>
      <button
        onClick={() => setThrowError(true)}
        className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
      >
        Trigger Error
      </button>
    </div>
  );
}