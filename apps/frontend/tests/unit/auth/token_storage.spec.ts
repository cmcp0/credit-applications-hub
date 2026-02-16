import { describe, expect, it } from "vitest";

import {
  buildAuthSessionState,
  parseAuthPrincipalFromToken,
} from "@/features/auth/model/auth_types";
import {
  AUTH_SESSION_STORAGE_KEY,
  clearAuthSession,
  loadAuthSession,
  persistAuthSession,
} from "@/features/auth/services/token_storage";
import { makeJwt, makeLoginResponse } from "../../helpers/auth_fixtures";

describe("token_storage", () => {
  it("persists and reloads a valid session", () => {
    const session = buildAuthSessionState(makeLoginResponse());
    persistAuthSession(session);

    const loaded = loadAuthSession(session.expiresAtEpochSeconds - 1);

    expect(loaded).toEqual(session);
  });

  it("clears invalid JSON payload", () => {
    sessionStorage.setItem(AUTH_SESSION_STORAGE_KEY, "{invalid");

    const loaded = loadAuthSession();

    expect(loaded).toBeNull();
    expect(sessionStorage.getItem(AUTH_SESSION_STORAGE_KEY)).toBeNull();
  });

  it("clears expired sessions", () => {
    const expiredToken = makeJwt({ exp: 100 });
    const session = buildAuthSessionState(
      makeLoginResponse({ access_token: expiredToken }),
    );
    persistAuthSession(session);

    const loaded = loadAuthSession(101);

    expect(loaded).toBeNull();
    expect(sessionStorage.getItem(AUTH_SESSION_STORAGE_KEY)).toBeNull();
  });

  it("rejects JWT payload missing required claims", () => {
    const malformedToken = makeJwt({ extraClaims: { exp: undefined } });

    expect(() => parseAuthPrincipalFromToken(malformedToken)).toThrow("Missing required exp claim");
  });

  it("clearAuthSession removes storage key", () => {
    sessionStorage.setItem(AUTH_SESSION_STORAGE_KEY, "{}");
    clearAuthSession();
    expect(sessionStorage.getItem(AUTH_SESSION_STORAGE_KEY)).toBeNull();
  });
});
