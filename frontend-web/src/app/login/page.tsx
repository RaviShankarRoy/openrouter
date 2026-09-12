import type { Metadata } from "next";

import { LoginButton } from "@/api/components/auth/LoginButton";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/api/ui/card";

export const metadata: Metadata = { title: "Sign in" };

// FE-012: OAuth-only sign-in. Phase 2 adds magic-link via Resend.
export default function LoginPage() {
  return (
    <div className="grid min-h-dvh place-items-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>Continue with your developer account.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <LoginButton provider="google" label="Continue with Google" />
          <LoginButton provider="github" label="Continue with GitHub" />
          <p className="mt-4 text-center text-xs text-muted-foreground">
            New here? Signing in creates an account automatically.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
