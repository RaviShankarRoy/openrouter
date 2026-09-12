import "next-auth";

// The `jwt` callback in src/app/api/auth/[...nextauth]/route.ts enriches the
// session with the backend-issued JWT and the identity it encodes. Declare
// those here so server actions can read them without casting.
declare module "next-auth" {
  interface Session {
    backendJwt?: string;
    userId?: string;
    orgId?: string;
    role?: string;
    /** Only set when the backend token exchange failed. */
    accessToken?: string;
  }
}
