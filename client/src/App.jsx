import { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import WelcomeSection from './components/WelcomeSection';
import ExamplesSection from './components/ExamplesSection';
import ChatInterface from './components/ChatInterface';
import InputSection from './components/InputSection';
import useSocket from './hooks/useSocket';

function App() {
  const [messages, setMessages] = useState([]);
  const [currentInput, setCurrentInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const loadingTimeoutRef = useRef(null);
  
  const { 
    socket, 
    isConnected, 
    connectionStatus, 
    currentSessionId,
    createNewSession,
    sendQuery 
  } = useSocket();

  const handleSendMessage = async (message) => {
    if (!message.trim() || !isConnected) return;

    setIsLoading(true);
    
    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: message,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setCurrentInput('');

    // Clear any existing timeout
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
    }

    // Set a safety timeout to clear loading state if no response is received
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
      loadingTimeoutRef.current = null;
      const timeoutMessage = {
        id: Date.now() + 2,
        type: 'error',
        content: 'Request timed out. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, timeoutMessage]);
    }, 30000); // 30 seconds timeout
    
    try {
      await sendQuery(message);
      // Note: Loading state will be cleared by socket event handlers
    } catch (error) {
      console.error('Error sending message:', error);
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }
      setIsLoading(false);
      
      // Add error message to chat
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: 'Failed to send message. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleExampleClick = (exampleQuery) => {
    handleSendMessage(exampleQuery);
  };

  const handleNewSession = () => {
    createNewSession();
    setMessages([]);
    setCurrentInput('');
  };

  // Handle socket responses
  useEffect(() => {
    if (!socket) return;

    const handleQueryResponse = (data) => {
      // Clear timeout and loading state
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }
      setIsLoading(false);
      
      const responseMessage = {
        id: Date.now(),
        type: 'assistant',
        content: data,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, responseMessage]);
    };

    const handleQueryError = (data) => {
      // Clear timeout and loading state
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }
      setIsLoading(false);
      
      const errorMessage = {
        id: Date.now(),
        type: 'error',
        content: data.error || 'An error occurred while processing your request.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    };

    const handleConnectionEstablished = (data) => {
      console.log('Connection established:', data);
    };

    socket.on('query_response', handleQueryResponse);
    socket.on('query_error', handleQueryError);
    socket.on('connection_established', handleConnectionEstablished);

    return () => {
      socket.off('query_response', handleQueryResponse);
      socket.off('query_error', handleQueryError);
      socket.off('connection_established', handleConnectionEstablished);
    };
  }, [socket]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
    };
  }, []);

  const showWelcome = messages.length === 0;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header 
        isConnected={isConnected}
        connectionStatus={connectionStatus}
        sessionId={currentSessionId}
      />
      
      <main className="flex-1 flex flex-col">
        {showWelcome ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4">
            <WelcomeSection />
            <ExamplesSection onExampleClick={handleExampleClick} />
          </div>
        ) : (
          <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full px-4">
            <ChatInterface 
              messages={messages}
              isLoading={isLoading}
              isConnected={isConnected}
            />
          </div>
        )}
        
        <div className="bg-white border-t border-gray-200 px-4 py-4">
          <div className="max-w-4xl mx-auto">
            <InputSection
              value={currentInput}
              onChange={setCurrentInput}
              onSend={handleSendMessage}
              onNewSession={handleNewSession}
              isLoading={isLoading}
              isConnected={isConnected}
              placeholder={showWelcome ? "Or type your own question in the input field below" : "Ask me anything about your payments..."}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
