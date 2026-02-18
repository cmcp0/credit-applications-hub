import type { AuthPrincipal } from "@/features/auth/model/auth_types";

export function canManageOperationUsers(principal: AuthPrincipal | null): boolean {
  if (!principal || !principal.roles.includes("admin")) {
    return false;
  }
  return principal.permissions.includes("users:manage_operations");
}

export function canManageWorkflows(principal: AuthPrincipal | null): boolean {
  if (!principal || !principal.roles.includes("admin")) {
    return false;
  }
  return principal.permissions.includes("workflows:manage");
}

