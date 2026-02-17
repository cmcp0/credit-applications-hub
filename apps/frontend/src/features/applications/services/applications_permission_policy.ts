import type { AuthPrincipal, RoleCode } from "@/features/auth/model/auth_types";

export type ApplicationsRoute = "/applications/customer" | "/applications/operation";

const APPLICATIONS_MODULE_ROLES: readonly RoleCode[] = ["customer", "operation"];
const CUSTOMER_ACCESS_PERMISSION = "applications:list_own";
const CUSTOMER_CREATE_PERMISSION = "applications:create";
const OPERATION_ACCESS_PERMISSION = "applications:list_all";
const OPERATION_STATUS_UPDATE_PERMISSION = "applications:update_customer";

export function canAccessApplicationsModule(role: RoleCode, permissions: string[]): boolean {
  if (role === "customer") {
    return permissions.includes(CUSTOMER_ACCESS_PERMISSION);
  }

  if (role === "operation") {
    return permissions.includes(OPERATION_ACCESS_PERMISSION);
  }

  return false;
}

export function canUpdateApplicationStatus(role: RoleCode, permissions: string[]): boolean {
  if (role !== "operation") {
    return false;
  }

  return permissions.includes(OPERATION_STATUS_UPDATE_PERMISSION);
}

export function canCreateApplication(role: RoleCode, permissions: string[]): boolean {
  if (role !== "customer") {
    return false;
  }

  return permissions.includes(CUSTOMER_CREATE_PERMISSION);
}

export function resolveApplicationsTarget(
  principal: AuthPrincipal,
): ApplicationsRoute | "/forbidden" {
  if (principal.roles.includes("admin")) {
    return "/forbidden";
  }

  if (
    principal.roles.includes("operation") &&
    canAccessApplicationsModule("operation", principal.permissions)
  ) {
    return "/applications/operation";
  }

  if (
    principal.roles.includes("customer") &&
    canAccessApplicationsModule("customer", principal.permissions)
  ) {
    return "/applications/customer";
  }

  return "/forbidden";
}

export function hasApplicationsRole(principal: AuthPrincipal): boolean {
  return APPLICATIONS_MODULE_ROLES.some((role) => principal.roles.includes(role));
}
