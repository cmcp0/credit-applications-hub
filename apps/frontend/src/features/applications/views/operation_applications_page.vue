<template>
  <DashboardShell
    role-label="Operation"
    title="Operations Applications Queue"
    description="Review applications and execute status transitions."
  >
    <section class="grid gap-5">
      <Alert v-if="!isAllowed" variant="destructive">
        You do not have access to operation applications services.
      </Alert>

      <template v-else>
        <Card custom-class="border-border/80">
          <CardHeader>
            <CardTitle>Filters</CardTitle>
            <CardDescription>Filter queue by country and status.</CardDescription>
          </CardHeader>
          <CardContent class="grid gap-4">
            <div class="grid gap-3 sm:grid-cols-3">
              <label class="space-y-2 text-sm font-medium">
                <span>Country</span>
                <Input v-model="countryFilter" maxlength="2" placeholder="MX" />
              </label>
              <label class="space-y-2 text-sm font-medium">
                <span>Status</span>
                <Input v-model="statusFilter" maxlength="120" placeholder="PENDING_REVIEW" />
              </label>
              <label class="space-y-2 text-sm font-medium">
                <span>Page Size</span>
                <Input v-model="pageSize" inputmode="numeric" type="number" min="1" max="100" />
              </label>
            </div>
            <div class="inline-flex gap-2">
              <Button size="sm" @click="applyFilters">Apply</Button>
              <Button size="sm" variant="secondary" @click="resetFilters">Reset</Button>
            </div>
          </CardContent>
        </Card>

        <Alert v-if="store.isRealtimeDegraded">
          Realtime channel unavailable. Polling every 5 seconds to keep queue data fresh.
        </Alert>

        <ApplicationsTable
          title="Applications Queue"
          description="Global operational queue with status transition actions."
          :items="store.items"
          :is-loading="store.isListLoading"
          :page="store.page"
          :page-size="store.pageSize"
          :total="store.total"
          :show-status-action="canUpdateStatus"
          empty-message="No applications in queue."
          @open="openDetail"
          @prepare-status-update="prepareStatusUpdate"
          @refresh="loadList"
          @previous-page="previousPage"
          @next-page="nextPage"
        />

        <StatusTransitionDialog
          :application-id="selectedApplicationId"
          :current-status-code="detail?.status_code ?? null"
          :expected-version="detail?.version ?? null"
          :is-submitting="store.isMutating"
          :can-update-status="canUpdateStatus"
          :error-message="store.errorMessage"
          @submit="applyStatusTransition"
        />

        <Card v-if="detail" custom-class="border-border/80">
          <CardHeader>
            <CardTitle>Selected Application</CardTitle>
            <CardDescription>{{ detail.id }}</CardDescription>
          </CardHeader>
          <CardContent class="grid gap-2 text-sm">
            <p><span class="font-medium">Country:</span> {{ detail.country }}</p>
            <p><span class="font-medium">Status:</span> {{ detail.status_code }}</p>
            <p><span class="font-medium">Version:</span> {{ detail.version }}</p>
            <p>
              <span class="font-medium">Allowed transitions:</span>
              {{ detail.status_metadata.allowed_transitions.join(", ") || "-" }}
            </p>
          </CardContent>
        </Card>
      </template>
    </section>
  </DashboardShell>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import ApplicationsTable from "@/features/applications/components/applications_table.vue";
import StatusTransitionDialog from "@/features/applications/components/status_transition_dialog.vue";
import type { ApplicationsRealtimeEvent } from "@/features/applications/realtime/applications_updates_subscriber";
import { subscribeToApplicationsUpdates } from "@/features/applications/realtime/applications_updates_subscriber";
import {
  canAccessApplicationsModule,
  canUpdateApplicationStatus,
} from "@/features/applications/services/applications_permission_policy";
import { useApplicationsStore } from "@/features/applications/store/applications_store";
import { useAuthStore } from "@/features/auth/store/auth_store";
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";

const store = useApplicationsStore();
const authStore = useAuthStore();

const selectedApplicationId = ref<string | null>(null);
const detail = computed(() => store.currentDetail);
const countryFilter = ref("");
const statusFilter = ref("");
const pageSize = ref("20");
const isAllowed = computed(() => {
  const principal = authStore.principal;
  if (!principal) {
    return false;
  }
  return canAccessApplicationsModule("operation", principal.permissions);
});
const canUpdateStatus = computed(() => {
  const principal = authStore.principal;
  if (!principal) {
    return false;
  }
  return canUpdateApplicationStatus("operation", principal.permissions);
});
let realtimeSubscription: { unsubscribe(): void } | null = null;
let pollTimer: number | null = null;

onMounted(async () => {
  if (!isAllowed.value) {
    return;
  }

  await loadList();
  realtimeSubscription = subscribeToApplicationsUpdates(
    (event: ApplicationsRealtimeEvent) => {
      store.applyRealtimeSummary(event.application, event.version);
      if (selectedApplicationId.value && selectedApplicationId.value === event.application.id) {
        void store.refreshOperationDetailSilently(event.application.id);
      }
    },
    {
      onConnectionStateChange: (state) => {
        const degraded = state !== "connected";
        store.setRealtimeDegraded(degraded);
        if (degraded) {
          startFallbackPolling();
          return;
        }
        stopFallbackPolling();
      },
    },
  );
});

onUnmounted(() => {
  if (realtimeSubscription) {
    realtimeSubscription.unsubscribe();
    realtimeSubscription = null;
  }
  stopFallbackPolling();
});

async function loadList(): Promise<void> {
  const normalizedPageSize = normalizePageSize(pageSize.value);
  await store.loadOperationList({
    page: store.page,
    page_size: normalizedPageSize,
    country: countryFilter.value || undefined,
    status: statusFilter.value || undefined,
  });
}

async function applyFilters(): Promise<void> {
  store.page = 1;
  await loadList();
}

async function resetFilters(): Promise<void> {
  countryFilter.value = "";
  statusFilter.value = "";
  store.page = 1;
  await loadList();
}

async function previousPage(): Promise<void> {
  if (store.page <= 1) {
    return;
  }
  store.page -= 1;
  await loadList();
}

async function nextPage(): Promise<void> {
  const totalPages = Math.max(1, Math.ceil(store.total / store.pageSize));
  if (store.page >= totalPages) {
    return;
  }
  store.page += 1;
  await loadList();
}

async function openDetail(applicationId: string): Promise<void> {
  selectedApplicationId.value = applicationId;
  await store.loadOperationDetail(applicationId);
}

async function prepareStatusUpdate(applicationId: string): Promise<void> {
  await openDetail(applicationId);
}

async function applyStatusTransition(payload: {
  applicationId: string;
  status: string;
  reason_code?: string;
  expected_version: number;
}): Promise<void> {
  if (!canUpdateStatus.value) {
    return;
  }

  const success = await store.updateForOperation(payload.applicationId, {
    status: payload.status,
    reason_code: payload.reason_code,
    expected_version: payload.expected_version,
  });
  if (!success) {
    return;
  }

  await loadList();
}

function startFallbackPolling(): void {
  if (pollTimer !== null) {
    return;
  }
  pollTimer = window.setInterval(() => {
    if (!store.isListLoading) {
      void loadList();
    }
  }, 5_000);
}

function stopFallbackPolling(): void {
  if (pollTimer === null) {
    return;
  }
  window.clearInterval(pollTimer);
  pollTimer = null;
}

function normalizePageSize(raw: string): number {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    return 20;
  }
  return Math.min(100, Math.max(1, Math.trunc(parsed)));
}
</script>
