import {
  AuthSessionState,
  isSessionExpired,
  parseAuthSessionState,
} from "@/features/auth/model/auth_types";

export const AUTH_SESSION_STORAGE_KEY = "auth_session";

export function persistAuthSession(state: AuthSessionState): void {
  sessionStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(state));
}

export function loadAuthSession(nowEpochSeconds = Math.floor(Date.now() / 1000)): AuthSessionState | null {
  const raw = sessionStorage.getItem(AUTH_SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    clearAuthSession();
    return null;
  }

  try {
    const session = parseAuthSessionState(parsed);
    if (isSessionExpired(session, nowEpochSeconds)) {
      clearAuthSession();
      return null;
    }
    return session;
  } catch {
    clearAuthSession();
    return null;
  }
}

export function clearAuthSession(): void {
  sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
}
