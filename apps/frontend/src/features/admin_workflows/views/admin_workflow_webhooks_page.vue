<template>
  <DashboardShell
    role-label="Admin"
    title="Workflow Webhooks"
    description="Manage endpoints, inspect event deliveries, and replay failed events."
  >
    <section class="grid gap-4">
      <Alert v-if="errorMessage" variant="destructive">{{ errorMessage }}</Alert>
      <Alert v-if="successMessage">{{ successMessage }}</Alert>

      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Create Endpoint</CardTitle>
          <CardDescription>Workflow id: <code>{{ workflowId }}</code></CardDescription>
        </CardHeader>
        <CardContent class="grid gap-3 sm:grid-cols-2">
          <Input v-model="createDirection" placeholder="EGRESS" />
          <Input v-model="createProviderCode" placeholder="provider_code" />
          <Input v-model="createEventType" placeholder="event_type" />
          <Input v-model="createMethod" placeholder="POST" />
          <Input v-model="createUrl" placeholder="https://provider.example/webhooks/status" />
          <Input v-model="createSecretRef" placeholder="secrets://..." />
          <Input v-model="createTimeoutMs" type="number" min="1000" max="30000" />
          <Button :disabled="isMutating" @click="createEndpoint">
            {{ isMutating ? "Saving..." : "Create Endpoint" }}
          </Button>
        </CardContent>
      </Card>

      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Endpoint Update / Secret Rotation</CardTitle>
        </CardHeader>
        <CardContent class="grid gap-3 sm:grid-cols-[1fr_120px_1fr_auto]">
          <Input v-model="selectedEndpointId" placeholder="endpoint_id" />
          <Input v-model="selectedEndpointActive" placeholder="active true|false" />
          <Input v-model="rotateReason" placeholder="rotation reason" />
          <div class="inline-flex gap-2">
            <Button size="sm" variant="secondary" :disabled="isMutating" @click="updateEndpoint">
              Update
            </Button>
            <Button size="sm" :disabled="isMutating" @click="rotateEndpointSecret">
              Rotate
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card custom-class="border-border/80">
        <CardHeader class="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Webhook Events</CardTitle>
            <CardDescription>Filters, pagination, and replay controls.</CardDescription>
          </div>
          <Button size="sm" variant="ghost" :disabled="isLoading" @click="loadEvents">Refresh</Button>
        </CardHeader>
        <CardContent class="grid gap-4">
          <div class="grid gap-3 sm:grid-cols-[120px_160px_160px_120px]">
            <Input v-model="directionFilter" placeholder="INGRESS|EGRESS" />
            <Input v-model="eventTypeFilter" placeholder="event_type" />
            <Input v-model="deliveryStatusFilter" placeholder="FAILED|DELIVERED" />
            <Input v-model="pageSizeInput" type="number" min="1" max="100" />
          </div>
          <div class="inline-flex gap-2">
            <Button variant="secondary" :disabled="isLoading" @click="applyFilters">Apply</Button>
            <Button variant="ghost" :disabled="isLoading" @click="resetFilters">Reset</Button>
          </div>

          <p v-if="isLoading" class="text-sm text-muted-foreground">Loading webhook events...</p>
          <div v-else-if="events.length === 0" class="text-sm text-muted-foreground">
            No webhook events found.
          </div>

          <div v-else class="overflow-auto">
            <table class="w-full min-w-[1180px] text-left text-sm">
              <thead>
                <tr class="border-b border-border text-xs uppercase tracking-[0.08em] text-muted-foreground">
                  <th class="py-2 pr-3">Event ID</th>
                  <th class="py-2 pr-3">Direction</th>
                  <th class="py-2 pr-3">Type</th>
                  <th class="py-2 pr-3">Status</th>
                  <th class="py-2 pr-3">Occurred</th>
                  <th class="py-2 pr-3">Last Attempt</th>
                  <th class="py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="event in events" :key="event.id" class="border-b border-border/60">
                  <td class="py-3 pr-3 font-mono text-xs">{{ event.id }}</td>
                  <td class="py-3 pr-3">{{ event.direction }}</td>
                  <td class="py-3 pr-3">{{ event.event_type }}</td>
                  <td class="py-3 pr-3">{{ event.delivery_status }}</td>
                  <td class="py-3 pr-3">{{ formatDate(event.occurred_at) }}</td>
                  <td class="py-3 pr-3">
                    <span v-if="event.last_attempt">
                      #{{ event.last_attempt.attempt_no }}
                      {{ event.last_attempt.response_code ?? event.last_attempt.error_code ?? "-" }}
                    </span>
                    <span v-else>-</span>
                  </td>
                  <td class="py-3 text-right">
                    <Button
                      size="sm"
                      :disabled="replayDisabled(event.id)"
                      @click="replayEvent(event.id)"
                    >
                      {{ replayLabel(event.id) }}
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
import type { WorkflowWebhookEventSummary } from "@/features/admin_workflows/model/admin_workflow_types";
import { createWebhookAdminService } from "@/features/admin_workflows/services/webhook_admin_service";
import { useAdminWorkflowsStore } from "@/features/admin_workflows/store/admin_workflows_store";
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";

