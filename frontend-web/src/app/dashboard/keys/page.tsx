import type { Metadata } from "next";

import { CreateKeyDialog } from "@/api/components/api-keys/CreateKeyDialog";
import { KeyList } from "@/api/components/api-keys/KeyList";

export const metadata: Metadata = {
  title: "API keys",
};

// FE-004: API key management. Container handles the layout; KeyList fetches
// + renders, CreateKeyDialog owns its own state.
export default function KeysPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">API keys</h1>
          <p className="text-sm text-muted-foreground">
            Issue, label, and revoke keys. The plaintext value is shown once at creation.
          </p>
        </div>
        <CreateKeyDialog />
      </div>
      <KeyList />
    </div>
  );
}
