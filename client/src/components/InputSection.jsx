import React from 'react';

const InputSection = ({
  value,
  onChange,
  onSend,
  onNewSession,
  isLoading,
  isConnected,
  placeholder = "Ask me anything about your payments..."
}) => {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (value.trim() && isConnected && !isLoading) {
      onSend(value.trim());
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleNewSessionClick = () => {
    if (isConnected && onNewSession) {
      onNewSession();
    }
  };

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="flex items-end space-x-3">
        {/* Plus icon for new session */}
        <button
          type="button"
          onClick={handleNewSessionClick}
          disabled={!isConnected}

          className="flex-shrink-0 w-10 h-10 bg-white border border-gray-300 rounded-lg flex items-center justify-center text-gray-600 hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed transform -translate-y-3"

          title="Start new session"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </button>

        {/* Input field container */}
        <div className="flex-1 relative">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            disabled={!isConnected || isLoading}
            rows="1"
            className="input-field resize-none min-h-[3rem] max-h-32 pr-14 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              resize: 'none',
              overflow: 'hidden'
            }}
            onInput={(e) => {
              // Auto-resize textarea
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px';
            }}
          />

          {/* Send button inside input */}
          <button
            type="submit"
            disabled={!value.trim() || !isConnected || isLoading}
            className="absolute right-2 bottom-3 w-10 h-10 bg-primary-600 text-white rounded-lg flex items-center justify-center transition-all duration-200 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Send message"
          >
            {isLoading ? (
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
      </form>

      {/* Connection status message */}
      {!isConnected && (
        <div className="mt-2 text-center">
          <span className="text-sm text-red-600 bg-red-50 px-3 py-1 rounded-full">
            Not connected to server
          </span>
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div className="mt-2 text-center">
          <span className="text-sm text-gray-600">
            <span className="loading-dots">Processing your request</span>
          </span>
        </div>
      )}

      {/* Helpful hints */}
      <div className="mt-3 text-center text-xs text-gray-500">
        <span>Press Enter to send • Shift+Enter for new line • Click + to start new session</span>
      </div>
    </div>
  );
};

export default InputSection;
