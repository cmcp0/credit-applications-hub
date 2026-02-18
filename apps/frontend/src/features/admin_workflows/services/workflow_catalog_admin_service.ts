import {
  createWorkflow,
  listWorkflows,
  publishWorkflow,
  type ListWorkflowsParams,
} from "@/features/admin_workflows/api/workflows_admin_api";
import type {
  CreateWorkflowResponse,
  PublishWorkflowResponse,
  WorkflowsListResponse,
} from "@/features/admin_workflows/model/admin_workflow_types";

export interface WorkflowCatalogAdminService {
  listWorkflows(params?: ListWorkflowsParams): Promise<WorkflowsListResponse>;
  createWorkflow(input: {
    country: string;
    version: number;
    statuses: Array<{
      code: string;
      label: string;
      is_initial: boolean;
      is_terminal: boolean;
      sort_order: number;
    }>;
    transitions: Array<{ from: string; to: string }>;
  }): Promise<CreateWorkflowResponse>;
  publishWorkflow(
    workflowId: string,
    input: { expected_version: number },
  ): Promise<PublishWorkflowResponse>;
}

export function createWorkflowCatalogAdminService(): WorkflowCatalogAdminService {
  return {
    listWorkflows,
    createWorkflow,
    publishWorkflow,
  };
}
