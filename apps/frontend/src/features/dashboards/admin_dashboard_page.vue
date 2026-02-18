<template>
  <DashboardShell
    role-label="Admin"
    title="Admin Dashboard"
    description="Manage operation users and workflow configuration access."
  >
    <section class="grid gap-4 md:grid-cols-2">
      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Operation Users</CardTitle>
          <CardDescription>
            Assign operation role and enable or disable operation access.
          </CardDescription>
        </CardHeader>
        <CardContent class="flex flex-col gap-3">
          <p class="text-sm text-muted-foreground">
            Permission required: <code>users:manage_operations</code>
          </p>
          <RouterLink v-if="canManageUsers" to="/dashboard/admin/operation-users">
            <Button>Open Operation User Admin</Button>
          </RouterLink>
          <Alert v-else>
            Your account does not have permission to manage operation users.
          </Alert>
        </CardContent>
      </Card>

      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Workflow Governance</CardTitle>
          <CardDescription>
            Manage workflow versions, graph rules, webhooks, and async execution
            visibility.
          </CardDescription>
        </CardHeader>
        <CardContent class="flex flex-col gap-3">
          <p class="text-sm text-muted-foreground">
            Permission required: <code>workflows:manage</code>
          </p>
          <RouterLink v-if="canManageWorkflowAdmin" to="/dashboard/admin/workflows">
            <Button>Open Workflow Admin</Button>
          </RouterLink>
          <Alert v-else>
            Your account does not have permission to manage workflows.
          </Alert>
        </CardContent>
      </Card>
    </section>
  </DashboardShell>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  canManageOperationUsers,
  canManageWorkflows,
} from "@/features/admin_workflows/services/admin_workflow_permission_policy";
import { useAuthStore } from "@/features/auth/store/auth_store";
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";

const authStore = useAuthStore();
const principal = computed(() => authStore.principal);

const canManageUsers = computed(() => canManageOperationUsers(principal.value));
const canManageWorkflowAdmin = computed(() => canManageWorkflows(principal.value));
</script>
