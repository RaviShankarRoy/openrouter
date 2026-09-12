import Link from "next/link";

import type { Model } from "@/service/model/model";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/api/ui/card";
import { Badge } from "@/api/ui/badge";
import { formatPerMillion } from "@/shared/format";

export function ModelCard({ model }: { model: Model }) {
  return (
    <Link href={`/models/${encodeURIComponent(model.id)}`}>
      <Card className="transition-colors hover:bg-accent">
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-base">{model.id}</CardTitle>
            <Badge variant="outline">{model.provider}</Badge>
          </div>
          <CardDescription>{model.description ?? "—"}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span>ctx: {model.contextWindow.toLocaleString()}</span>
          <span>in: {formatPerMillion(model.pricing.inputPerMillion)}/1M</span>
          <span>out: {formatPerMillion(model.pricing.outputPerMillion)}/1M</span>
          {model.modalities.map((m) => (
            <Badge key={m} variant="secondary">
              {m}
            </Badge>
          ))}
        </CardContent>
      </Card>
    </Link>
  );
}
