"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiKeyRepository } from "@/repository/api-key";
import { Button } from "@/api/ui/button";

// AK-004: revoke. Confirmation via native dialog — modal-in-modal is overkill.
export function RevokeKeyButton({ keyId }: { keyId: string }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => apiKeyRepository.revoke(keyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  const onClick = () => {
    if (confirm("Revoke this key? This cannot be undone.")) mutation.mutate();
  };

  return (
    <Button variant="ghost" size="sm" onClick={onClick} disabled={mutation.isPending}>
      {mutation.isPending ? "Revoking…" : "Revoke"}
    </Button>
  );
}
