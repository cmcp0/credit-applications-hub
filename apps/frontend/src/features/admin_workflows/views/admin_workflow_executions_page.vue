<template>
  <DashboardShell
    role-label="Admin"
    title="Workflow Executions"
    description="Inspect async execution lifecycle, retries, and failure details."
  >
    <section class="grid gap-4">
      <Alert v-if="errorMessage" variant="destructive">{{ errorMessage }}</Alert>

      <Card custom-class="border-border/80">
        <CardHeader class="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Execution Diagnostics</CardTitle>
            <CardDescription>Workflow id: <code>{{ workflowId }}</code></CardDescription>
          </div>
          <Button size="sm" variant="ghost" :disabled="isLoading" @click="loadExecutions">Refresh</Button>
        </CardHeader>
        <CardContent class="grid gap-4">
          <div class="grid gap-3 sm:grid-cols-[160px_1fr_1fr_140px_140px]">
            <Input v-model="statusFilter" placeholder="FAILED|RUNNING" />
            <Input v-model="applicationIdFilter" placeholder="application_id" />
            <Input v-model="correlationIdFilter" placeholder="correlation_id" />
            <Input v-model="sortBy" placeholder="updated_at" />
            <Input v-model="sortDir" placeholder="desc" />
          </div>
          <div class="grid gap-3 sm:grid-cols-[1fr_1fr_120px_auto_auto]">
            <Input v-model="fromFilter" placeholder="from ISO datetime" />
            <Input v-model="toFilter" placeholder="to ISO datetime" />
            <Input v-model="pageSizeInput" type="number" min="1" max="100" />
            <Button variant="secondary" :disabled="isLoading" @click="applyFilters">Apply</Button>
            <Button variant="ghost" :disabled="isLoading" @click="resetFilters">Reset</Button>
          </div>

          <p v-if="isLoading" class="text-sm text-muted-foreground">Loading executions...</p>
          <div v-else-if="executions.length === 0" class="text-sm text-muted-foreground">
            No executions found for this workflow.
          </div>

          <div v-else class="overflow-auto">
            <table class="w-full min-w-[1280px] text-left text-sm">
              <thead>
                <tr class="border-b border-border text-xs uppercase tracking-[0.08em] text-muted-foreground">
                  <th class="py-2 pr-3">Job ID</th>
                  <th class="py-2 pr-3">Status</th>
                  <th class="py-2 pr-3">Attempts</th>
                  <th class="py-2 pr-3">Operation</th>
                  <th class="py-2 pr-3">Sub Operation</th>
                  <th class="py-2 pr-3">Correlation</th>
                  <th class="py-2 pr-3">Last Error</th>
                  <th class="py-2 pr-3">Updated</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="execution in executions" :key="execution.job_id" class="border-b border-border/60">
                  <td class="py-3 pr-3 font-mono text-xs">{{ execution.job_id }}</td>
                  <td class="py-3 pr-3">{{ execution.status }}</td>
                  <td class="py-3 pr-3">{{ execution.attempts }} / {{ execution.max_attempts }}</td>
                  <td class="py-3 pr-3">
                    <span v-if="execution.operation">{{ execution.operation.name }}</span>
                    <span v-else>-</span>
                  </td>
                  <td class="py-3 pr-3">
                    <span v-if="execution.sub_operation">{{ execution.sub_operation.execution_type }}</span>
                    <span v-else>-</span>
                  </td>
                  <td class="py-3 pr-3 font-mono text-xs">{{ execution.correlation_id }}</td>
                  <td class="py-3 pr-3">
                    {{ execution.last_error_code || "-" }}
                    <span v-if="execution.last_error_message">
                      : {{ execution.last_error_message }}
                    </span>
                  </td>
                  <td class="py-3 pr-3">{{ formatDate(execution.updated_at) }}</td>
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

      <RouterLink to="/dashboard/admin/workflows">
        <Button variant="secondary">Back to Workflow Administration</Button>
      </RouterLink>
    </section>
  </DashboardShell>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { WorkflowsAdminApiError } from "@/features/admin_workflows/api/workflows_admin_api";
import type { WorkflowExecutionSummary } from "@/features/admin_workflows/model/admin_workflow_types";
import { createExecutionAdminService } from "@/features/admin_workflows/services/execution_admin_service";
import { useAdminWorkflowsStore } from "@/features/admin_workflows/store/admin_workflows_store";
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";

