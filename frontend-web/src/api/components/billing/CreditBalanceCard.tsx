import { apiClient } from "@/repository/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/api/ui/card";
import { formatCurrency } from "@/shared/format";

interface BalanceResponse {
  available: number;
  reserved: number;
  monthly_cap: number | null;
}

// FE-010: server-rendered card. Renders zero state without flicker because
// the request is awaited on the server.
export async function CreditBalanceCard() {
  let balance: BalanceResponse | null = null;
  try {
    balance = await apiClient.get<BalanceResponse>("/billing/balance");
  } catch {
    // Network errors here just show a fallback, don't break the page.
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Credits</CardTitle>
        <CardDescription>Available balance</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-semibold">
          {balance ? formatCurrency(balance.available) : "—"}
        </p>
        {balance?.reserved ? (
          <p className="text-xs text-muted-foreground">
            {formatCurrency(balance.reserved)} reserved
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
