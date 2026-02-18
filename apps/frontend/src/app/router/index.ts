import { createRouter, createWebHistory } from "vue-router";

import type { AuthStore } from "@/features/auth/store/auth_store";
import { installAuthGuards } from "@/app/router/auth_guards";
import RootEntryPage from "@/app/router/root_entry_page.vue";
import LoginPage from "@/features/auth/views/login_page.vue";
import CustomerDashboardPage from "@/features/dashboards/customer_dashboard_page.vue";
import OperationDashboardPage from "@/features/dashboards/operation_dashboard_page.vue";
import AdminDashboardPage from "@/features/dashboards/admin_dashboard_page.vue";
import CustomerApplicationsPage from "@/features/applications/views/customer_applications_page.vue";
import OperationApplicationsPage from "@/features/applications/views/operation_applications_page.vue";
import AdminOperationUsersPage from "@/features/admin_workflows/views/admin_operation_users_page.vue";
import AdminWorkflowsPage from "@/features/admin_workflows/views/admin_workflows_page.vue";
import AdminWorkflowEditorPage from "@/features/admin_workflows/views/admin_workflow_editor_page.vue";
import AdminWorkflowWebhooksPage from "@/features/admin_workflows/views/admin_workflow_webhooks_page.vue";
import AdminWorkflowExecutionsPage from "@/features/admin_workflows/views/admin_workflow_executions_page.vue";
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
        path: "/dashboard/admin/operation-users",
        component: AdminOperationUsersPage,
        meta: {
          requiresAuth: true,
          allowedRoles: ["admin"],
          requiredPermissions: ["users:manage_operations"],
        },
      },
      {
        path: "/dashboard/admin/workflows",
        component: AdminWorkflowsPage,
        meta: {
          requiresAuth: true,
          allowedRoles: ["admin"],
          requiredPermissions: ["workflows:manage"],
        },
      },
      {
        path: "/dashboard/admin/workflows/:workflowId/editor",
        component: AdminWorkflowEditorPage,
        meta: {
          requiresAuth: true,
          allowedRoles: ["admin"],
          requiredPermissions: ["workflows:manage"],
        },
      },
      {
        path: "/dashboard/admin/workflows/:workflowId/webhooks",
        component: AdminWorkflowWebhooksPage,
        meta: {
          requiresAuth: true,
          allowedRoles: ["admin"],
          requiredPermissions: ["workflows:manage"],
        },
      },
      {
        path: "/dashboard/admin/workflows/:workflowId/executions",
        component: AdminWorkflowExecutionsPage,
        meta: {
          requiresAuth: true,
          allowedRoles: ["admin"],
          requiredPermissions: ["workflows:manage"],
        },
      },
      {
        path: "/applications",
        component: RootEntryPage,
        meta: { requiresAuth: true },
      },
      {
        path: "/applications/customer",
        component: CustomerApplicationsPage,
        meta: {
          requiresAuth: true,
          allowedRoles: ["customer"],
          requiredPermissions: ["applications:list_own"],
        },
      },
      {
        path: "/applications/operation",
        component: OperationApplicationsPage,
        meta: {
          requiresAuth: true,
          allowedRoles: ["operation"],
          requiredPermissions: ["applications:list_all"],
        },
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
