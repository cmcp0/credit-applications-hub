export type WorkflowVersionStatus = "DRAFT" | "PUBLISHED" | "RETIRED";
export type SubOperationExecutionType =
  | "QUERY_USE_CASE"
  | "COMMAND_USE_CASE"
  | "THIRD_PARTY_HTTP_REQUEST";
export type SubOperationTriggerType =
  | "TRIGGER_EVENT"
  | "TRIGGER_COMMAND"
  | "TRIGGER_WEBHOOK_EGRESS";
export type WebhookDirection = "INGRESS" | "EGRESS";
export type WebhookDeliveryStatus =
  | "RECEIVED"
  | "QUEUED"
  | "DELIVERED"
  | "FAILED"
  | "DEAD_LETTERED";
export type WorkflowExecutionStatus =
  | "PENDING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "DEAD_LETTERED";

export interface ApiErrorResponse {
  code: string;
  message: string;
}

export interface OperationUserSummary {
  user_id: string;
  email: string;
  is_active: boolean;
  has_operation_role: boolean;
  updated_at: string;
}

export interface OperationUsersListResponse {
  items: OperationUserSummary[];
  page: number;
  page_size: number;
  total: number;
}

export interface WorkflowSummary {
  id: string;
  country: string;
  version: number;
  version_status: WorkflowVersionStatus;
  active: boolean;
  published_at?: string | null;
}

export interface WorkflowsListResponse {
  items: WorkflowSummary[];
}

export interface CreateWorkflowResponse {
  id: string;
  country: string;
  version: number;
  version_status: WorkflowVersionStatus;
}

export interface PublishWorkflowResponse {
  workflow_id: string;
  country: string;
  version: number;
  version_status: WorkflowVersionStatus;
  active: boolean;
  published_at: string;
}

export interface WorkflowGraphTrigger {
  id?: string;
  trigger_type: SubOperationTriggerType;
  trigger_name: string;
  payload_template: Record<string, unknown>;
  condition_expr?: string | null;
}

export interface WorkflowGraphSubOperation {
  id?: string;
  sort_order: number;
  execution_type: SubOperationExecutionType;
  target_ref: string;
  input_template: Record<string, unknown>;
  output_alias?: string | null;
  active: boolean;
  triggers: WorkflowGraphTrigger[];
}

export interface WorkflowGraphOperation {
  id?: string;
  name: string;
  sort_order: number;
  active: boolean;
  sub_operations: WorkflowGraphSubOperation[];
}

export interface WorkflowGraphCounts {
  operations: number;
  sub_operations: number;
  triggers: number;
}

export interface UpsertWorkflowGraphResponse {
  workflow_id: string;
  version: number;
  graph_revision: number;
  etag: string;
  counts: WorkflowGraphCounts;
  updated_at: string;
}

export interface CreateWebhookEndpointResponse {
  endpoint_id: string;
  direction: WebhookDirection;
  active: boolean;
}

export interface UpdateWebhookEndpointResponse {
  endpoint_id: string;
  workflow_id: string;
  active: boolean;
  updated_at: string;
}

export interface RotateWebhookEndpointSecretResponse {
  endpoint_id: string;
  secret_ref: string;
  rotated_at: string;
}

export interface ReplayWebhookEventResponse {
  queued: boolean;
  command_id: string;
}

export interface WebhookEventLastAttempt {
  attempt_no: number;
  delivery_status: WebhookDeliveryStatus;
  response_code?: number | null;
  error_code?: string | null;
  error_message?: string | null;
  next_retry_at?: string | null;
  created_at: string;
}

export interface WorkflowWebhookEventSummary {
  id: string;
  endpoint_id: string;
  provider_code: string;
  direction: WebhookDirection;
  event_type: string;
  application_id?: string | null;
  payload_hash: string;
  signature_valid?: boolean | null;
  delivery_status: WebhookDeliveryStatus;
  correlation_id: string;
  occurred_at: string;
  created_at: string;
  last_attempt?: WebhookEventLastAttempt | null;
}

export interface WorkflowWebhookEventListResponse {
  items: WorkflowWebhookEventSummary[];
  page: number;
  page_size: number;
  total: number;
  sort_by: "occurred_at" | "created_at";
  sort_dir: "asc" | "desc";
}

export interface WorkflowExecutionOperationSummary {
  id: string;
  name: string;
  sort_order: number;
}

export interface WorkflowExecutionSubOperationSummary {
  id: string;
  execution_type: SubOperationExecutionType;
  target_ref: string;
}

export interface WorkflowExecutionSummary {
  job_id: string;
  workflow_id: string;
  workflow_revision: number;
  application_id?: string | null;
  operation?: WorkflowExecutionOperationSummary | null;
  sub_operation?: WorkflowExecutionSubOperationSummary | null;
  status: WorkflowExecutionStatus;
  attempts: number;
  max_attempts: number;
  available_at?: string | null;
  locked_at?: string | null;
  completed_at?: string | null;
  last_error_code?: string | null;
  last_error_message?: string | null;
  correlation_id: string;
  payload_summary: Record<string, unknown>;
  updated_at: string;
  created_at: string;
}

export interface WorkflowExecutionListResponse {
  items: WorkflowExecutionSummary[];
  page: number;
  page_size: number;
  total: number;
  sort_by: "updated_at" | "available_at" | "created_at";
  sort_dir: "asc" | "desc";
}

export type AdminWorkflowRoutePath =
  | "/dashboard/admin/operation-users"
  | "/dashboard/admin/workflows"
  | "/dashboard/admin/workflows/:workflowId/editor"
  | "/dashboard/admin/workflows/:workflowId/webhooks"
  | "/dashboard/admin/workflows/:workflowId/executions";

export interface AdminWorkflowRouteContext {
  workflowId: string;
}

