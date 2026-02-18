import {
  listWorkflowExecutions,
  type ListWorkflowExecutionsParams,
} from "@/features/admin_workflows/api/workflows_admin_api";
import type { WorkflowExecutionListResponse } from "@/features/admin_workflows/model/admin_workflow_types";

export interface ExecutionAdminService {
  listWorkflowExecutions(
    workflowId: string,
    params?: ListWorkflowExecutionsParams,
  ): Promise<WorkflowExecutionListResponse>;
}

export function createExecutionAdminService(): ExecutionAdminService {
  return {
    listWorkflowExecutions,
  };
}

