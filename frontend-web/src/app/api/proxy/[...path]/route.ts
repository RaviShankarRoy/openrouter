import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/app/api/auth/[...nextauth]/route";
import { serverEnv } from "@/shared/config/env";

// BFF: proxies the browser to the gateway with the user's session token.
// Keeps the bearer token off the client where possible.

export const dynamic = "force-dynamic";

interface RouteParams {
  params: Promise<{ path: string[] }>;
}

async function proxy(req: NextRequest, { params }: RouteParams) {
  const session = await auth();
  const accessToken = (session as { accessToken?: string } | null)?.accessToken;
  if (!accessToken) {
    return NextResponse.json(
      { error: { message: "Not authenticated", type: "authentication_error" } },
      { status: 401 },
    );
  }

  const { path } = await params;
  const target = new URL(`${serverEnv.NEXT_PUBLIC_API_BASE_URL}/api/v1/${path.join("/")}`);
  for (const [k, v] of req.nextUrl.searchParams) target.searchParams.set(k, v);

  const upstream = await fetch(target, {
    method: req.method,
    headers: filterHeaders(req.headers, accessToken),
    body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
    redirect: "manual",
  });

  // Stream SSE responses through unchanged so playground streaming works.
  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: passthroughHeaders(upstream.headers),
  });
}

function filterHeaders(incoming: Headers, token: string): Headers {
  const out = new Headers();
  for (const [k, v] of incoming) {
    if (["host", "cookie", "authorization", "connection"].includes(k.toLowerCase())) continue;
    out.set(k, v);
  }
  out.set("authorization", `Bearer ${token}`);
  return out;
}

function passthroughHeaders(upstream: Headers): Headers {
  const out = new Headers();
  for (const [k, v] of upstream) {
    if (["transfer-encoding", "connection"].includes(k.toLowerCase())) continue;
    out.set(k, v);
  }
  return out;
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
