import type { NextConfig } from "next";

// Standalone output keeps the production image small (DRD §22.2 < 200MB).
// Security headers per OWASP baseline; CSP is intentionally minimal here and
// should be tightened per-route once nonce-based RSC streaming lands.
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  // typedRoutes is not yet supported by Turbopack (Next 15.1).
  // Enable it once Turbopack lands support, or use webpack dev (`next dev` without --turbopack).
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts", "@radix-ui/react-dialog"],
  },
  // instrumentation.ts is auto-loaded by Next 15; flag retained for clarity.
  serverExternalPackages: ["pino", "pino-pretty"],
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
      { protocol: "https", hostname: "cdn.openrouter.example.com" },
    ],
    formats: ["image/avif", "image/webp"],
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
