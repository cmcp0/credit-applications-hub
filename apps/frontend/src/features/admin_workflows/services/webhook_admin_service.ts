import {
  createWebhookEndpoint,
  listWebhookEvents,
  replayWebhookEvent,
  rotateWebhookEndpointSecret,
  updateWebhookEndpoint,
  type ListWorkflowWebhookEventsParams,
} from "@/features/admin_workflows/api/workflows_admin_api";
import type {
  CreateWebhookEndpointResponse,
  ReplayWebhookEventResponse,
  RotateWebhookEndpointSecretResponse,
  UpdateWebhookEndpointResponse,
  WorkflowWebhookEventListResponse,
} from "@/features/admin_workflows/model/admin_workflow_types";

export interface WebhookAdminService {
  createWebhookEndpoint(
    workflowId: string,
    input: {
      direction: string;
      provider_code: string;
      event_type: string;
      method: string;
      url: string;
      secret_ref: string;
      timeout_ms?: number;
      active?: boolean;
    },
  ): Promise<CreateWebhookEndpointResponse>;
  updateWebhookEndpoint(
    workflowId: string,
    endpointId: string,
    input: {
      active?: boolean;
      method?: string;
      url?: string;
      timeout_ms?: number;
    },
  ): Promise<UpdateWebhookEndpointResponse>;
  rotateWebhookEndpointSecret(
    workflowId: string,
    endpointId: string,
    input: { reason: string },
  ): Promise<RotateWebhookEndpointSecretResponse>;
  listWebhookEvents(
    workflowId: string,
    params?: ListWorkflowWebhookEventsParams,
  ): Promise<WorkflowWebhookEventListResponse>;
  replayWebhookEvent(
    workflowId: string,
    webhookEventId: string,
    input: { command_id: string; reason: string },
  ): Promise<ReplayWebhookEventResponse>;
}

export function createWebhookAdminService(): WebhookAdminService {
  return {
    createWebhookEndpoint,
    updateWebhookEndpoint,
    rotateWebhookEndpointSecret,
    listWebhookEvents,
    replayWebhookEvent,
  };
}

