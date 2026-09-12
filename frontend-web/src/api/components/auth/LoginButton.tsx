"use client";

import { signIn } from "next-auth/react";

import { Button } from "@/api/ui/button";

// FE-012 OAuth login. Provider passed as prop so caller controls layout.
export function LoginButton({ provider, label }: { provider: "google" | "github"; label: string }) {
  return (
    <Button variant="outline" onClick={() => signIn(provider, { callbackUrl: "/dashboard" })}>
      {label}
    </Button>
  );
}
