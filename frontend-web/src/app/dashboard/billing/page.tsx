import type { Metadata } from "next";
import { Suspense } from "react";

import { CreditBalanceCard } from "@/api/components/billing/CreditBalanceCard";
import { PurchaseCreditsDialog } from "@/api/components/billing/PurchaseCreditsDialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/api/ui/card";
import { Skeleton } from "@/api/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/api/ui/table";

export const metadata: Metadata = {
  title: "Billing",
};

// FE-010 billing UI. Placeholder invoice list — wired to /billing/invoices once
// PY-011 (Stripe) lands.
export default function BillingPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
          <p className="text-sm text-muted-foreground">Credit balance, purchases, and invoices.</p>
        </div>
        <PurchaseCreditsDialog />
      </div>

      <Suspense fallback={<Skeleton className="h-32" />}>
        <CreditBalanceCard />
      </Suspense>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Invoices</CardTitle>
          <CardDescription>Stripe-hosted invoices for past purchases.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Receipt</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={4} className="text-center text-sm text-muted-foreground">
                  No invoices yet.
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
