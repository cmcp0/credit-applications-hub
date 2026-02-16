import type {
  AuthSessionState,
  LoginResponse,
  RoleCode,
} from "@/features/auth/model/auth_types";
import { buildAuthSessionState } from "@/features/auth/model/auth_types";

interface JwtClaims {
  sub: string;
  roles: string[];
  permissions: string[];
  iat: number;
  exp: number;
  iss: string;
  aud: string;
}

interface JwtFixtureOptions {
  subject?: string;
  roles?: RoleCode[];
  permissions?: string[];
  exp?: number;
  iat?: number;
  iss?: string;
  aud?: string;
  extraClaims?: Record<string, unknown>;
}

export function makeJwt(options: JwtFixtureOptions = {}): string {
  const now = Math.floor(Date.now() / 1000);
  const claims: JwtClaims & Record<string, unknown> = {
    sub: options.subject ?? "test-user",
    roles: options.roles ?? ["customer"],
    permissions: options.permissions ?? ["applications:list_own"],
    iat: options.iat ?? now,
    exp: options.exp ?? now + 3600,
    iss: options.iss ?? "credit-app-backend",
    aud: options.aud ?? "credit-app-frontend",
    ...(options.extraClaims ?? {}),
  };

  const header = { alg: "HS256", typ: "JWT" };
  return `${encodeBase64Url(header)}.${encodeBase64Url(claims)}.signature`;
}

export function makeLoginResponse(overrides: Partial<LoginResponse> = {}): LoginResponse {
  return {
    access_token: overrides.access_token ?? makeJwt(),
    token_type: overrides.token_type ?? "bearer",
    expires_in: overrides.expires_in ?? 3600,
  };
}

export function makeSession(overrides: Partial<LoginResponse> = {}): AuthSessionState {
  return buildAuthSessionState(makeLoginResponse(overrides));
}

function encodeBase64Url(payload: object): string {
  return Buffer.from(JSON.stringify(payload), "utf-8")
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}
