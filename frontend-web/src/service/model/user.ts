export type UserRole = "user" | "admin" | "owner";

export interface User {
  id: string;
  email: string;
  name: string | null;
  image: string | null;
  role: UserRole;
  organizationId: string | null;
  createdAt: string;
}

export interface Session {
  user: User;
  expires: string;
  accessToken?: string;
}
