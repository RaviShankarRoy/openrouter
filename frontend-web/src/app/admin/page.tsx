import { redirect } from "next/navigation";

import { auth } from "@/app/api/auth/[...nextauth]/route";

// AD-009..015: internal admin. RBAC-gated — only owner/admin roles.
// Real role check uses the session.user.role attached during JWT callback.
export default async function AdminPage() {
  const session = await auth();
  const role = (session?.user as { role?: string } | undefined)?.role;
  if (role !== "owner" && role !== "admin") redirect("/dashboard");

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
      <p className="text-sm text-muted-foreground">
        Platform-wide controls. Phase 2: provider health, user management, pricing, abuse flags.
      </p>
    </div>
  );
}
