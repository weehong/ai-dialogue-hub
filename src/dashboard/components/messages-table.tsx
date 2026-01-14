'use client';

import * as React from 'react';
import {
  ColumnDef,
  SortingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { ArrowUpDown, Trash2, User, History } from 'lucide-react';

import { Message } from '@/lib/types';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';

interface MessagesTableProps {
  messages: Message[];
  onDelete: (messageId: string) => Promise<void>;
  isLoading?: boolean;
}

export function MessagesTable({ messages, onDelete, isLoading }: MessagesTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: 'date', desc: true },
  ]);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  const handleDelete = async (messageId: string) => {
    setDeletingId(messageId);
    try {
      await onDelete(messageId);
    } finally {
      setDeletingId(null);
    }
  };

  const columns: ColumnDef<Message>[] = [
    {
      accessorKey: 'date',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Date
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const date = row.getValue('date') as number | string | Date;
        // Handle Unix timestamp (seconds) vs Date/string
        const dateObj = typeof date === 'number' && date < 10000000000
          ? new Date(date * 1000)  // Unix timestamp in seconds
          : new Date(date);
        return (
          <span className="text-sm text-muted-foreground whitespace-nowrap">
            {dateObj.toLocaleString()}
          </span>
        );
      },
    },
    {
      accessorKey: 'from_user',
      header: 'User',
      cell: ({ row }) => {
        const user = row.getValue('from_user') as Message['from_user'];
        if (!user) {
          return <span className="text-muted-foreground">Unknown</span>;
        }
        const displayName = user.username
          ? `@${user.username}`
          : [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Unknown';
        return (
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">{displayName}</span>
          </div>
        );
      },
    },
    {
      accessorKey: 'text',
      header: 'Message',
      cell: ({ row }) => {
        const text = row.getValue('text') as string;
        const caption = row.original.caption;
        const content = text || caption;
        const wasEdited = row.original.was_edited;
        const editHistory = row.original.edit_history;

        if (!content) {
          return (
            <span className="text-muted-foreground italic">
              [Media message]
            </span>
          );
        }

        return (
          <div className="max-w-md">
            <p className="truncate">{content}</p>
            {wasEdited && editHistory && editHistory.length > 0 && (
              <Popover>
                <PopoverTrigger asChild>
                  <Badge
                    variant="secondary"
                    className="text-xs mt-1 cursor-pointer hover:bg-secondary/80"
                  >
                    <History className="h-3 w-3 mr-1" />
                    edited ({editHistory.length})
                  </Badge>
                </PopoverTrigger>
                <PopoverContent className="w-96" align="start">
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm">Edit History</h4>
                    <div className="space-y-2">
                      {editHistory.map((entry, index) => {
                        const editDate = typeof entry.edited_at === 'number' && entry.edited_at < 10000000000
                          ? new Date(entry.edited_at * 1000)
                          : new Date(entry.edited_at);
                        const editContent = entry.text || entry.caption;

                        return (
                          <div
                            key={index}
                            className="p-2 bg-muted rounded text-sm"
                          >
                            <p className="text-xs text-muted-foreground mb-1">
                              {editDate.toLocaleString()}
                            </p>
                            <p className="break-words">
                              {editContent || '[No content]'}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
            )}
            {wasEdited && (!editHistory || editHistory.length === 0) && (
              <Badge variant="secondary" className="text-xs mt-1">
                edited
              </Badge>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'message_id',
      header: 'ID',
      cell: ({ row }) => {
        return (
          <Badge variant="outline" className="font-mono text-xs">
            {row.getValue('message_id')}
          </Badge>
        );
      },
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const message = row.original;
        const isDeleting = deletingId === message._id;

        return (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
                disabled={isDeleting}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Message</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete this message? This action cannot be undone.
                  <div className="mt-2 p-2 bg-muted rounded text-sm">
                    &quot;{(message.text || message.caption || '[Media]').substring(0, 100)}
                    {(message.text || message.caption || '').length > 100 ? '...' : ''}&quot;
                  </div>
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => handleDelete(message._id)}
                  className="bg-destructive hover:bg-destructive/90"
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        );
      },
    },
  ];

  const table = useReactTable({
    data: messages,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>ID</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...Array(5)].map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <div className="h-8 bg-muted animate-pulse rounded" />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center">
                No messages found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
