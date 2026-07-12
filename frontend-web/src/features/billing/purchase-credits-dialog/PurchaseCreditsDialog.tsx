"use client";

import { useState } from "react";

import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog";
import { Input } from "@/shared/ui/input";
import { apiClient } from "@/shared/api/client";

// FE-010: Stripe Elements integration is Phase 2. For Phase 1 we redirect
// to a Checkout Session URL the backend creates.
export function PurchaseCreditsDialog() {
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState("25");
  const [busy, setBusy] = useState(false);

  const onPurchase = async () => {
    setBusy(true);
    try {
      const { url } = await apiClient.post<{ url: string }>("/billing/credits/purchase", {
        amount_usd: Number(amount),
      });
      window.location.href = url;
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Add credits</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Purchase credits</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="amount" className="text-sm font-medium">
              Amount (USD)
            </label>
            <Input
              id="amount"
              type="number"
              min="5"
              step="5"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">A 5.5% platform fee applies.</p>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={onPurchase} disabled={busy}>
              {busy ? "Redirecting…" : "Continue to Stripe"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
