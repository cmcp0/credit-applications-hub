import {
  upsertWorkflowGraph,
  type WorkflowsAdminApiError,
} from "@/features/admin_workflows/api/workflows_admin_api";
import type {
  UpsertWorkflowGraphResponse,
  WorkflowGraphOperation,
} from "@/features/admin_workflows/model/admin_workflow_types";

export type { WorkflowsAdminApiError };

export interface WorkflowGraphAdminService {
  upsertWorkflowGraph(
    workflowId: string,
    input: {
      expected_version?: number;
      operations: WorkflowGraphOperation[];
      deleted_operation_ids: string[];
      deleted_sub_operation_ids: string[];
      deleted_trigger_ids: string[];
    },
    options?: { ifMatch?: string },
  ): Promise<UpsertWorkflowGraphResponse>;
}

export function createWorkflowGraphAdminService(): WorkflowGraphAdminService {
  return {
    upsertWorkflowGraph,
  };
}

