<template>
  <DashboardShell
    role-label="Admin"
    title="Workflow Graph Editor"
    description="Save operation graph revisions with optimistic concurrency controls."
  >
    <section class="grid gap-4">
      <Alert v-if="errorMessage" variant="destructive">{{ errorMessage }}</Alert>
      <Alert v-if="successMessage">{{ successMessage }}</Alert>

      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Editor Context</CardTitle>
          <CardDescription>
            Workflow id: <code>{{ workflowId }}</code>
          </CardDescription>
        </CardHeader>
        <CardContent class="grid gap-3 sm:grid-cols-[180px_1fr]">
          <label class="space-y-2 text-sm">
            <span class="font-medium">Expected Version</span>
            <Input v-model="expectedVersionInput" type="number" min="1" />
          </label>
          <label class="space-y-2 text-sm">
            <span class="font-medium">If-Match ETag (optional)</span>
            <Input v-model="ifMatchEtag" placeholder='W/"workflow:...:v#:r#"' />
          </label>
        </CardContent>
      </Card>

      <Card custom-class="border-border/80">
        <CardHeader>
          <CardTitle>Operations JSON</CardTitle>
          <CardDescription>
            Provide an array of operations with sub-operations and triggers.
          </CardDescription>
        </CardHeader>
        <CardContent class="grid gap-3">
          <textarea
            v-model="operationsJson"
            class="min-h-[320px] rounded-md border border-input bg-background p-3 font-mono text-xs"
          />
          <div class="inline-flex gap-2">
            <Button variant="secondary" @click="loadTemplate">Load Template</Button>
            <Button :disabled="isSaving" @click="saveGraph">
              {{ isSaving ? "Saving..." : "Save Graph" }}
            </Button>
          </div>
          <div class="text-xs text-muted-foreground">
            <p><span class="font-medium">Current ETag:</span> {{ currentEtag || "-" }}</p>
            <p><span class="font-medium">Graph Revision:</span> {{ graphRevision ?? "-" }}</p>
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
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { WorkflowsAdminApiError } from "@/features/admin_workflows/api/workflows_admin_api";
import type {
  SubOperationExecutionType,
  SubOperationTriggerType,
  WorkflowGraphOperation,
} from "@/features/admin_workflows/model/admin_workflow_types";
import { createWorkflowCatalogAdminService } from "@/features/admin_workflows/services/workflow_catalog_admin_service";
import { createWorkflowGraphAdminService } from "@/features/admin_workflows/services/workflow_graph_admin_service";
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";

const route = useRoute();
const workflowId = computed(() => String(route.params.workflowId ?? ""));
const workflowCatalogService = createWorkflowCatalogAdminService();
const workflowGraphService = createWorkflowGraphAdminService();

const expectedVersionInput = ref("1");
const ifMatchEtag = ref("");
const currentEtag = ref<string | null>(null);
const graphRevision = ref<number | null>(null);
const operationsJson = ref("[]");
const isSaving = ref(false);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

const allowedExecutionTypes = new Set<SubOperationExecutionType>([
  "QUERY_USE_CASE",
  "COMMAND_USE_CASE",
  "THIRD_PARTY_HTTP_REQUEST",
]);
const allowedTriggerTypes = new Set<SubOperationTriggerType>([
  "TRIGGER_EVENT",
  "TRIGGER_COMMAND",
  "TRIGGER_WEBHOOK_EGRESS",
]);

onMounted(async () => {
  loadTemplate();
  await loadWorkflowVersion();
});

async function loadWorkflowVersion(): Promise<void> {
  try {
    const result = await workflowCatalogService.listWorkflows();
    const selected = result.items.find((item) => item.id === workflowId.value);
    if (selected) {
      expectedVersionInput.value = String(selected.version);
    }
  } catch {
    // Keep editor usable even if catalog prefetch fails.
  }
}

function loadTemplate(): void {
  operationsJson.value = JSON.stringify(
    [
      {
        name: "provider_enrichment",
        sort_order: 1,
        active: true,
        sub_operations: [
          {
            sort_order: 1,
            execution_type: "THIRD_PARTY_HTTP_REQUEST",
            target_ref: "webhook_endpoint:replace-with-endpoint-id",
            input_template: {
              application_id: "{{ application.id }}",
              country: "{{ application.country }}",
            },
            output_alias: "provider_response",
            active: true,
            triggers: [
              {
                trigger_type: "TRIGGER_EVENT",
                trigger_name: "credit.workflow.execution.completed",
                payload_template: {
                  application_id: "{{ application.id }}",
                },
              },
            ],
          },
        ],
      },
    ],
    null,
    2,
  );
}

