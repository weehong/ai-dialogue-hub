'use client';

import { useEffect, useState } from 'react';
import { GroupsTable } from '@/components/groups-table';
import { Group } from '@/lib/types';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useWebSocket } from '@/components/websocket-provider';
import { Badge } from '@/components/ui/badge';
import { Activity, TrendingUp, Users } from 'lucide-react';

export default function DashboardPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { isConnected, subscribe } = useWebSocket();

  const fetchGroups = async () => {
    try {
      const response = await fetch('/api/groups');
      if (!response.ok) {
        throw new Error('Failed to fetch groups');
      }
      const data = await response.json();
      setGroups(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGroups();
  }, []);

  // Subscribe to WebSocket updates for new groups
  useEffect(() => {
    const unsubscribe = subscribe(-1, (message) => {
      if (message.type === 'new_group') {
        const newGroup = message.payload as Group;
        setGroups((prevGroups) => {
          const exists = prevGroups.some((g) => g.chat_id === newGroup.chat_id);
          if (exists) {
            return prevGroups;
          }
          return [newGroup, ...prevGroups];
        });
      }
    });

    return () => {
      unsubscribe();
    };
  }, [subscribe]);

  // Calculate stats
  const totalMessages = groups.reduce((sum, group) => sum + (group.message_count || 0), 0);
  const totalGroups = groups.length;

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Dashboard Overview
          </h1>
          <p className="mt-2 text-muted-foreground text-sm sm:text-base">
            Monitor and manage your Telegram group message logs
          </p>
        </div>
        <Badge
          variant={isConnected ? 'default' : 'secondary'}
          className="flex items-center gap-2 w-fit px-4 py-2"
        >
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
          {isConnected ? 'Live' : 'Offline'}
        </Badge>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="animate-slide-up border-l-4 border-l-primary">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Users className="h-4 w-4" />
              Active Groups
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-foreground">
              {isLoading ? (
                <Skeleton className="h-9 w-16" />
              ) : (
                totalGroups.toLocaleString()
            )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Groups with logging enabled
            </p>
          </CardContent>
        </Card>

        <Card className="animate-slide-up border-l-4 border-l-chart-2" style={{ animationDelay: '100ms' }}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Total Messages
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-foreground">
              {isLoading ? (
                <Skeleton className="h-9 w-24" />
              ) : (
                totalMessages.toLocaleString()
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Messages across all groups
            </p>
          </CardContent>
        </Card>

        <Card className="animate-slide-up border-l-4 border-l-chart-3 sm:col-span-2 lg:col-span-1" style={{ animationDelay: '200ms' }}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Average per Group
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-foreground">
              {isLoading ? (
                <Skeleton className="h-9 w-20" />
              ) : (
                Math.round(totalMessages / (totalGroups || 1)).toLocaleString()
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Messages per group
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Error State */}
      {error && (
        <Card className="border-destructive animate-slide-up">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      )}

      {/* Groups Table/Cards */}
      {isLoading ? (
        <Card className="animate-slide-up">
          <CardHeader>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64 mt-2" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="animate-slide-up" style={{ animationDelay: '300ms' }}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              Active Groups
            </CardTitle>
            <CardDescription>
              Click on a group to view and search its message history
            </CardDescription>
          </CardHeader>
          <CardContent>
            <GroupsTable groups={groups} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
