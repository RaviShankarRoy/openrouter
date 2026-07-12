import { apiClient } from "@/shared/api/client";
import type { User } from "@/entities/user/types";

// Repository for the User domain model. Backed by /users/me on the BFF.
export const userRepository = {
  me: (): Promise<User> => apiClient.get<User>("/users/me"),
  update: (patch: Partial<Pick<User, "name" | "image">>): Promise<User> =>
    apiClient.patch<User>("/users/me", patch),
};
