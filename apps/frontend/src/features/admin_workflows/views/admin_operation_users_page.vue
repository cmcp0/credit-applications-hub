<template>
  <DashboardShell
    role-label="Admin"
    title="Operation Users Administration"
    description="Assign or revoke operation access for authenticated users."
  >
    <section class="grid gap-4">
      <Alert v-if="errorMessage" variant="destructive">{{ errorMessage }}</Alert>
      <Alert v-if="successMessage">{{ successMessage }}</Alert>

      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Assign Operation Role</CardTitle>
          <CardDescription>
            Enter an existing user id and assign operation access.
          </CardDescription>
        </CardHeader>
        <CardContent class="grid gap-3 sm:grid-cols-[1fr_auto]">
          <Input v-model="assignUserId" placeholder="User UUID" />
          <Button :disabled="isAssigning || !assignUserId.trim()" @click="assignRole">
            {{ isAssigning ? "Assigning..." : "Assign Role" }}
          </Button>
        </CardContent>
      </Card>

      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Operation Users</CardTitle>
          <CardDescription>List and enable/disable operation access.</CardDescription>
        </CardHeader>
        <CardContent class="grid gap-4">
          <div class="grid gap-3 sm:grid-cols-[220px_120px_auto_auto]">
            <label class="space-y-2 text-sm">
              <span class="font-medium">Active Filter</span>
              <Input v-model="activeFilter" placeholder="any | true | false" />
            </label>
            <label class="space-y-2 text-sm">
              <span class="font-medium">Page Size</span>
              <Input v-model="pageSizeInput" type="number" min="1" max="100" />
            </label>
            <Button class="self-end" variant="secondary" :disabled="isLoading" @click="applyFilters">
              Apply
            </Button>
            <Button class="self-end" variant="ghost" :disabled="isLoading" @click="loadUsers">
              Refresh
            </Button>
          </div>

          <p v-if="isLoading" class="text-sm text-muted-foreground">Loading users...</p>
          <div v-else-if="users.length === 0" class="text-sm text-muted-foreground">
            No users found for the selected filters.
          </div>

          <div v-else class="overflow-auto">
            <table class="w-full min-w-[880px] text-left text-sm">
              <thead>
                <tr class="border-b border-border text-xs uppercase tracking-[0.08em] text-muted-foreground">
                  <th class="py-2 pr-3">User ID</th>
                  <th class="py-2 pr-3">Email</th>
                  <th class="py-2 pr-3">Active</th>
                  <th class="py-2 pr-3">Operation Access</th>
                  <th class="py-2 pr-3">Updated</th>
                  <th class="py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in users" :key="user.user_id" class="border-b border-border/60">
                  <td class="py-3 pr-3 font-mono text-xs">{{ user.user_id }}</td>
                  <td class="py-3 pr-3">{{ user.email }}</td>
                  <td class="py-3 pr-3">{{ user.is_active ? "Yes" : "No" }}</td>
                  <td class="py-3 pr-3">{{ user.has_operation_role ? "Enabled" : "Disabled" }}</td>
                  <td class="py-3 pr-3">{{ formatDate(user.updated_at) }}</td>
                  <td class="py-3 text-right">
                    <Button
                      size="sm"
                      :variant="user.has_operation_role ? 'secondary' : 'default'"
                      @click="toggleOperationAccess(user.user_id, !user.has_operation_role)"
                    >
                      {{ user.has_operation_role ? "Disable" : "Enable" }}
                    </Button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="flex items-center justify-between border-t border-border pt-3 text-sm">
            <p class="text-muted-foreground">
              Page {{ page }} of {{ totalPages }} ({{ total }} total)
            </p>
            <div class="inline-flex gap-2">
              <Button size="sm" variant="secondary" :disabled="page <= 1 || isLoading" @click="previousPage">
                Previous
              </Button>
              <Button size="sm" variant="secondary" :disabled="page >= totalPages || isLoading" @click="nextPage">
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <RouterLink to="/dashboard/admin">
        <Button variant="secondary">Back to Admin Dashboard</Button>
      </RouterLink>
    </section>
  </DashboardShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  OperationUsersApiError,
} from "@/features/admin_workflows/api/operation_users_api";
import type { OperationUserSummary } from "@/features/admin_workflows/model/admin_workflow_types";
import { createOperationUsersAdminService } from "@/features/admin_workflows/services/operation_users_admin_service";
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";

const service = createOperationUsersAdminService();

const users = ref<OperationUserSummary[]>([]);
const total = ref(0);
const page = ref(1);
const pageSizeInput = ref("20");
const activeFilter = ref("any");
const isLoading = ref(false);
const isAssigning = ref(false);
const assignUserId = ref("");
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

const totalPages = computed(() => {
  const size = normalizePageSize(pageSizeInput.value);
  return Math.max(1, Math.ceil(total.value / size));
});

onMounted(async () => {
  await loadUsers();
});

async function loadUsers(): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  isLoading.value = true;
  try {
    const result = await service.listOperationUsers({
      active: parseActiveFilter(activeFilter.value),
      page: page.value,
      page_size: normalizePageSize(pageSizeInput.value),
    });
    users.value = result.items;
    total.value = result.total;
    page.value = result.page;
    pageSizeInput.value = String(result.page_size);
  } catch (error) {
    errorMessage.value = mapOperationUsersError(error, "Unable to load operation users.");
  } finally {
    isLoading.value = false;
  }
}

async function assignRole(): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  isAssigning.value = true;
  try {
    const result = await service.assignOperationRole({ user_id: assignUserId.value.trim() });
    successMessage.value = `Operation role assigned to ${result.user_id}.`;
    assignUserId.value = "";
    await loadUsers();
  } catch (error) {
    errorMessage.value = mapOperationUsersError(error, "Unable to assign operation role.");
  } finally {
    isAssigning.value = false;
  }
}

async function toggleOperationAccess(userId: string, enabled: boolean): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  try {
    await service.setOperationAccess(userId, { enabled });
    successMessage.value = enabled
      ? "Operation access enabled."
      : "Operation access disabled.";
    await loadUsers();
  } catch (error) {
    errorMessage.value = mapOperationUsersError(error, "Unable to update operation access.");
  }
}

async function previousPage(): Promise<void> {
  if (page.value <= 1) {
    return;
  }
  page.value -= 1;
  await loadUsers();
}

async function nextPage(): Promise<void> {
  if (page.value >= totalPages.value) {
    return;
  }
  page.value += 1;
  await loadUsers();
}

async function applyFilters(): Promise<void> {
  page.value = 1;
  await loadUsers();
}

function parseActiveFilter(value: string): boolean | undefined {
  const normalized = value.trim().toLowerCase();
  if (normalized === "true") {
    return true;
  }
  if (normalized === "false") {
    return false;
  }
  return undefined;
}

function normalizePageSize(raw: string): number {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    return 20;
  }
  return Math.max(1, Math.min(100, Math.trunc(parsed)));
}

function mapOperationUsersError(error: unknown, fallback: string): string {
  if (!(error instanceof OperationUsersApiError)) {
    return fallback;
  }
  if (error.code === "USER_NOT_FOUND") {
    return "User not found. Verify the user id and try again.";
  }
  if (error.code === "ROLE_ALREADY_ASSIGNED") {
    return "The user already has the operation role.";
  }
  return error.message || fallback;
}

function formatDate(raw: string): string {
  const value = new Date(raw);
  if (Number.isNaN(value.getTime())) {
    return raw;
  }
  return value.toLocaleString();
}
</script>

