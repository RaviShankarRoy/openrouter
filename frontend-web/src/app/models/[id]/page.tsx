import { notFound } from "next/navigation";

import { modelRepository } from "@/entities/model/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import { Badge } from "@/shared/ui/badge";
import { formatPerMillion } from "@/shared/lib/format";

interface Props {
  params: Promise<{ id: string }>;
}

// MK-004: model detail page. Server-rendered for SEO.
export default async function ModelDetailPage({ params }: Props) {
  const { id } = await params;
  const decoded = decodeURIComponent(id);
  let model;
  try {
    const list = await modelRepository.list();
    model = list.data.find((m) => m.id === decoded);
  } catch {
    model = undefined;
  }
  if (!model) notFound();

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-3xl font-semibold tracking-tight">{model.id}</h1>
          <Badge variant="outline">{model.provider}</Badge>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">{model.description ?? "—"}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Context window</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{model.contextWindow.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Input price</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{formatPerMillion(model.pricing.inputPerMillion)}</p>
            <p className="text-xs text-muted-foreground">per million tokens</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Output price</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{formatPerMillion(model.pricing.outputPerMillion)}</p>
            <p className="text-xs text-muted-foreground">per million tokens</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Modalities</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-2">
          {model.modalities.map((m) => (
            <Badge key={m} variant="secondary">
              {m}
            </Badge>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
