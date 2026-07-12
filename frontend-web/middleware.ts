import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Edge-runtime auth guard. Auth.js JWT cookie presence is the gate; full
// session resolution happens in route handlers / RSC. This keeps the edge
// hop cheap and avoids importing the full Auth.js machinery into middleware.
const PROTECTED_PREFIXES = ["/dashboard", "/admin", "/playground"];
const ADMIN_PREFIX = "/admin";
const SESSION_COOKIES = ["authjs.session-token", "__Secure-authjs.session-token"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const requiresAuth = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (!requiresAuth) return NextResponse.next();

  const hasSession = SESSION_COOKIES.some((name) => request.cookies.get(name)?.value);
  if (!hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("from", pathname);
    return NextResponse.redirect(url);
  }

  // RBAC for /admin is enforced in the route's RSC layer where the full
  // session (with role claims) is available.
  if (pathname.startsWith(ADMIN_PREFIX)) {
    const response = NextResponse.next();
    response.headers.set("x-requires-role", "admin");
    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*", "/playground/:path*"],
};
