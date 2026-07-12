import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { auth } from "@/app/api/auth/[...nextauth]/route";
import { Sidebar } from "@/widgets/sidebar/Sidebar";
import { Topbar } from "@/widgets/topbar/Topbar";

// Server-side session check — middleware only catches missing cookies; this
// confirms the session resolves and exposes role for downstream RBAC checks.
//
// DEV_BYPASS_AUTH=true skips the redirect so the dashboard renders with a
// fake user. Set in .env.local for local exploration; never in prod.
export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const session = await auth();
  const bypass = process.env.DEV_BYPASS_AUTH === "true";

  if (!session?.user && !bypass) redirect("/login?from=/dashboard");

  const user = session?.user ?? { name: "Dev User", email: "dev@local", image: null };

  return (
    <div className="grid min-h-dvh grid-cols-[240px_1fr]">
      <Sidebar />
      <div className="flex min-h-dvh flex-col">
        <Topbar user={user} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
