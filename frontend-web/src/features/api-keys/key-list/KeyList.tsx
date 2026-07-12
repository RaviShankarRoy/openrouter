"use client";

import { useQuery } from "@tanstack/react-query";

import { apiKeyRepository } from "@/entities/api-key/api";
import { RevokeKeyButton } from "@/features/api-keys/revoke-key-button/RevokeKeyButton";
import { Skeleton } from "@/shared/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";
import { formatDate } from "@/shared/lib/format";

export function KeyList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => apiKeyRepository.list(),
  });

  if (isLoading) return <Skeleton className="h-64" />;
  if (error) return <p className="text-sm text-destructive">Failed to load API keys.</p>;

  const keys = data?.data ?? [];
  if (keys.length === 0) {
    return (
      <p className="rounded border border-dashed p-8 text-center text-sm text-muted-foreground">
        No API keys yet — create your first one above.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Prefix</TableHead>
          <TableHead>Created</TableHead>
          <TableHead>Last used</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {keys.map((k) => (
          <TableRow key={k.id} className={k.revokedAt ? "opacity-50" : ""}>
            <TableCell className="font-medium">{k.name}</TableCell>
            <TableCell className="font-mono text-xs">{k.prefix}…</TableCell>
            <TableCell className="text-sm text-muted-foreground">{formatDate(k.createdAt)}</TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {k.lastUsedAt ? formatDate(k.lastUsedAt) : "—"}
            </TableCell>
            <TableCell className="text-right">
              {k.revokedAt ? <span className="text-xs">revoked</span> : <RevokeKeyButton keyId={k.id} />}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
