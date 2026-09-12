"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { apiKeyRepository } from "@/repository/api-key";
import { Button } from "@/api/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/api/ui/dialog";
import { Input } from "@/api/ui/input";
import { useClipboard } from "@/service/hooks/use-clipboard";

const schema = z.object({
  name: z.string().min(1, "Name is required").max(64),
  monthlyBudgetUsd: z.coerce.number().min(0).optional(),
  expiresInDays: z.coerce.number().int().min(1).max(3650).optional(),
});

type FormValues = z.infer<typeof schema>;

// FE-004 + AK-003. Two-step: collect → confirm. Plaintext shown ONCE.
export function CreateKeyDialog() {
  const [open, setOpen] = useState(false);
  const [secret, setSecret] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { copy, copied } = useClipboard();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => apiKeyRepository.create(values),
    onSuccess: (data) => {
      setSecret(data.secret);
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const reset = () => {
    setSecret(null);
    setOpen(false);
    form.reset();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => (o ? setOpen(true) : reset())}>
      <DialogTrigger asChild>
        <Button>Create key</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{secret ? "Save your key" : "Create API key"}</DialogTitle>
        </DialogHeader>

        {secret ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Copy this key now — it cannot be shown again.
            </p>
            <pre className="overflow-x-auto rounded bg-muted p-3 font-mono text-xs">{secret}</pre>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => copy(secret)}>
                {copied ? "Copied" : "Copy"}
              </Button>
              <Button onClick={reset}>Done</Button>
            </div>
          </div>
        ) : (
          <form
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
            className="space-y-4"
          >
            <div className="space-y-1">
              <label htmlFor="name" className="text-sm font-medium">
                Name
              </label>
              <Input id="name" placeholder="prod-server-01" {...form.register("name")} />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive">{form.formState.errors.name.message}</p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label htmlFor="budget" className="text-sm font-medium">
                  Monthly budget USD
                </label>
                <Input id="budget" type="number" step="0.01" min="0" {...form.register("monthlyBudgetUsd")} />
              </div>
              <div className="space-y-1">
                <label htmlFor="expires" className="text-sm font-medium">
                  Expires in (days)
                </label>
                <Input id="expires" type="number" min="1" {...form.register("expiresInDays")} />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={reset}>
                Cancel
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Creating…" : "Create"}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
