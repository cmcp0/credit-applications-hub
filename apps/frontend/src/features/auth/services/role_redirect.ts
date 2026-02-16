import {
  AuthPrincipal,
  RoleCode,
} from "@/features/auth/model/auth_types";

export const ROLE_PRIORITY: readonly RoleCode[] = ["admin", "operation", "customer"];

export const DASHBOARD_BY_ROLE: Record<RoleCode, DashboardRoute> = {
  admin: "/dashboard/admin",
  operation: "/dashboard/operation",
  customer: "/dashboard/customer",
};

export type DashboardRoute =
  | "/dashboard/customer"
  | "/dashboard/operation"
  | "/dashboard/admin";

const DASHBOARD_REQUIREMENTS: Record<DashboardRoute, PermissionRequirement> = {
  "/dashboard/customer": {
    type: "all",
    permissions: ["applications:list_own"],
  },
  "/dashboard/operation": {
    type: "all",
    permissions: ["applications:list_all"],
  },
  "/dashboard/admin": {
    type: "any",
    permissions: ["users:manage_operations", "workflows:manage"],
  },
};

interface PermissionRequirement {
  type: "all" | "any";
  permissions: string[];
}

export function resolveDashboardTarget(principal: AuthPrincipal): DashboardRoute | "/forbidden" {
  for (const role of ROLE_PRIORITY) {
    if (!principal.roles.includes(role)) {
      continue;
    }

    const candidateRoute = DASHBOARD_BY_ROLE[role];
    if (canAccessDashboard(principal.permissions, candidateRoute)) {
      return candidateRoute;
    }
  }

  return "/forbidden";
}

export function canAccessDashboard(
  permissions: string[],
  dashboardRoute: DashboardRoute,
): boolean {
  const requirement = DASHBOARD_REQUIREMENTS[dashboardRoute];
  if (requirement.type === "all") {
    return requirement.permissions.every((permission) => permissions.includes(permission));
  }
  return requirement.permissions.some((permission) => permissions.includes(permission));
}

export function permissionsForDashboard(dashboardRoute: DashboardRoute): PermissionRequirement {
  return DASHBOARD_REQUIREMENTS[dashboardRoute];
}