const route = useRoute();
const store = useAdminWorkflowsStore();
const service = createExecutionAdminService();

const workflowId = computed(() => String(route.params.workflowId ?? ""));
const executions = ref<WorkflowExecutionSummary[]>([]);
const isLoading = ref(false);
const errorMessage = ref<string | null>(null);
const page = ref(1);
const pageSizeInput = ref("20");
const total = ref(0);

const statusFilter = ref("");
const applicationIdFilter = ref("");
const correlationIdFilter = ref("");
const fromFilter = ref("");
const toFilter = ref("");
const sortBy = ref("updated_at");
const sortDir = ref("desc");

let pollTimer: number | null = null;

const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / normalizePageSize(pageSizeInput.value))),
);

onMounted(async () => {
  store.setSelectedWorkflow(workflowId.value);
  document.addEventListener("visibilitychange", onVisibilityChange);
  await loadExecutions();
  startPolling();
});

onUnmounted(() => {
  stopPolling();
  document.removeEventListener("visibilitychange", onVisibilityChange);
});

function onVisibilityChange(): void {
  if (document.hidden) {
    stopPolling();
    return;
  }
  startPolling();
}

function startPolling(): void {
  if (!store.isPollingEnabled || pollTimer !== null || document.hidden) {
    return;
  }
  pollTimer = window.setInterval(() => {
    void loadExecutions();
  }, store.pollingIntervalMs);
}

function stopPolling(): void {
  if (pollTimer === null) {
    return;
  }
  window.clearInterval(pollTimer);
  pollTimer = null;
}

async function loadExecutions(): Promise<void> {
  errorMessage.value = null;
  isLoading.value = true;
  try {
    const result = await service.listWorkflowExecutions(workflowId.value, {
      status: statusFilter.value || undefined,
      application_id: applicationIdFilter.value || undefined,
      correlation_id: correlationIdFilter.value || undefined,
      from: fromFilter.value || undefined,
      to: toFilter.value || undefined,
      sort_by: normalizeExecutionSortBy(sortBy.value),
      sort_dir: normalizeSortDir(sortDir.value),
      page: page.value,
      page_size: normalizePageSize(pageSizeInput.value),
    });
    executions.value = result.items;
    total.value = result.total;
    page.value = result.page;
    pageSizeInput.value = String(result.page_size);
    sortBy.value = result.sort_by;
    sortDir.value = result.sort_dir;
  } catch (error) {
    errorMessage.value = mapExecutionError(error, "Unable to load workflow executions.");
  } finally {
    isLoading.value = false;
  }
}

async function applyFilters(): Promise<void> {
  page.value = 1;
  await loadExecutions();
}

async function resetFilters(): Promise<void> {
  statusFilter.value = "";
  applicationIdFilter.value = "";
  correlationIdFilter.value = "";
  fromFilter.value = "";
  toFilter.value = "";
  sortBy.value = "updated_at";
  sortDir.value = "desc";
  page.value = 1;
  await loadExecutions();
}

async function previousPage(): Promise<void> {
  if (page.value <= 1) {
    return;
  }
  page.value -= 1;
  await loadExecutions();
}

async function nextPage(): Promise<void> {
  if (page.value >= totalPages.value) {
    return;
  }
  page.value += 1;
  await loadExecutions();
}

function normalizePageSize(raw: string): number {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    return 20;
  }
  return Math.max(1, Math.min(100, Math.trunc(parsed)));
}

function normalizeExecutionSortBy(raw: string): "updated_at" | "available_at" | "created_at" {
  const normalized = raw.trim().toLowerCase();
  if (normalized === "available_at") {
    return "available_at";
  }
  if (normalized === "created_at") {
    return "created_at";
  }
  return "updated_at";
}

function normalizeSortDir(raw: string): "asc" | "desc" {
  return raw.trim().toLowerCase() === "asc" ? "asc" : "desc";
}

function mapExecutionError(error: unknown, fallback: string): string {
  if (!(error instanceof WorkflowsAdminApiError)) {
    return fallback;
  }
  if (error.code === "INVALID_QUERY_PARAMS") {
    return "Invalid execution query parameters.";
  }
  if (error.code === "WORKFLOW_NOT_FOUND") {
    return "Workflow was not found.";
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

