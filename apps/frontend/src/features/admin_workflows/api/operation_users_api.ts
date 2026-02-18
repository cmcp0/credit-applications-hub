import type {
  ApiErrorResponse,
  OperationUsersListResponse,
} from "@/features/admin_workflows/model/admin_workflow_types";

const DEFAULT_ERROR_MESSAGE = "Unable to complete operation-user admin request";

export class OperationUsersApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "OperationUsersApiError";
    this.status = status;
    this.code = code;
  }
}

export interface ListOperationUsersParams {
  active?: boolean;
  page?: number;
  page_size?: number;
}

export async function listOperationUsers(
  params: ListOperationUsersParams = {},
): Promise<OperationUsersListResponse> {
  const query = new URLSearchParams();
  if (typeof params.active === "boolean") {
    query.set("active", String(params.active));
  }
  if (typeof params.page === "number") {
    query.set("page", String(params.page));
  }
  if (typeof params.page_size === "number") {
    query.set("page_size", String(params.page_size));
  }

  const path =
    query.size > 0
      ? `/api/users/operations?${query.toString()}`
      : "/api/users/operations";
  const response = await fetch(resolveUrl(path));
  if (!response.ok) {
    throw await buildOperationUsersApiError(response);
  }

  return (await response.json()) as OperationUsersListResponse;
}

export async function assignOperationRole(input: {
  user_id: string;
}): Promise<{ user_id: string; assigned_role: string; assigned_at: string }> {
  const response = await fetch(resolveUrl("/api/users/operations"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw await buildOperationUsersApiError(response);
  }
  return (await response.json()) as {
    user_id: string;
    assigned_role: string;
    assigned_at: string;
  };
}

export async function setOperationAccess(
  userId: string,
  input: { enabled: boolean },
): Promise<{ user_id: string; enabled: boolean; updated_at: string }> {
  const response = await fetch(
    resolveUrl(`/api/users/operations/${encodeURIComponent(userId)}`),
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) {
    throw await buildOperationUsersApiError(response);
  }
  return (await response.json()) as {
    user_id: string;
    enabled: boolean;
    updated_at: string;
  };
}

async function buildOperationUsersApiError(
  response: Response,
): Promise<OperationUsersApiError> {
  const defaultError = new OperationUsersApiError(
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
    return new OperationUsersApiError(response.status, code, message);
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
