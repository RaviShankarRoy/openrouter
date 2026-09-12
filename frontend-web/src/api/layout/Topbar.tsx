import { SignOutButton } from "@/api/components/auth/SignOutButton";

interface TopbarUser {
  name?: string | null;
  email?: string | null;
  image?: string | null;
}

export function Topbar({ user }: { user: TopbarUser }) {
  return (
    <header className="flex h-14 items-center justify-between border-b px-6">
      <div className="text-sm text-muted-foreground">
        {user.email ? <span>Signed in as {user.email}</span> : null}
      </div>
      <SignOutButton />
    </header>
  );
}