const route = useRoute();
const store = useAdminWorkflowsStore();
const service = createWebhookAdminService();

const workflowId = computed(() => String(route.params.workflowId ?? ""));
const events = ref<WorkflowWebhookEventSummary[]>([]);
const isLoading = ref(false);
const isMutating = ref(false);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

const directionFilter = ref("");
const eventTypeFilter = ref("");
const deliveryStatusFilter = ref("");
const page = ref(1);
const pageSizeInput = ref("20");
const total = ref(0);

const createDirection = ref("EGRESS");
const createProviderCode = ref("");
const createEventType = ref("");
const createMethod = ref("POST");
const createUrl = ref("");
const createSecretRef = ref("");
const createTimeoutMs = ref("5000");

const selectedEndpointId = ref("");
const selectedEndpointActive = ref("true");
const rotateReason = ref("scheduled_rotation");

let pollTimer: number | null = null;

const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / normalizePageSize(pageSizeInput.value))),
);

onMounted(async () => {
  store.setSelectedWorkflow(workflowId.value);
  document.addEventListener("visibilitychange", onVisibilityChange);
  await loadEvents();
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
    void loadEvents();
  }, store.pollingIntervalMs);
}

function stopPolling(): void {
  if (pollTimer === null) {
    return;
  }
  window.clearInterval(pollTimer);
  pollTimer = null;
}

async function loadEvents(): Promise<void> {
  errorMessage.value = null;
  isLoading.value = true;
  try {
    const result = await service.listWebhookEvents(workflowId.value, {
      direction: directionFilter.value || undefined,
      event_type: eventTypeFilter.value || undefined,
      delivery_status: deliveryStatusFilter.value || undefined,
      page: page.value,
      page_size: normalizePageSize(pageSizeInput.value),
      sort_by: "occurred_at",
      sort_dir: "desc",
    });
    events.value = result.items;
    total.value = result.total;
    page.value = result.page;
    pageSizeInput.value = String(result.page_size);
  } catch (error) {
    errorMessage.value = mapWebhookError(error, "Unable to load webhook events.");
  } finally {
    isLoading.value = false;
  }
}

async function createEndpoint(): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  isMutating.value = true;
  try {
    const created = await service.createWebhookEndpoint(workflowId.value, {
      direction: createDirection.value.trim().toUpperCase(),
      provider_code: createProviderCode.value.trim(),
      event_type: createEventType.value.trim(),
      method: createMethod.value.trim().toUpperCase(),
      url: createUrl.value.trim(),
      secret_ref: createSecretRef.value.trim(),
      timeout_ms: normalizeTimeout(createTimeoutMs.value),
      active: true,
    });
    selectedEndpointId.value = created.endpoint_id;
    successMessage.value = `Endpoint ${created.endpoint_id} created.`;
    await loadEvents();
  } catch (error) {
    errorMessage.value = mapWebhookError(error, "Unable to create webhook endpoint.");
  } finally {
    isMutating.value = false;
  }
}

