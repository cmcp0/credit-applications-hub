import { defineStore } from "pinia";

import {
  AuthSessionState,
  LoginResponse,
  buildAuthSessionState,
  isSessionExpired,
} from "@/features/auth/model/auth_types";
import {
  clearAuthSession,
  loadAuthSession,
  persistAuthSession,
} from "@/features/auth/services/token_storage";

interface AuthState {
  session: AuthSessionState | null;
}

export const useAuthStore = defineStore("auth_store", {
  state: (): AuthState => ({
    session: null,
  }),
  getters: {
    isAuthenticated(state): boolean {
      return !!state.session && !isSessionExpired(state.session);
    },
    principal(state) {
      return state.session?.principal ?? null;
    },
    bearerToken(state): string | null {
      return state.session?.token ?? null;
    },
  },
  actions: {
    hydrateFromStorage(nowEpochSeconds = Math.floor(Date.now() / 1000)): void {
      const session = loadAuthSession(nowEpochSeconds);
      this.session = session;
    },

    setSession(session: AuthSessionState): void {
      this.session = session;
      persistAuthSession(session);
    },

    applyLoginResponse(loginResponse: LoginResponse): AuthSessionState {
      const session = buildAuthSessionState(loginResponse);
      this.setSession(session);
      return session;
    },

    clearSession(): void {
      this.session = null;
      clearAuthSession();
    },

    logout(): void {
      this.clearSession();
    },

    hasValidSession(nowEpochSeconds = Math.floor(Date.now() / 1000)): boolean {
      if (!this.session) {
        return false;
      }

      if (isSessionExpired(this.session, nowEpochSeconds)) {
        this.clearSession();
        return false;
      }

      return true;
    },
  },
});

export type AuthStore = ReturnType<typeof useAuthStore>;
