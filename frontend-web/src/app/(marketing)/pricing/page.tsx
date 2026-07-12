import type { Metadata } from "next";

import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/shared/ui/card";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Pay only for what you use. No seat fees, no tier upgrades.",
};

const tiers = [
  {
    name: "Pay-as-you-go",
    price: "$0/mo",
    description: "Pure usage-based pricing. Provider price + 5% gateway fee.",
    features: ["All providers", "Unlimited keys", "Standard rate limits", "Community support"],
    cta: "Start free",
    highlighted: false,
  },
  {
    name: "Team",
    price: "$99/mo",
    description: "For teams that need RBAC, audit logs, and higher limits.",
    features: ["Everything in PAYG", "RBAC + audit log", "5x rate limits", "SSO via OIDC", "Priority email"],
    cta: "Start trial",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    description: "Self-hosted, on-prem, or VPC deployment with dedicated support.",
    features: ["Self-host (Helm)", "Custom rate limits", "SLA 99.99%", "Dedicated CSM", "Air-gapped option"],
    cta: "Contact sales",
    highlighted: false,
  },
];

export default function PricingPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <div className="mb-12 text-center">
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Simple, usage-based pricing</h1>
        <p className="mt-3 text-muted-foreground">No seat fees. No surprise overages.</p>
      </div>
      <div className="grid gap-6 md:grid-cols-3">
        {tiers.map((tier) => (
          <Card key={tier.name} className={tier.highlighted ? "border-primary shadow-md" : undefined}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{tier.name}</CardTitle>
                {tier.highlighted ? <Badge>Recommended</Badge> : null}
              </div>
              <div className="mt-2 text-3xl font-semibold">{tier.price}</div>
              <CardDescription className="mt-2">{tier.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-center gap-2">
                    <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-primary" />
                    {f}
                  </li>
                ))}
              </ul>
            </CardContent>
            <CardFooter>
              <Button className="w-full" variant={tier.highlighted ? "default" : "outline"}>
                {tier.cta}
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </main>
  );
}