async function updateEndpoint(): Promise<void> {
  if (!selectedEndpointId.value.trim()) {
    errorMessage.value = "endpoint_id is required to update endpoint.";
    return;
  }
  errorMessage.value = null;
  successMessage.value = null;
  isMutating.value = true;
  try {
    await service.updateWebhookEndpoint(workflowId.value, selectedEndpointId.value.trim(), {
      active: parseBoolean(selectedEndpointActive.value),
    });
    successMessage.value = "Endpoint updated.";
  } catch (error) {
    errorMessage.value = mapWebhookError(error, "Unable to update endpoint.");
  } finally {
    isMutating.value = false;
  }
}

async function rotateEndpointSecret(): Promise<void> {
  if (!selectedEndpointId.value.trim()) {
    errorMessage.value = "endpoint_id is required to rotate secret.";
    return;
  }
  errorMessage.value = null;
  successMessage.value = null;
  isMutating.value = true;
  try {
    const rotated = await service.rotateWebhookEndpointSecret(
      workflowId.value,
      selectedEndpointId.value.trim(),
      { reason: rotateReason.value.trim() || "scheduled_rotation" },
    );
    successMessage.value = `Secret rotated: ${rotated.secret_ref}`;
  } catch (error) {
    errorMessage.value = mapWebhookError(error, "Unable to rotate endpoint secret.");
  } finally {
    isMutating.value = false;
  }
}

async function replayEvent(eventId: string): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  const commandId = crypto.randomUUID();
  try {
    await service.replayWebhookEvent(workflowId.value, eventId, {
      command_id: commandId,
      reason: "manual_replay_from_admin_ui",
    });
    store.setReplayCooldown(eventId, Date.now() + 60_000);
    successMessage.value = `Replay command queued (${commandId}).`;
  } catch (error) {
    errorMessage.value = mapWebhookError(error, "Unable to replay webhook event.");
  }
}

async function applyFilters(): Promise<void> {
  page.value = 1;
  await loadEvents();
}

async function resetFilters(): Promise<void> {
  directionFilter.value = "";
  eventTypeFilter.value = "";
  deliveryStatusFilter.value = "";
  page.value = 1;
  await loadEvents();
}

async function previousPage(): Promise<void> {
  if (page.value <= 1) {
    return;
  }
  page.value -= 1;
  await loadEvents();
}

async function nextPage(): Promise<void> {
  if (page.value >= totalPages.value) {
    return;
  }
  page.value += 1;
  await loadEvents();
}

function parseBoolean(raw: string): boolean | undefined {
  const normalized = raw.trim().toLowerCase();
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

function normalizeTimeout(raw: string): number {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    return 5000;
  }
  return Math.max(1000, Math.min(30000, Math.trunc(parsed)));
}

function replayDisabled(eventId: string): boolean {
  return store.replayCooldownRemainingMs(eventId) > 0 || isMutating.value;
}

function replayLabel(eventId: string): string {
  const remaining = store.replayCooldownRemainingMs(eventId);
  if (remaining <= 0) {
    return "Replay";
  }
  return `Cooldown ${Math.ceil(remaining / 1000)}s`;
}

function mapWebhookError(error: unknown, fallback: string): string {
  if (!(error instanceof WorkflowsAdminApiError)) {
    return fallback;
  }
  if (error.code === "REPLAY_COOLDOWN_ACTIVE") {
    return "Replay cooldown is active for this event.";
  }
  if (error.code === "REPLAY_RATE_LIMIT_EXCEEDED") {
    return "Replay rate limit exceeded. Wait and retry.";
  }
  if (error.code === "INVALID_QUERY_PARAMS") {
    return "Invalid webhook query filters.";
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

