import type { Router } from "vue-router";

import { canAccessDashboard, resolveDashboardTarget } from "@/features/auth/services/role_redirect";
import type { DashboardRoute } from "@/features/auth/services/role_redirect";
import { resolveApplicationsTarget } from "@/features/applications/services/applications_permission_policy";
import type { AuthStore } from "@/features/auth/store/auth_store";

const DASHBOARD_PATHS: ReadonlySet<string> = new Set([
  "/dashboard/customer",
  "/dashboard/operation",
  "/dashboard/admin",
]);

export function installAuthGuards(
  router: Router,
  authStore: AuthStore,
): void {
  router.beforeEach((to) => {
    const authenticated = authStore.hasValidSession();
    const principal = authStore.principal;

    if (to.path === "/") {
      if (!authenticated || !principal) {
        return { path: "/login" };
      }
      return { path: resolveDashboardTarget(principal) };
    }

    if (to.path === "/login" && authenticated && principal) {
      return { path: resolveDashboardTarget(principal) };
    }

    if (to.path === "/applications" && authenticated && principal) {
      return { path: resolveApplicationsTarget(principal) };
    }

    if (to.meta.requiresAuth !== true) {
      return true;
    }

    if (!authenticated || !principal) {
      return { path: "/login" };
    }

    if (to.path.startsWith("/applications") && principal.roles.includes("admin")) {
      return { path: "/forbidden" };
    }

    if (DASHBOARD_PATHS.has(to.path)) {
      const dashboardRoute = to.path as DashboardRoute;
      if (!canAccessDashboard(principal.permissions, dashboardRoute)) {
        return { path: "/forbidden" };
      }
    }

    const requiredPermissions = readStringArrayMeta(to.meta.requiredPermissions);
    if (
      requiredPermissions.length > 0 &&
      !requiredPermissions.every((permission) => principal.permissions.includes(permission))
    ) {
      return { path: "/forbidden" };
    }

    const allowedRoles = readStringArrayMeta(to.meta.allowedRoles);
    const principalRoles = principal.roles as string[];
    if (allowedRoles.length > 0 && !allowedRoles.some((role) => principalRoles.includes(role))) {
      return { path: "/forbidden" };
    }

    return true;
  });
}

function readStringArrayMeta(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}
