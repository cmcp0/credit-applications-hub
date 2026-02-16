import { createRouter, createWebHistory } from "vue-router";

import type { AuthStore } from "@/features/auth/store/auth_store";
import { installAuthGuards } from "@/app/router/auth_guards";
import RootEntryPage from "@/app/router/root_entry_page.vue";
import LoginPage from "@/features/auth/views/login_page.vue";
import CustomerDashboardPage from "@/features/dashboards/customer_dashboard_page.vue";
import OperationDashboardPage from "@/features/dashboards/operation_dashboard_page.vue";
import AdminDashboardPage from "@/features/dashboards/admin_dashboard_page.vue";
import ForbiddenPage from "@/shared/ui/forbidden_page.vue";

export function createAppRouter(authStore: AuthStore) {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: "/",
        component: RootEntryPage,
        meta: { public: true },
      },
      {
        path: "/login",
        component: LoginPage,
        meta: { public: true },
      },
      {
        path: "/forbidden",
        component: ForbiddenPage,
        meta: { public: true },
      },
      {
        path: "/dashboard/customer",
        component: CustomerDashboardPage,
        meta: { requiresAuth: true },
      },
      {
        path: "/dashboard/operation",
        component: OperationDashboardPage,
        meta: { requiresAuth: true },
      },
      {
        path: "/dashboard/admin",
        component: AdminDashboardPage,
        meta: { requiresAuth: true },
      },
      {
        path: "/:pathMatch(.*)*",
        redirect: "/",
      },
    ],
  });

  installAuthGuards(router, authStore);

  return router;
}