async function saveGraph(): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;
  isSaving.value = true;

  try {
    const operations = parseOperationsJson(operationsJson.value);
    validateGraph(operations);
    const expectedVersion = normalizeVersion(expectedVersionInput.value);

    const result = await workflowGraphService.upsertWorkflowGraph(
      workflowId.value,
      {
        expected_version: expectedVersion,
        operations,
        deleted_operation_ids: [],
        deleted_sub_operation_ids: [],
        deleted_trigger_ids: [],
      },
      { ifMatch: ifMatchEtag.value.trim() || undefined },
    );

    currentEtag.value = result.etag;
    graphRevision.value = result.graph_revision;
    ifMatchEtag.value = result.etag;
    successMessage.value = "Workflow graph saved.";
  } catch (error) {
    errorMessage.value = mapEditorError(error);
  } finally {
    isSaving.value = false;
  }
}

function parseOperationsJson(raw: string): WorkflowGraphOperation[] {
  const parsed = JSON.parse(raw) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error("operations payload must be a JSON array");
  }
  return parsed as WorkflowGraphOperation[];
}

function validateGraph(operations: WorkflowGraphOperation[]): void {
  assertContiguousSortOrder(
    operations.map((operation) => Number(operation.sort_order)),
    "operations.sort_order",
  );

  for (const operation of operations) {
    if (!operation.name || operation.name.trim().length === 0) {
      throw new Error("operation name is required");
    }
    assertContiguousSortOrder(
      operation.sub_operations.map((subOperation) => Number(subOperation.sort_order)),
      "sub_operations.sort_order",
    );
    for (const subOperation of operation.sub_operations) {
      if (!allowedExecutionTypes.has(subOperation.execution_type)) {
        throw new Error(`invalid execution_type: ${subOperation.execution_type}`);
      }
      if (
        subOperation.execution_type === "THIRD_PARTY_HTTP_REQUEST" &&
        !subOperation.target_ref?.trim()
      ) {
        throw new Error("target_ref is required for THIRD_PARTY_HTTP_REQUEST");
      }
      for (const trigger of subOperation.triggers) {
        if (!allowedTriggerTypes.has(trigger.trigger_type)) {
          throw new Error(`invalid trigger_type: ${trigger.trigger_type}`);
        }
        if (!trigger.trigger_name?.trim()) {
          throw new Error("trigger_name is required");
        }
      }
    }
  }
}

function assertContiguousSortOrder(values: number[], label: string): void {
  if (values.length === 0) {
    return;
  }
  const sorted = [...values].sort((a, b) => a - b);
  for (let index = 0; index < sorted.length; index += 1) {
    if (sorted[index] !== index + 1) {
      throw new Error(`${label} must be contiguous and unique`);
    }
  }
}

function normalizeVersion(raw: string): number {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    return 1;
  }
  return Math.max(1, Math.trunc(parsed));
}

function mapEditorError(error: unknown): string {
  if (error instanceof SyntaxError) {
    return "Invalid JSON. Please fix the operations payload and retry.";
  }
  if (error instanceof Error && !(error instanceof WorkflowsAdminApiError)) {
    return error.message;
  }
  if (error instanceof WorkflowsAdminApiError) {
    if (error.code === "PRECONDITION_REQUIRED") {
      return "Missing concurrency precondition. Provide expected version or If-Match ETag.";
    }
    if (error.code === "ETAG_MISMATCH" || error.code === "VERSION_CONFLICT") {
      return "Your editor is stale. Reload the latest workflow and retry.";
    }
    if (error.code === "GRAPH_VALIDATION_ERROR") {
      return "Server-side graph validation failed. Review fields and retry.";
    }
    if (error.code === "WORKFLOW_NOT_DRAFT") {
      return "Published workflow versions are immutable. Edit a draft version instead.";
    }
    return error.message || "Unable to save workflow graph.";
  }
  return "Unable to save workflow graph.";
}
</script>

