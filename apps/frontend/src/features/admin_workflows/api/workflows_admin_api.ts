import type {
  ApiErrorResponse,
  CreateWebhookEndpointResponse,
  CreateWorkflowResponse,
  PublishWorkflowResponse,
  ReplayWebhookEventResponse,
  RotateWebhookEndpointSecretResponse,
  UpdateWebhookEndpointResponse,
  UpsertWorkflowGraphResponse,
  WorkflowExecutionListResponse,
  WorkflowGraphOperation,
  WorkflowWebhookEventListResponse,
  WorkflowsListResponse,
} from "@/features/admin_workflows/model/admin_workflow_types";

const DEFAULT_ERROR_MESSAGE = "Unable to complete workflow admin request";

export class WorkflowsAdminApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "WorkflowsAdminApiError";
    this.status = status;
    this.code = code;
  }
}

export interface ListWorkflowsParams {
  country?: string;
  active?: boolean;
  version_status?: string;
}

export interface ListWorkflowWebhookEventsParams {
  direction?: string;
  event_type?: string;
  delivery_status?: string;
  application_id?: string;
  correlation_id?: string;
  sort_by?: "occurred_at" | "created_at";
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface ListWorkflowExecutionsParams {
  status?: string;
  application_id?: string;
  operation_id?: string;
  sub_operation_id?: string;
  from?: string;
  to?: string;
  correlation_id?: string;
  sort_by?: "updated_at" | "available_at" | "created_at";
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export async function listWorkflows(
  params: ListWorkflowsParams = {},
): Promise<WorkflowsListResponse> {
  const query = new URLSearchParams();
  if (params.country) {
    query.set("country", params.country.trim().toUpperCase());
  }
  if (typeof params.active === "boolean") {
    query.set("active", String(params.active));
  }
  if (params.version_status) {
    query.set("version_status", params.version_status.trim().toUpperCase());
  }

  const path =
    query.size > 0 ? `/api/workflows?${query.toString()}` : "/api/workflows";
  const response = await fetch(resolveUrl(path));
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as WorkflowsListResponse;
}

export async function createWorkflow(input: {
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
}): Promise<CreateWorkflowResponse> {
  const response = await fetch(resolveUrl("/api/workflows"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as CreateWorkflowResponse;
}

export async function publishWorkflow(
  workflowId: string,
  input: { expected_version: number },
): Promise<PublishWorkflowResponse> {
  const response = await fetch(
    resolveUrl(`/api/workflows/${encodeURIComponent(workflowId)}/publish`),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as PublishWorkflowResponse;
}

export async function upsertWorkflowGraph(
  workflowId: string,
  input: {
    expected_version?: number;
    operations: WorkflowGraphOperation[];
    deleted_operation_ids: string[];
    deleted_sub_operation_ids: string[];
    deleted_trigger_ids: string[];
  },
  options: { ifMatch?: string } = {},
): Promise<UpsertWorkflowGraphResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options.ifMatch) {
    headers["If-Match"] = options.ifMatch;
  }

  const response = await fetch(
    resolveUrl(`/api/workflows/${encodeURIComponent(workflowId)}/graph`),
    {
      method: "PUT",
      headers,
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as UpsertWorkflowGraphResponse;
}

export async function createWebhookEndpoint(
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
): Promise<CreateWebhookEndpointResponse> {
  const response = await fetch(
    resolveUrl(`/api/workflows/${encodeURIComponent(workflowId)}/webhooks/endpoints`),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as CreateWebhookEndpointResponse;
}

export async function updateWebhookEndpoint(
  workflowId: string,
  endpointId: string,
  input: {
    active?: boolean;
    method?: string;
    url?: string;
    timeout_ms?: number;
  },
): Promise<UpdateWebhookEndpointResponse> {
  const response = await fetch(
    resolveUrl(
      `/api/workflows/${encodeURIComponent(workflowId)}/webhooks/endpoints/${encodeURIComponent(endpointId)}`,
    ),
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as UpdateWebhookEndpointResponse;
}

export async function rotateWebhookEndpointSecret(
  workflowId: string,
  endpointId: string,
  input: { reason: string },
): Promise<RotateWebhookEndpointSecretResponse> {
  const response = await fetch(
    resolveUrl(
      `/api/workflows/${encodeURIComponent(workflowId)}/webhooks/endpoints/${encodeURIComponent(endpointId)}/rotate-secret`,
    ),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as RotateWebhookEndpointSecretResponse;
}

export async function listWebhookEvents(
  workflowId: string,
  params: ListWorkflowWebhookEventsParams = {},
): Promise<WorkflowWebhookEventListResponse> {
  const query = new URLSearchParams();
  if (params.direction) {
    query.set("direction", params.direction.trim().toUpperCase());
  }
  if (params.event_type) {
    query.set("event_type", params.event_type.trim());
  }
  if (params.delivery_status) {
    query.set("delivery_status", params.delivery_status.trim().toUpperCase());
  }
  if (params.application_id) {
    query.set("application_id", params.application_id.trim());
  }
  if (params.correlation_id) {
    query.set("correlation_id", params.correlation_id.trim());
  }
  if (params.sort_by) {
    query.set("sort_by", params.sort_by);
  }
  if (params.sort_dir) {
    query.set("sort_dir", params.sort_dir);
  }
  if (typeof params.page === "number") {
    query.set("page", String(params.page));
  }
  if (typeof params.page_size === "number") {
    query.set("page_size", String(params.page_size));
  }

  const path = `/api/workflows/${encodeURIComponent(workflowId)}/webhooks/events${
    query.size > 0 ? `?${query.toString()}` : ""
  }`;
  const response = await fetch(resolveUrl(path));
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as WorkflowWebhookEventListResponse;
}

export async function replayWebhookEvent(
  workflowId: string,
  webhookEventId: string,
  input: { command_id: string; reason: string },
): Promise<ReplayWebhookEventResponse> {
  const response = await fetch(
    resolveUrl(
      `/api/workflows/${encodeURIComponent(workflowId)}/webhooks/events/${encodeURIComponent(webhookEventId)}/replay`,
    ),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as ReplayWebhookEventResponse;
}

export async function listWorkflowExecutions(
  workflowId: string,
  params: ListWorkflowExecutionsParams = {},
): Promise<WorkflowExecutionListResponse> {
  const query = new URLSearchParams();
  if (params.status) {
    query.set("status", params.status.trim().toUpperCase());
  }
  if (params.application_id) {
    query.set("application_id", params.application_id.trim());
  }
  if (params.operation_id) {
    query.set("operation_id", params.operation_id.trim());
  }
  if (params.sub_operation_id) {
    query.set("sub_operation_id", params.sub_operation_id.trim());
  }
  if (params.from) {
    query.set("from", params.from.trim());
  }
  if (params.to) {
    query.set("to", params.to.trim());
  }
  if (params.correlation_id) {
    query.set("correlation_id", params.correlation_id.trim());
  }
  if (params.sort_by) {
    query.set("sort_by", params.sort_by);
  }
  if (params.sort_dir) {
    query.set("sort_dir", params.sort_dir);
  }
  if (typeof params.page === "number") {
    query.set("page", String(params.page));
  }
  if (typeof params.page_size === "number") {
    query.set("page_size", String(params.page_size));
  }

  const path = `/api/workflows/${encodeURIComponent(workflowId)}/executions${
    query.size > 0 ? `?${query.toString()}` : ""
  }`;
  const response = await fetch(resolveUrl(path));
  if (!response.ok) {
    throw await buildWorkflowsAdminApiError(response);
  }
  return (await response.json()) as WorkflowExecutionListResponse;
}

async function buildWorkflowsAdminApiError(
  response: Response,
): Promise<WorkflowsAdminApiError> {
  const defaultError = new WorkflowsAdminApiError(
    response.status,
    "UNKNOWN_ERROR",
    DEFAULT_ERROR_MESSAGE,
  );

  try {
    const payload = (await response.clone().json()) as Partial<ApiErrorResponse>;
    const code =
      typeof payload.code === "string" && payload.code.length > 0
        ? payload.code
        : "UNKNOWN_ERROR";
    const message =
      typeof payload.message === "string" && payload.message.length > 0
        ? payload.message
        : DEFAULT_ERROR_MESSAGE;
    return new WorkflowsAdminApiError(response.status, code, message);
  } catch {
    return defaultError;
  }
}

function resolveUrl(path: string): string {
  const base = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
  if (!base) {
    return path;
  }

  return new URL(path, base).toString();
}

