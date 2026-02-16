import type { Router } from "vue-router";

import type { AuthStore } from "@/features/auth/store/auth_store";
import { parseApiError } from "@/features/auth/api/auth_api";

const API_PREFIX = "/api";
const TOKEN_INVALID_CODES = new Set(["TOKEN_INVALID", "TOKEN_EXPIRED"]);

export function bootstrapAuthSession(authStore: AuthStore): void {
  authStore.hydrateFromStorage();
}

export function installAuthAwareFetch(
  authStore: AuthStore,
  router: Router,
): void {
  if (typeof window === "undefined") {
    return;
  }

  const globalWithAuthState = window as Window & {
    __creditAuthFetchInstalled__?: boolean;
  };

  if (globalWithAuthState.__creditAuthFetchInstalled__) {
    return;
  }

  const nativeFetch = window.fetch.bind(window);
  globalWithAuthState.__creditAuthFetchInstalled__ = true;

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    let request = new Request(normalizeRequestInput(input), init);
    const requestUrl = new URL(request.url, window.location.origin);
    const isProtectedApi =
      requestUrl.pathname === API_PREFIX || requestUrl.pathname.startsWith(`${API_PREFIX}/`);

    if (isProtectedApi) {
      if (!authStore.hasValidSession()) {
        await redirectToLogin(router);
        throw new Error("LOCAL_SESSION_EXPIRED");
      }

      const bearerToken = authStore.bearerToken;
      if (bearerToken) {
        const headers = new Headers(request.headers);
        headers.set("Authorization", `Bearer ${bearerToken}`);
        request = new Request(request, { headers });
      }
    }

    const response = await nativeFetch(request);

    if (!isProtectedApi) {
      return response;
    }

    if (response.status === 401) {
      const apiError = await parseApiError(response);
      if (TOKEN_INVALID_CODES.has(apiError.code)) {
        authStore.clearSession();
        await redirectToLogin(router);
      }
    }

    if (response.status === 403) {
      await redirectToForbidden(router);
    }

    return response;
  };
}

function normalizeRequestInput(input: RequestInfo | URL): RequestInfo {
  if (typeof input === "string") {
    if (/^https?:\/\//i.test(input)) {
      return input;
    }
    return new URL(input, window.location.origin).toString();
  }

  if (input instanceof URL) {
    return input.toString();
  }

  return input;
}

async function redirectToLogin(router: Router): Promise<void> {
  if (router.currentRoute.value.path !== "/login") {
    await router.replace("/login");
  }
}

async function redirectToForbidden(router: Router): Promise<void> {
  if (router.currentRoute.value.path !== "/forbidden") {
    await router.replace("/forbidden");
  }
}
