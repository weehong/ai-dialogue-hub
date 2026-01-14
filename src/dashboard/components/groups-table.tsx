'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  ColumnDef,
  SortingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { ArrowUpDown, MessageSquare, Users, Calendar, ChevronRight } from 'lucide-react';

import { Group } from '@/lib/types';
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

interface GroupsTableProps {
  groups: Group[];
}

export function GroupsTable({ groups }: GroupsTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: 'activated_at', desc: true },
  ]);

  const columns: ColumnDef<Group>[] = [
    {
      accessorKey: 'chat_title',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="-ml-4"
          >
            Group Name
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const title = row.getValue('chat_title') as string;
        return (
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="font-semibold text-foreground">
                {title || 'Unknown Group'}
              </p>
              <p className="text-xs text-muted-foreground">
                ID: {row.original.chat_id}
              </p>
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'message_count',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Messages
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const count = row.getValue('message_count') as number;
        return (
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">{count.toLocaleString()}</span>
          </div>
        );
      },
    },
    {
      accessorKey: 'activated_at',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Activated
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const date = row.getValue('activated_at') as string | Date;
        const dateObj = new Date(date);
        return (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4" />
            <span>{dateObj.toLocaleDateString()}</span>
          </div>
        );
      },
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const group = row.original;
        return (
          <Link href={`/groups/${group.chat_id}`}>
            <Button variant="ghost" size="sm" className="gap-2">
              View
              <ChevronRight className="h-4 w-4" />
            </Button>
          </Link>
        );
      },
    },
  ];

  const table = useReactTable({
    data: groups,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
  });

  return (
    <div className="space-y-4">
      {/* Mobile Card View */}
      <div className="sm:hidden space-y-3">
        {groups.map((group, index) => (
          <Link
            key={group._id}
            href={`/groups/${group.chat_id}`}
            className="block"
          >
            <div className="animate-slide-up rounded-xl border bg-card p-4 shadow-sm transition-all hover:shadow-md hover:border-primary/50"
                 style={{ animationDelay: `${index * 50}ms` }}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-primary shadow-md">
                    <Users className="h-6 w-6 text-primary-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-base text-foreground truncate">
                      {group.chat_title || 'Unknown Group'}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className="text-xs font-mono">
                        {group.chat_id}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <MessageSquare className="h-4 w-4" />
                        <span className="font-medium">{group.message_count.toLocaleString()}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-4 w-4" />
                        <span>{new Date(group.activated_at || '').toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <ChevronRight className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-1" />
              </div>
            </div>
          </Link>
        ))}
        {groups.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No groups found</p>
          </div>
        )}
      </div>

      {/* Desktop Table View */}
      <div className="hidden sm:block rounded-xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="bg-muted/50 hover:bg-muted/50">
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="font-semibold">
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
              table.getRowModel().rows.map((row, index) => (
                <TableRow
                  key={row.id}
                  className="animate-slide-up transition-colors hover:bg-muted/50 cursor-pointer"
                  style={{ animationDelay: `${index * 30}ms` }}
                  onClick={() => {
                    const chatId = row.original.chat_id;
                    window.location.href = `/groups/${chatId}`;
                  }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-32 text-center">
                  <div className="flex flex-col items-center gap-3 text-muted-foreground">
                    <Users className="h-12 w-12 opacity-50" />
                    <p>No groups found</p>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
