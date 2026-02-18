<template>
  <DashboardShell
    role-label="Admin"
    title="Workflow Administration"
    description="Create, publish, and navigate workflow governance artifacts."
  >
    <section class="grid gap-4">
      <Alert v-if="errorMessage" variant="destructive">{{ errorMessage }}</Alert>
      <Alert v-if="successMessage">{{ successMessage }}</Alert>

      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Create Draft Workflow</CardTitle>
          <CardDescription>
            Creates a draft version with default MVP statuses and transitions.
          </CardDescription>
        </CardHeader>
        <CardContent class="grid gap-3 sm:grid-cols-[120px_120px_auto]">
          <Input v-model="createCountry" maxlength="2" placeholder="MX" />
          <Input v-model="createVersion" type="number" min="1" placeholder="1" />
          <Button :disabled="isCreating" @click="createDraftWorkflow">
            {{ isCreating ? "Creating..." : "Create Draft" }}
          </Button>
        </CardContent>
      </Card>

      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Workflow Catalog</CardTitle>
          <CardDescription>Filter and publish workflow versions.</CardDescription>
        </CardHeader>
        <CardContent class="grid gap-4">
          <div class="grid gap-3 sm:grid-cols-[120px_120px_160px_auto_auto]">
            <Input v-model="countryFilter" maxlength="2" placeholder="Country" />
            <Input v-model="activeFilter" placeholder="active true|false" />
            <Input v-model="versionStatusFilter" placeholder="DRAFT|PUBLISHED" />
            <Button variant="secondary" :disabled="isLoading" @click="loadWorkflows">Apply</Button>
            <Button variant="ghost" :disabled="isLoading" @click="loadWorkflows">Refresh</Button>
          </div>

          <p v-if="isLoading" class="text-sm text-muted-foreground">Loading workflows...</p>
          <div v-else-if="workflows.length === 0" class="text-sm text-muted-foreground">
            No workflows found for the selected filters.
          </div>

          <div v-else class="overflow-auto">
            <table class="w-full min-w-[1020px] text-left text-sm">
              <thead>
                <tr class="border-b border-border text-xs uppercase tracking-[0.08em] text-muted-foreground">
                  <th class="py-2 pr-3">Workflow ID</th>
                  <th class="py-2 pr-3">Country</th>
                  <th class="py-2 pr-3">Version</th>
                  <th class="py-2 pr-3">Status</th>
                  <th class="py-2 pr-3">Active</th>
                  <th class="py-2 pr-3">Published At</th>
                  <th class="py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="workflow in workflows" :key="workflow.id" class="border-b border-border/60">
                  <td class="py-3 pr-3 font-mono text-xs">{{ workflow.id }}</td>
                  <td class="py-3 pr-3">{{ workflow.country }}</td>
                  <td class="py-3 pr-3">{{ workflow.version }}</td>
                  <td class="py-3 pr-3">{{ workflow.version_status }}</td>
                  <td class="py-3 pr-3">{{ workflow.active ? "Yes" : "No" }}</td>
                  <td class="py-3 pr-3">
                    {{ workflow.published_at ? formatDate(workflow.published_at) : "-" }}
                  </td>
                  <td class="py-3 text-right">
                    <div class="inline-flex flex-wrap justify-end gap-2">
                      <Button
                        size="sm"
                        :disabled="workflow.version_status !== 'DRAFT' || isPublishingById[workflow.id]"
                        @click="publishDraft(workflow.id, workflow.version)"
                      >
                        {{ isPublishingById[workflow.id] ? "Publishing..." : "Publish" }}
                      </Button>
                      <RouterLink :to="`/dashboard/admin/workflows/${workflow.id}/editor`">
                        <Button size="sm" variant="secondary">Editor</Button>
                      </RouterLink>
                      <RouterLink :to="`/dashboard/admin/workflows/${workflow.id}/webhooks`">
                        <Button size="sm" variant="secondary">Webhooks</Button>
                      </RouterLink>
                      <RouterLink :to="`/dashboard/admin/workflows/${workflow.id}/executions`">
                        <Button size="sm" variant="secondary">Executions</Button>
                      </RouterLink>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
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
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { WorkflowsAdminApiError } from "@/features/admin_workflows/api/workflows_admin_api";
import type { WorkflowSummary } from "@/features/admin_workflows/model/admin_workflow_types";
import { createWorkflowCatalogAdminService } from "@/features/admin_workflows/services/workflow_catalog_admin_service";
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";

const service = createWorkflowCatalogAdminService();

const workflows = ref<WorkflowSummary[]>([]);
const isLoading = ref(false);
const isCreating = ref(false);
const isPublishingById = reactive<Record<string, boolean>>({});
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);
const countryFilter = ref("");
const activeFilter = ref("");
const versionStatusFilter = ref("");
const createCountry = ref("MX");
const createVersion = ref("1");

onMounted(async () => {
  await loadWorkflows();
});

async function loadWorkflows(): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  isLoading.value = true;
  try {
    const result = await service.listWorkflows({
      country: countryFilter.value || undefined,
      active: parseBoolean(activeFilter.value),
      version_status: versionStatusFilter.value || undefined,
    });
    workflows.value = result.items;
  } catch (error) {
    errorMessage.value = mapWorkflowsError(error, "Unable to load workflows.");
  } finally {
    isLoading.value = false;
  }
}

async function createDraftWorkflow(): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  isCreating.value = true;
  try {
    const version = Number(createVersion.value);
    const created = await service.createWorkflow({
      country: createCountry.value.trim().toUpperCase(),
      version: Number.isFinite(version) ? Math.max(1, Math.trunc(version)) : 1,
      statuses: [
        {
          code: "PENDING_REVIEW",
          label: "Pending review",
          is_initial: true,
          is_terminal: false,
          sort_order: 1,
        },
        {
          code: "APPROVED",
          label: "Approved",
          is_initial: false,
          is_terminal: true,
          sort_order: 2,
        },
        {
          code: "REJECTED",
          label: "Rejected",
          is_initial: false,
          is_terminal: true,
          sort_order: 3,
        },
      ],
      transitions: [
        { from: "PENDING_REVIEW", to: "APPROVED" },
        { from: "PENDING_REVIEW", to: "REJECTED" },
      ],
    });
    successMessage.value = `Draft workflow ${created.id} created.`;
    await loadWorkflows();
  } catch (error) {
    errorMessage.value = mapWorkflowsError(error, "Unable to create workflow draft.");
  } finally {
    isCreating.value = false;
  }
}

async function publishDraft(workflowId: string, version: number): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  isPublishingById[workflowId] = true;
  try {
    const published = await service.publishWorkflow(workflowId, { expected_version: version });
    successMessage.value = `Workflow ${published.workflow_id} published.`;
    await loadWorkflows();
  } catch (error) {
    errorMessage.value = mapWorkflowsError(error, "Unable to publish workflow.");
  } finally {
    isPublishingById[workflowId] = false;
  }
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

function mapWorkflowsError(error: unknown, fallback: string): string {
  if (!(error instanceof WorkflowsAdminApiError)) {
    return fallback;
  }
  if (error.code === "VERSION_CONFLICT") {
    return "Version conflict detected. Reload the catalog and retry.";
  }
  if (error.code === "WORKFLOW_VALIDATION_FAILED") {
    return "Workflow definition failed validation. Review statuses and transitions.";
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

