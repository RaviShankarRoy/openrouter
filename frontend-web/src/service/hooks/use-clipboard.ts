"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Status = "idle" | "copied" | "error";

export function useClipboard(resetMs = 2000): {
  status: Status;
  copied: boolean;
  copy: (text: string) => Promise<boolean>;
} {
  const [status, setStatus] = useState<Status>("idle");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const copy = useCallback(
    async (text: string): Promise<boolean> => {
      try {
        if (!navigator?.clipboard) throw new Error("Clipboard API unavailable");
        await navigator.clipboard.writeText(text);
        setStatus("copied");
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => setStatus("idle"), resetMs);
        return true;
      } catch {
        setStatus("error");
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => setStatus("idle"), resetMs);
        return false;
      }
    },
    [resetMs],
  );

  return { status, copied: status === "copied", copy };
}
