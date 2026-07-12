import type { Model } from "@/entities/model/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";
import { formatPerMillion } from "@/shared/lib/format";

// FE-006: side-by-side comparison.
export function ModelComparison({ models }: { models: Model[] }) {
  if (models.length === 0) return null;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Model</TableHead>
          <TableHead>Provider</TableHead>
          <TableHead>Context</TableHead>
          <TableHead>Input / 1M</TableHead>
          <TableHead>Output / 1M</TableHead>
          <TableHead>Quality</TableHead>
          <TableHead>P50 latency</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {models.map((m) => (
          <TableRow key={m.id}>
            <TableCell className="font-medium">{m.id}</TableCell>
            <TableCell>{m.provider}</TableCell>
            <TableCell>{m.contextWindow.toLocaleString()}</TableCell>
            <TableCell>{formatPerMillion(m.pricing.inputPerMillion)}</TableCell>
            <TableCell>{formatPerMillion(m.pricing.outputPerMillion)}</TableCell>
            <TableCell>{m.qualityScore?.toFixed(2) ?? "—"}</TableCell>
            <TableCell>{m.medianLatencyMs ? `${m.medianLatencyMs}ms` : "—"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
