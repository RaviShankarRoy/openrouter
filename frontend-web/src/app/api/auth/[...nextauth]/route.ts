import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";
import Google from "next-auth/providers/google";

import { clientEnv, serverEnv } from "@/shared/config/env";

// FE-012: Auth.js v5. JWT strategy keeps sessions stateless and lets us
// attach role/org_id to the session object for RBAC checks.
//
// On first sign-in we exchange the OAuth provider's access token for a
// backend JWT (POST /v1/oauth/exchange). The backend resolves the user via
// the provider's userinfo endpoint, find-or-creates the User+Organization,
// and returns a JWT carrying user_id / org_id / role. We persist that on
// `token.backendJwt` and surface it on the session so client features can
// authenticate against the API.

type ExchangeResponse = {
  access_token: string;
  expires_in: number;
  user_id: string;
  org_id: string;
  role: string;
};

async function exchangeOAuthForBackendJwt(
  provider: "google" | "github",
  accessToken: string,
): Promise<ExchangeResponse | null> {
  const backendUrl = clientEnv.NEXT_PUBLIC_BACKEND_URL;
  try {
    const resp = await fetch(`${backendUrl}/v1/oauth/exchange`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, access_token: accessToken }),
      // No retry: the OAuth callback runs once. If it fails, the user
      // signs in again. Keeping it simple avoids partial-issuance bugs.
    });
    if (!resp.ok) {
      console.warn("oauth exchange failed", resp.status, await resp.text());
      return null;
    }
    return (await resp.json()) as ExchangeResponse;
  } catch (err) {
    console.warn("oauth exchange threw", err);
    return null;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: serverEnv?.GOOGLE_CLIENT_ID ?? "",
      clientSecret: serverEnv?.GOOGLE_CLIENT_SECRET ?? "",
    }),
    GitHub({
      clientId: serverEnv?.GITHUB_CLIENT_ID ?? "",
      clientSecret: serverEnv?.GITHUB_CLIENT_SECRET ?? "",
    }),
  ],
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  callbacks: {
    async jwt({ token, account }) {
      // `account` is only present on the first call after a successful
      // OAuth round-trip. After that we keep replaying token verbatim.
      if (account?.access_token && (account.provider === "google" || account.provider === "github")) {
        const exchanged = await exchangeOAuthForBackendJwt(
          account.provider,
          account.access_token,
        );
        if (exchanged) {
          token.backendJwt = exchanged.access_token;
          token.backendJwtExp = Math.floor(Date.now() / 1000) + exchanged.expires_in;
          token.userId = exchanged.user_id;
          token.orgId = exchanged.org_id;
          token.role = exchanged.role;
        } else {
          // Fall back to the raw OAuth token so the session isn't empty,
          // but downstream API calls will 401. Visible in /api/health.
          token.accessToken = account.access_token;
        }
      }
      return token;
    },
    async session({ session, token }) {
      const enriched = session as unknown as {
        backendJwt?: string;
        userId?: string;
        orgId?: string;
        role?: string;
        accessToken?: string;
      };
      if (token.backendJwt) enriched.backendJwt = token.backendJwt as string;
      if (token.userId) enriched.userId = token.userId as string;
      if (token.orgId) enriched.orgId = token.orgId as string;
      if (token.role) enriched.role = token.role as string;
      if (!token.backendJwt && token.accessToken) {
        enriched.accessToken = token.accessToken as string;
      }
      return session;
    },
  },
});

export const { GET, POST } = handlers;
