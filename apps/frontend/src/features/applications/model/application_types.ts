export interface ApplicationSummary {
  id: string;
  country: string;
  status_code: string;
  requested_amount: number;
  created_at: string;
  updated_at: string;
  version?: number;
}

export interface ApplicationStatusMetadata {
  code: string;
  label: string;
  is_terminal: boolean;
  allowed_transitions: string[];
}

export interface ApplicationDetail extends ApplicationSummary {
  version: number;
  status_metadata: ApplicationStatusMetadata;
}

export interface ListApplicationsParams {
  country?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface ListApplicationsResponse {
  items: ApplicationSummary[];
  page: number;
  page_size: number;
  total: number;
}

export interface CreateApplicationRequest {
  country: string;
  full_name: string;
  identity_document: string;
  requested_amount: number;
  monthly_income: number;
}

export interface ApplicationCreateResponse {
  id: string;
  country: string;
  status_code: string;
  created_at: string;
}

export interface UpdateApplicationStatusRequest {
  status: string;
  reason_code?: string;
  expected_version: number;
}

export interface ApplicationStatusUpdateResponse {
  id: string;
  previous_status_code: string;
  status_code: string;
  updated_at: string;
  version: number;
}

export interface ApiErrorResponse {
  code: string;
  message: string;
}

export interface ValidationFieldError {
  field: string;
  code: string;
  message: string;
}

export interface ValidationErrorResponse extends ApiErrorResponse {
  errors: ValidationFieldError[];
}

export class ApplicationsContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApplicationsContractError";
  }
}

export function normalizeCreateRequest(request: CreateApplicationRequest): CreateApplicationRequest {
  return {
    country: request.country.trim().toUpperCase(),
    full_name: request.full_name.trim(),
    identity_document: request.identity_document.trim(),
    requested_amount: request.requested_amount,
    monthly_income: request.monthly_income,
  };
}

export function normalizeStatusUpdateRequest(
  request: UpdateApplicationStatusRequest,
): UpdateApplicationStatusRequest {
  return {
    status: request.status.trim().toUpperCase(),
    reason_code: request.reason_code?.trim() || undefined,
    expected_version: request.expected_version,
  };
}
