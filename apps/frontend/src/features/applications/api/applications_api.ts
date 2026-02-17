import {
  ApiErrorResponse,
  ApplicationCreateResponse,
  ApplicationDetail,
  ApplicationStatusUpdateResponse,
  CreateApplicationRequest,
  ListApplicationsParams,
  ListApplicationsResponse,
  ValidationFieldError,
  normalizeCreateRequest,
  normalizeStatusUpdateRequest,
  UpdateApplicationStatusRequest,
} from "@/features/applications/model/application_types";

const DEFAULT_ERROR_MESSAGE = "Unable to complete applications request";

export class ApplicationsApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly validationErrors: ValidationFieldError[];

  constructor(
    status: number,
    code: string,
    message: string,
    validationErrors: ValidationFieldError[] = [],
  ) {
    super(message);
    this.name = "ApplicationsApiError";
    this.status = status;
    this.code = code;
    this.validationErrors = validationErrors;
  }
}

export async function createApplication(
  request: CreateApplicationRequest,
): Promise<ApplicationCreateResponse> {
  const response = await fetch(resolveUrl("/api/applications"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(normalizeCreateRequest(request)),
  });

  if (!response.ok) {
    throw await buildApplicationsApiError(response);
  }

  return (await response.json()) as ApplicationCreateResponse;
}

export async function listApplications(
  params: ListApplicationsParams = {},
): Promise<ListApplicationsResponse> {
  const query = new URLSearchParams();
  if (params.country) {
    query.set("country", params.country.trim().toUpperCase());
  }
  if (params.status) {
    query.set("status", params.status.trim().toUpperCase());
  }
  if (params.page) {
    query.set("page", String(params.page));
  }
  if (params.page_size) {
    query.set("page_size", String(params.page_size));
  }

  const path = query.size > 0 ? `/api/applications?${query.toString()}` : "/api/applications";

  const response = await fetch(resolveUrl(path));
  if (!response.ok) {
    throw await buildApplicationsApiError(response);
  }

  return (await response.json()) as ListApplicationsResponse;
}

export async function getApplication(applicationId: string): Promise<ApplicationDetail> {
  const response = await fetch(resolveUrl(`/api/applications/${encodeURIComponent(applicationId)}`));
  if (!response.ok) {
    throw await buildApplicationsApiError(response);
  }

  return (await response.json()) as ApplicationDetail;
}

export async function updateApplicationStatus(
  applicationId: string,
  request: UpdateApplicationStatusRequest,
): Promise<ApplicationStatusUpdateResponse> {
  const response = await fetch(
    resolveUrl(`/api/applications/${encodeURIComponent(applicationId)}/status`),
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(normalizeStatusUpdateRequest(request)),
    },
  );

  if (!response.ok) {
    throw await buildApplicationsApiError(response);
  }

  return (await response.json()) as ApplicationStatusUpdateResponse;
}

async function buildApplicationsApiError(response: Response): Promise<ApplicationsApiError> {
  const defaultError = new ApplicationsApiError(response.status, "UNKNOWN_ERROR", DEFAULT_ERROR_MESSAGE);

  try {
    const payload = (await response.clone().json()) as Partial<ApiErrorResponse> & {
      errors?: ValidationFieldError[];
    };

    const code = typeof payload.code === "string" && payload.code.length > 0 ? payload.code : "UNKNOWN_ERROR";
    const message =
      typeof payload.message === "string" && payload.message.length > 0
        ? payload.message
        : DEFAULT_ERROR_MESSAGE;
    const validationErrors = Array.isArray(payload.errors)
      ? payload.errors.filter(
          (item): item is ValidationFieldError =>
            !!item &&
            typeof item.field === "string" &&
            typeof item.code === "string" &&
            typeof item.message === "string",
        )
      : [];

    return new ApplicationsApiError(response.status, code, message, validationErrors);
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
