import type { Router } from "vue-router";

import { canAccessDashboard, resolveDashboardTarget } from "@/features/auth/services/role_redirect";
import type { DashboardRoute } from "@/features/auth/services/role_redirect";
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

    if (to.path === "/") {
      if (!authenticated || !authStore.principal) {
        return { path: "/login" };
      }
      return { path: resolveDashboardTarget(authStore.principal) };
    }

    if (to.path === "/login" && authenticated && authStore.principal) {
      return { path: resolveDashboardTarget(authStore.principal) };
    }

    if (to.meta.requiresAuth !== true) {
      return true;
    }

    if (!authenticated || !authStore.principal) {
      return { path: "/login" };
    }

    if (DASHBOARD_PATHS.has(to.path)) {
      const dashboardRoute = to.path as DashboardRoute;
      if (!canAccessDashboard(authStore.principal.permissions, dashboardRoute)) {
        return { path: "/forbidden" };
      }
    }

    return true;
  });
}
