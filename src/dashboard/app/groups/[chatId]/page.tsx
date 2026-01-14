'use client';

import { useEffect, useState, useCallback, useRef, use } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { Message, WebSocketMessage } from '@/lib/types';
import { MessagesTable } from '@/components/messages-table';
import { SearchInput } from '@/components/search-input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useWebSocket } from '@/components/websocket-provider';

interface MessagesResponse {
  messages: Message[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

interface SearchResponse {
  hits: Message[];
  query: string;
  processingTimeMs: number;
  estimatedTotalHits: number;
}

export default function MessagesPage({
  params,
}: {
  params: Promise<{ chatId: string }>;
}) {
  const { chatId } = use(params);
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const limit = 50;
  const { isConnected, subscribe } = useWebSocket();
  const hasFetched = useRef(false);

  const fetchMessages = useCallback(async (pageNum: number = 1) => {
    try {
      setIsLoading(true);
      const response = await fetch(
        `/api/messages?chatId=${chatId}&page=${pageNum}&limit=${limit}`
      );
      if (!response.ok) {
        throw new Error('Failed to fetch messages');
      }
      const data: MessagesResponse = await response.json();
      setMessages(data.messages);
      setPage(data.pagination.page);
      setTotal(data.pagination.total);
      setTotalPages(data.pagination.totalPages);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }, [chatId]);

  const searchMessages = useCallback(async (query: string) => {
    if (!query.trim()) {
      fetchMessages(page);
      return;
    }

    try {
      setIsSearching(true);
      const response = await fetch(
        `/api/search?q=${encodeURIComponent(query)}&chatId=${chatId}`
      );
      if (!response.ok) {
        throw new Error('Search failed');
      }
      const data: SearchResponse = await response.json();
      setMessages(data.hits);
      setTotal(data.estimatedTotalHits);
      setTotalPages(1);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setIsSearching(false);
    }
  }, [chatId, fetchMessages, page]);

  const handleDelete = async (messageId: string) => {
    try {
      const response = await fetch(`/api/messages/${messageId}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Failed to delete message');
      }
      setMessages((prev) => prev.filter((m) => m._id !== messageId));
      setTotal((prev) => prev - 1);
    } catch (err) {
      console.error('Delete failed:', err);
      throw err;
    }
  };

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    searchMessages(query);
  }, [searchMessages]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    fetchMessages(newPage);
  };

  // Initial fetch - only runs once
  useEffect(() => {
    if (!hasFetched.current) {
      hasFetched.current = true;
      fetchMessages(1);
    }
  }, [fetchMessages]);

  // Subscribe to WebSocket updates for this chat
  useEffect(() => {
    const unsubscribe = subscribe(parseInt(chatId, 10), (wsMessage: WebSocketMessage) => {
      if (wsMessage.type === 'new_message') {
        const newMessage = wsMessage.payload as Message;
        setMessages((prev) => [newMessage, ...prev]);
        setTotal((prev) => prev + 1);
      } else if (wsMessage.type === 'delete_message') {
        const { id } = wsMessage.payload as { id: string; chat_id: number };
        setMessages((prev) => prev.filter((m) => m._id !== id));
        setTotal((prev) => prev - 1);
      } else if (wsMessage.type === 'update_message') {
        const updatedMessage = wsMessage.payload as Message;
        setMessages((prev) =>
          prev.map((m) => (m._id === updatedMessage._id ? updatedMessage : m))
        );
      }
    });

    return () => unsubscribe();
  }, [chatId, subscribe]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push('/')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Messages</h1>
            <p className="text-muted-foreground">
              Chat ID: {chatId} | {total} messages
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={isConnected ? 'default' : 'secondary'}>
            {isConnected ? 'Live' : 'Offline'}
          </Badge>
          <Button
            variant="outline"
            size="icon"
            onClick={() => fetchMessages(page)}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Message Log</CardTitle>
              <CardDescription>
                Search and manage messages in this group
              </CardDescription>
            </div>
          </div>
          <div className="mt-4">
            <SearchInput
              onSearch={handleSearch}
              placeholder="Search messages with Meilisearch..."
              isLoading={isSearching}
            />
          </div>
        </CardHeader>
        <CardContent>
          <MessagesTable
            messages={messages}
            onDelete={handleDelete}
            isLoading={isLoading}
          />

          {/* Pagination */}
          {totalPages > 1 && !searchQuery && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page <= 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(page + 1)}
                  disabled={page >= totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
