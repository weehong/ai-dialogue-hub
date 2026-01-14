'use client';

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { Message, WebSocketMessage } from '@/lib/types';

interface WebSocketContextType {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  subscribe: (chatId: number, callback: (message: WebSocketMessage) => void) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

function getWebSocketURL(): string {
  // If NEXT_PUBLIC_WS_URL is set and not localhost, use it
  const envWsUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (envWsUrl && !envWsUrl.includes('localhost')) {
    return envWsUrl;
  }

  // Otherwise, dynamically construct based on current location
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;

    // Use environment variable port if available, otherwise default to 8081
    const wsPort = process.env.NEXT_PUBLIC_WS_PORT || '8081';

    return `${protocol}//${host}:${wsPort}`;
  }

  // Fallback for SSR
  return envWsUrl || 'ws://localhost:8080';
}

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const subscribersRef = useRef<Map<number, Set<(message: WebSocketMessage) => void>>>(new Map());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const wsUrl = getWebSocketURL();
      console.log('Connecting to WebSocket:', wsUrl);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);

          // Handle group updates (broadcast to all global subscribers)
          if (message.type === 'new_group') {
            const globalCallbacks = subscribersRef.current.get(-1);
            if (globalCallbacks) {
              globalCallbacks.forEach((callback) => callback(message));
            }
            return;
          }

          // Notify subscribers for this chat
          let chatId: number | undefined;
          if (message.type === 'delete_message') {
            chatId = (message.payload as { id: string; chat_id: number }).chat_id;
          } else {
            chatId = (message.payload as Message).chat_id;
          }

          if (chatId !== undefined) {
            const callbacks = subscribersRef.current.get(chatId);
            if (callbacks) {
              callbacks.forEach((callback) => callback(message));
            }
          }

          // Also notify global subscribers (chatId = -1)
          const globalCallbacks = subscribersRef.current.get(-1);
          if (globalCallbacks) {
            globalCallbacks.forEach((callback) => callback(message));
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 5000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const subscribe = useCallback(
    (chatId: number, callback: (message: WebSocketMessage) => void) => {
      if (!subscribersRef.current.has(chatId)) {
        subscribersRef.current.set(chatId, new Set());
      }
      subscribersRef.current.get(chatId)!.add(callback);

      // Return unsubscribe function
      return () => {
        const callbacks = subscribersRef.current.get(chatId);
        if (callbacks) {
          callbacks.delete(callback);
          if (callbacks.size === 0) {
            subscribersRef.current.delete(chatId);
          }
        }
      };
    },
    []
  );

  return (
    <WebSocketContext.Provider value={{ isConnected, lastMessage, subscribe }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}
