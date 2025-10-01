import React from 'react';

const Header = ({ isConnected, connectionStatus, sessionId }) => {
  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
      case 'reconnecting':
        return 'bg-yellow-500';
      case 'error':
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'reconnecting':
        return 'Reconnecting...';
      case 'error':
        return 'Connection Error';
      case 'failed':
        return 'Connection Failed';
      default:
        return 'Disconnected';
    }
  };

  const DiamondIcon = () => (
    <svg
      className="w-6 h-6"
      viewBox="0 0 24 24"
      fill="currentColor"
    >
      <path d="M12 2L2 7v10c0 5.55 3.84 10 10 10s10-4.45 10-10V7l-10-5z" />
    </svg>
  );

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Logo and Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center text-white">
            <DiamondIcon />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Payment Data AI</h1>
            <p className="text-xs text-gray-500 hidden sm:block">
              Intelligent payment analytics assistant
            </p>
          </div>
        </div>

        {/* Connection Status */}
        <div className="flex items-center space-x-4">
          {/* Session ID (hidden on mobile) */}
          {sessionId && (
            <div className="hidden md:flex flex-col items-end">
              <span className="text-xs text-gray-500">Session ID</span>
              <span className="text-xs font-mono text-gray-700">
                {sessionId.slice(-8)}
              </span>
            </div>
          )}

          {/* Connection Status Indicator */}
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
            <span className="text-sm text-gray-600 hidden sm:inline">
              {getStatusText()}
            </span>
          </div>

          {/* Connection Details (visible on hover for desktop) */}
          <div className="relative group">
            <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
            
            {/* Tooltip */}
            <div className="absolute right-0 top-full mt-2 w-64 bg-gray-900 text-white text-xs rounded-lg p-3 opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
              <div className="space-y-1">
                <div><strong>Status:</strong> {getStatusText()}</div>
                {sessionId && (
                  <div><strong>Session:</strong> {sessionId}</div>
                )}
                <div><strong>Server:</strong> {process.env.REACT_APP_API_URL || 'localhost:5000'}</div>
              </div>
              {/* Arrow */}
              <div className="absolute -top-1 right-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
