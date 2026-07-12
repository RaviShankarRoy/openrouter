"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { auth } from "@/app/api/auth/[...nextauth]/route";
import { ApiClient } from "@/shared/api/client";
import { clientEnv } from "@/shared/config/env";
import { logger } from "@/shared/lib/logger";
import type { ApiKeyCreateResponse } from "@/entities/api-key/types";

// FE-004 server action. Mutations live here so the form can post without a
// dedicated route handler (Next 15 + React 19 server-action pattern).
const createKeySchema = z.object({
  name: z.string().min(1).max(80),
  scopes: z.array(z.string()).default([]),
  monthlyBudgetUsd: z.number().nonnegative().nullable().default(null),
  expiresInDays: z.number().int().positive().max(365).optional(),
});

export type CreateKeyState =
  | { status: "idle" }
  | { status: "error"; message: string }
  | { status: "success"; key: ApiKeyCreateResponse };

export async function createKeyAction(
  _prev: CreateKeyState,
  formData: FormData,
): Promise<CreateKeyState> {
  const session = await auth();
  if (!session?.user) return { status: "error", message: "Not authenticated" };

  const parsed = createKeySchema.safeParse({
    name: formData.get("name"),
    scopes: formData.getAll("scopes").map(String),
    monthlyBudgetUsd: formData.get("monthlyBudgetUsd")
      ? Number(formData.get("monthlyBudgetUsd"))
      : null,
    expiresInDays: formData.get("expiresInDays")
      ? Number(formData.get("expiresInDays"))
      : undefined,
  });

  if (!parsed.success) {
    return { status: "error", message: parsed.error.issues[0]?.message ?? "Invalid input" };
  }

  try {
    const server = new ApiClient(clientEnv.NEXT_PUBLIC_BACKEND_URL);
    const key = await server.post<ApiKeyCreateResponse>("/keys", parsed.data, {
      bearerToken: session.accessToken,
    });
    revalidatePath("/dashboard/keys");
    return { status: "success", key };
  } catch (error) {
    logger.error({ err: error, userId: session.user.id }, "createKey failed");
    return { status: "error", message: "Could not create key. Try again." };
  }
}

export async function revokeKeyAction(keyId: string): Promise<{ ok: boolean; message?: string }> {
  const session = await auth();
  if (!session?.user) return { ok: false, message: "Not authenticated" };

  try {
    const server = new ApiClient(clientEnv.NEXT_PUBLIC_BACKEND_URL);
    await server.delete<void>(`/keys/${encodeURIComponent(keyId)}`, {
      bearerToken: session.accessToken,
    });
    revalidatePath("/dashboard/keys");
    return { ok: true };
  } catch (error) {
    logger.error({ err: error, keyId }, "revokeKey failed");
    return { ok: false, message: "Revoke failed" };
  }
}
