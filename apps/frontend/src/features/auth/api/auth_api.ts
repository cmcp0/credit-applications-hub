import {
  ApiErrorResponse,
  LoginRequest,
  LoginResponse,
} from "@/features/auth/model/auth_types";

const DEFAULT_ERROR_MESSAGE = "Unable to complete request";

export class AuthApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.code = code;
  }
}

export async function login(request: LoginRequest): Promise<LoginResponse> {
  const normalizedPayload = {
    email: request.email.trim(),
    password: request.password,
  };

  const response = await fetch(resolveUrl("/auth/login"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(normalizedPayload),
  });

  if (!response.ok) {
    const apiError = await parseApiError(response);
    throw new AuthApiError(response.status, apiError.code, apiError.message);
  }

  const payload = (await response.json()) as LoginResponse;

  if (typeof payload.access_token !== "string" || payload.access_token.length === 0) {
    throw new AuthApiError(500, "INVALID_LOGIN_RESPONSE", "Login response missing access token");
  }

  if (payload.token_type !== "bearer") {
    throw new AuthApiError(500, "INVALID_LOGIN_RESPONSE", "Login response token_type must be bearer");
  }

  if (!Number.isFinite(payload.expires_in) || payload.expires_in <= 0) {
    throw new AuthApiError(500, "INVALID_LOGIN_RESPONSE", "Login response expires_in is invalid");
  }

  return payload;
}

export async function parseApiError(response: Response): Promise<ApiErrorResponse> {
  try {
    const payload = (await response.clone().json()) as Partial<ApiErrorResponse>;
    const code = typeof payload.code === "string" && payload.code.length > 0 ? payload.code : "UNKNOWN_ERROR";
    const message =
      typeof payload.message === "string" && payload.message.length > 0
        ? payload.message
        : DEFAULT_ERROR_MESSAGE;

    return { code, message };
  } catch {
    return {
      code: "UNKNOWN_ERROR",
      message: DEFAULT_ERROR_MESSAGE,
    };
  }
}

function resolveUrl(path: string): string {
  const base = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
  if (!base) {
    return path;
  }

  return new URL(path, base).toString();
}
