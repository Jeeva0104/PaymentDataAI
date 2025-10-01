import { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';

const useSocket = () => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Generate session ID
  const generateSessionId = () => {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  // Get server URL based on environment
  const getServerUrl = () => {
    // Browser always connects to localhost (host machine)
    // regardless of container environment variables
    // since WebSocket connections run in the browser, not in containers
    return 'http://localhost:5000';
  };

  const connect = () => {
    const serverUrl = getServerUrl();
    console.log('Connecting to:', serverUrl);
    
    setConnectionStatus('connecting');
    
    const newSocket = io(serverUrl, {
      transports: ['websocket', 'polling'],
      timeout: 10000,
      reconnection: true,
      reconnectionAttempts: maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });

    // Connection successful
    newSocket.on('connect', () => {
      console.log('Connected to server with ID:', newSocket.id);
      setIsConnected(true);
      setConnectionStatus('connected');
      reconnectAttempts.current = 0;
      
      // Create initial session
      const sessionId = generateSessionId();
      setCurrentSessionId(sessionId);
      newSocket.emit('create_session', { sessionId });
    });

    // Connection failed
    newSocket.on('connect_error', (error) => {
      console.error('Connection error:', error);
      setIsConnected(false);
      setConnectionStatus('error');
      reconnectAttempts.current++;
      
      if (reconnectAttempts.current >= maxReconnectAttempts) {
        setConnectionStatus('failed');
        newSocket.disconnect();
      }
    });

    // Disconnected
    newSocket.on('disconnect', (reason) => {
      console.log('Disconnected:', reason);
      setIsConnected(false);
      setConnectionStatus('disconnected');
      
      // Don't auto-reconnect if it was intentional
      if (reason === 'io client disconnect') {
        setConnectionStatus('disconnected');
      } else {
        setConnectionStatus('reconnecting');
      }
    });

    // Reconnecting
    newSocket.on('reconnect', (attemptNumber) => {
      console.log('Reconnected after', attemptNumber, 'attempts');
      setIsConnected(true);
      setConnectionStatus('connected');
      reconnectAttempts.current = 0;
    });

    // Reconnect failed
    newSocket.on('reconnect_failed', () => {
      console.error('Failed to reconnect after', maxReconnectAttempts, 'attempts');
      setConnectionStatus('failed');
    });

    // Server events
    newSocket.on('connection_established', (data) => {
      console.log('Server connection established:', data);
      if (data.session_id) {
        setCurrentSessionId(data.session_id);
      }
    });

    newSocket.on('error', (error) => {
      console.error('Socket error:', error);
    });

    setSocket(newSocket);
  };

  const disconnect = () => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
      setIsConnected(false);
      setConnectionStatus('disconnected');
      setCurrentSessionId(null);
    }
  };

  const createNewSession = () => {
    if (socket && isConnected) {
      const sessionId = generateSessionId();
      setCurrentSessionId(sessionId);
      socket.emit('create_session', { sessionId });
      console.log('Created new session:', sessionId);
    }
  };

  const sendQuery = (query) => {
    return new Promise((resolve, reject) => {
      if (!socket || !isConnected) {
        reject(new Error('Not connected to server'));
        return;
      }

      if (!query.trim()) {
        reject(new Error('Query cannot be empty'));
        return;
      }

      try {
        socket.emit('user-query', { 
          query: query.trim(),
          sessionId: currentSessionId 
        });
        resolve();
      } catch (error) {
        reject(error);
      }
    });
  };

  const ping = () => {
    if (socket && isConnected) {
      socket.emit('ping');
    }
  };

  const getSessionInfo = () => {
    if (socket && isConnected) {
      socket.emit('get_session_info');
    }
  };

  // Auto-connect on mount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, []);

  // Heartbeat to keep connection alive
  useEffect(() => {
    if (!isConnected) return;

    const heartbeat = setInterval(() => {
      if (socket && isConnected) {
        ping();
      }
    }, 30000); // 30 seconds

    return () => clearInterval(heartbeat);
  }, [isConnected, socket]);

  return {
    socket,
    isConnected,
    connectionStatus,
    currentSessionId,
    connect,
    disconnect,
    createNewSession,
    sendQuery,
    ping,
    getSessionInfo
  };
};

export default useSocket;
