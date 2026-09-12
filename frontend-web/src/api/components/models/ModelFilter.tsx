"use client";

import type { Modality } from "@/service/model/model";
import { Input } from "@/api/ui/input";
import { Badge } from "@/api/ui/badge";

interface Props {
  query: string;
  onQueryChange: (q: string) => void;
  modality: Modality | "all";
  onModalityChange: (m: Modality | "all") => void;
}

const MODALITIES: Array<Modality | "all"> = ["all", "text", "image", "audio", "video", "embedding"];

// MK-002: filter by modality + free text. State lives in the parent so the
// list can be a server component when codegen lands.
export function ModelFilter({ query, onQueryChange, modality, onModalityChange }: Props) {
  return (
    <div className="space-y-3">
      <Input
        placeholder="Search models…"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
      />
      <div className="flex flex-wrap gap-2">
        {MODALITIES.map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => onModalityChange(m)}
            className="cursor-pointer"
          >
            <Badge variant={m === modality ? "default" : "outline"}>{m}</Badge>
          </button>
        ))}
      </div>
    </div>
  );
}
