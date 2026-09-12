import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CreateKeyDialog } from "./CreateKeyDialog";

vi.mock("@/repository/api-key", () => ({
  apiKeyRepository: {
    create: vi.fn().mockResolvedValue({
      id: "k_1",
      name: "test",
      prefix: "sk-or-v1-abc",
      secret: "sk-or-v1-secret",
      createdAt: new Date().toISOString(),
      lastUsedAt: null,
      expiresAt: null,
      revokedAt: null,
      scopes: [],
      monthlyBudgetUsd: null,
    }),
  },
}));

function renderWithProviders(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("CreateKeyDialog", () => {
  it("opens the dialog when the trigger is clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateKeyDialog />);
    await user.click(screen.getByRole("button", { name: /create key/i }));
    expect(await screen.findByRole("heading", { name: /create api key/i })).toBeInTheDocument();
  });

  it("validates that name is required", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateKeyDialog />);
    await user.click(screen.getByRole("button", { name: /create key/i }));
    await user.click(await screen.findByRole("button", { name: /^create$/i }));
    expect(await screen.findByText(/name is required/i)).toBeInTheDocument();
  });
});
