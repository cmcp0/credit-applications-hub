export type RoleCode = "customer" | "operation" | "admin";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface AuthPrincipal {
  sub: string;
  roles: RoleCode[];
  permissions: string[];
  exp: number;
  iss: string;
  aud: string;
}

export interface AuthSessionState {
  token: string;
  tokenType: "bearer";
  expiresAtEpochSeconds: number;
  principal: AuthPrincipal;
}

export interface ApiErrorResponse {
  code: string;
  message: string;
}

const SUPPORTED_ROLES: ReadonlySet<RoleCode> = new Set(["customer", "operation", "admin"]);

export class AuthContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthContractError";
  }
}

export function isRoleCode(value: string): value is RoleCode {
  return SUPPORTED_ROLES.has(value as RoleCode);
}

export function decodeJwtPayload(token: string): Record<string, unknown> {
  const segments = token.split(".");
  if (segments.length !== 3) {
    throw new AuthContractError("Malformed JWT");
  }

  const payload = segments[1];
  const decoded = base64UrlDecode(payload);

  let parsed: unknown;
  try {
    parsed = JSON.parse(decoded);
  } catch {
    throw new AuthContractError("JWT payload is not valid JSON");
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new AuthContractError("JWT payload must be an object");
  }

  return parsed as Record<string, unknown>;
}

export function parseAuthPrincipalFromToken(token: string): AuthPrincipal {
  const payload = decodeJwtPayload(token);

  const sub = payload.sub;
  const roles = payload.roles;
  const permissions = payload.permissions;
  const exp = payload.exp;
  const iss = payload.iss;
  const aud = payload.aud;

  if (typeof sub !== "string" || sub.length === 0) {
    throw new AuthContractError("Missing required sub claim");
  }

  if (!Array.isArray(roles)) {
    throw new AuthContractError("Missing required roles claim");
  }

  if (!Array.isArray(permissions) || !permissions.every((value) => typeof value === "string")) {
    throw new AuthContractError("Missing required permissions claim");
  }

  if (typeof exp !== "number" || Number.isNaN(exp)) {
    throw new AuthContractError("Missing required exp claim");
  }

  if (typeof iss !== "string" || iss.length === 0) {
    throw new AuthContractError("Missing required iss claim");
  }

  if (typeof aud !== "string" || aud.length === 0) {
    throw new AuthContractError("Missing required aud claim");
  }

  const normalizedRoles = roles
    .filter((value): value is string => typeof value === "string")
    .filter((value): value is RoleCode => isRoleCode(value));

  return {
    sub,
    roles: normalizedRoles,
    permissions: [...new Set(permissions)],
    exp,
    iss,
    aud,
  };
}

export function buildAuthSessionState(loginResponse: LoginResponse): AuthSessionState {
  if (loginResponse.token_type !== "bearer") {
    throw new AuthContractError("Unsupported token type");
  }

  if (!Number.isFinite(loginResponse.expires_in) || loginResponse.expires_in <= 0) {
    throw new AuthContractError("Invalid expires_in in login response");
  }

  const principal = parseAuthPrincipalFromToken(loginResponse.access_token);

  return {
    token: loginResponse.access_token,
    tokenType: "bearer",
    expiresAtEpochSeconds: principal.exp,
    principal,
  };
}

export function parseAuthSessionState(value: unknown): AuthSessionState {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new AuthContractError("Session payload must be an object");
  }

  const session = value as Partial<AuthSessionState>;

  if (typeof session.token !== "string" || session.token.length === 0) {
    throw new AuthContractError("Session token is required");
  }

  if (session.tokenType !== "bearer") {
    throw new AuthContractError("Session tokenType must be bearer");
  }

  if (
    typeof session.expiresAtEpochSeconds !== "number" ||
    !Number.isFinite(session.expiresAtEpochSeconds)
  ) {
    throw new AuthContractError("Session expiresAtEpochSeconds is invalid");
  }

  const principal = parseAuthPrincipal(session.principal);

  if (principal.exp !== session.expiresAtEpochSeconds) {
    throw new AuthContractError("Session expiry must match principal exp");
  }

  return {
    token: session.token,
    tokenType: "bearer",
    expiresAtEpochSeconds: session.expiresAtEpochSeconds,
    principal,
  };
}

export function parseAuthPrincipal(value: unknown): AuthPrincipal {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new AuthContractError("Session principal is invalid");
  }

  const principal = value as Record<string, unknown>;
  const sub = principal.sub;
  const roles = principal.roles;
  const permissions = principal.permissions;
  const exp = principal.exp;
  const iss = principal.iss;
  const aud = principal.aud;

  if (typeof sub !== "string" || sub.length === 0) {
    throw new AuthContractError("Session principal sub is invalid");
  }

  if (!Array.isArray(roles)) {
    throw new AuthContractError("Session principal roles are invalid");
  }

  if (!Array.isArray(permissions) || !permissions.every((item) => typeof item === "string")) {
    throw new AuthContractError("Session principal permissions are invalid");
  }

  if (typeof exp !== "number" || Number.isNaN(exp)) {
    throw new AuthContractError("Session principal exp is invalid");
  }

  if (typeof iss !== "string" || iss.length === 0) {
    throw new AuthContractError("Session principal iss is invalid");
  }

  if (typeof aud !== "string" || aud.length === 0) {
    throw new AuthContractError("Session principal aud is invalid");
  }

  const normalizedRoles = roles
    .filter((item): item is string => typeof item === "string")
    .filter((item): item is RoleCode => isRoleCode(item));

  return {
    sub,
    roles: normalizedRoles,
    permissions: [...new Set(permissions)],
    exp,
    iss,
    aud,
  };
}

export function isSessionExpired(
  session: Pick<AuthSessionState, "expiresAtEpochSeconds">,
  nowEpochSeconds = Math.floor(Date.now() / 1000),
): boolean {
  return session.expiresAtEpochSeconds <= nowEpochSeconds;
}

function base64UrlDecode(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");

  if (typeof atob === "function") {
    return decodeURIComponent(
      Array.prototype.map
        .call(atob(padded), (character: string) => `%${(`00${character.charCodeAt(0).toString(16)}`).slice(-2)}`)
        .join(""),
    );
  }

  return Buffer.from(padded, "base64").toString("utf-8");
}
