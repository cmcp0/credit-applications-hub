import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { subscribeToApplicationsUpdates } from "@/features/applications/realtime/applications_updates_subscriber";
import { AUTH_SESSION_STORAGE_KEY } from "@/features/auth/services/token_storage";
import { makeJwt, makeSession } from "../../helpers/auth_fixtures";

describe("applications_updates_subscriber", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("degrades when there is no active auth session", () => {
    const onConnectionStateChange = vi.fn();
    const websocketFactory = vi.fn();
    vi.stubGlobal("WebSocket", websocketFactory as unknown as typeof WebSocket);

    const subscription = subscribeToApplicationsUpdates(
      () => undefined,
      { onConnectionStateChange },
    );

    expect(onConnectionStateChange).toHaveBeenCalledWith("degraded");
    expect(websocketFactory).not.toHaveBeenCalled();
    subscription.unsubscribe();
  });

  it("builds websocket url with access token", () => {
    const token = makeJwt({
      roles: ["customer"],
      permissions: ["applications:list_own"],
    });
    sessionStorage.setItem(
      AUTH_SESSION_STORAGE_KEY,
      JSON.stringify(makeSession({ access_token: token })),
    );

    vi.stubEnv("VITE_APPLICATIONS_WS_URL", "https://backend.example.com/custom/ws");

    const openedUrls: string[] = [];

    class FakeWebSocket {
      static readonly CONNECTING = 0;
      static readonly OPEN = 1;
      static readonly CLOSING = 2;
      static readonly CLOSED = 3;

      readonly url: string;
      readyState = FakeWebSocket.CONNECTING;
      onopen: ((this: WebSocket, event: Event) => unknown) | null = null;
      onmessage: ((this: WebSocket, event: MessageEvent) => unknown) | null = null;
      onerror: ((this: WebSocket, event: Event) => unknown) | null = null;
      onclose: ((this: WebSocket, event: CloseEvent) => unknown) | null = null;

      constructor(url: string | URL) {
        this.url = String(url);
        openedUrls.push(this.url);
      }

      close(): void {
        this.readyState = FakeWebSocket.CLOSED;
      }
    }

    vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);

    const subscription = subscribeToApplicationsUpdates(() => undefined);

    expect(openedUrls).toHaveLength(1);
    const parsed = new URL(openedUrls[0]);
    expect(parsed.protocol).toBe("wss:");
    expect(parsed.pathname).toBe("/custom/ws");
    expect(parsed.searchParams.get("access_token")).toBe(token);

    subscription.unsubscribe();
  });
});
