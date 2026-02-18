import type { ApplicationSummary } from "@/features/applications/model/application_types";
import { loadAuthSession } from "@/features/auth/services/token_storage";

export interface ApplicationsRealtimeEvent {
  application: ApplicationSummary;
  version: number;
}

type RealtimeConnectionState = "connected" | "degraded";

interface SubscribeOptions {
  onConnectionStateChange?: (state: RealtimeConnectionState) => void;
}

export interface ApplicationsUpdatesSubscription {
  unsubscribe(): void;
}

const CUSTOM_EVENT_NAME = "credit-applications:realtime";

export function dispatchApplicationsRealtimeEvent(event: ApplicationsRealtimeEvent): void {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new CustomEvent<ApplicationsRealtimeEvent>(CUSTOM_EVENT_NAME, { detail: event }));
}

export function subscribeToApplicationsUpdates(
  onEvent: (event: ApplicationsRealtimeEvent) => void,
  options: SubscribeOptions = {},
): ApplicationsUpdatesSubscription {
  if (typeof window === "undefined") {
    return {
      unsubscribe(): void {
        // no-op
      },
    };
  }

  const onConnectionStateChange = options.onConnectionStateChange ?? (() => undefined);

  const customEventHandler = (event: Event): void => {
    const customEvent = event as CustomEvent<ApplicationsRealtimeEvent>;
    if (isRealtimeEvent(customEvent.detail)) {
      onEvent(customEvent.detail);
    }
  };
  window.addEventListener(CUSTOM_EVENT_NAME, customEventHandler as EventListener);

  const wsUrl = resolveWebSocketUrl();
  if (!wsUrl) {
    onConnectionStateChange("degraded");
    return {
      unsubscribe(): void {
        window.removeEventListener(CUSTOM_EVENT_NAME, customEventHandler as EventListener);
      },
    };
  }
  if (typeof WebSocket === "undefined") {
    onConnectionStateChange("degraded");
    return {
      unsubscribe(): void {
        window.removeEventListener(CUSTOM_EVENT_NAME, customEventHandler as EventListener);
      },
    };
  }

  const socket = new WebSocket(wsUrl);
  socket.onopen = () => {
    onConnectionStateChange("connected");
  };
  socket.onmessage = (message) => {
    try {
      const parsed = JSON.parse(String(message.data)) as unknown;
      const event = extractRealtimeEvent(parsed);
      if (event) {
        onEvent(event);
      }
    } catch {
      // Ignore malformed payloads from transport.
    }
  };
  socket.onerror = () => {
    onConnectionStateChange("degraded");
  };
  socket.onclose = () => {
    onConnectionStateChange("degraded");
  };

  return {
    unsubscribe(): void {
      window.removeEventListener(CUSTOM_EVENT_NAME, customEventHandler as EventListener);
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    },
  };
}

function resolveWebSocketUrl(): string | null {
  const token = resolveAccessToken();
  if (!token) {
    return null;
  }

  const configured = (import.meta.env.VITE_APPLICATIONS_WS_URL ?? "").trim();
  if (configured.length > 0) {
    return withAccessToken(configured, token);
  }

  const base = (import.meta.env.VITE_API_BASE_URL ?? "").trim() || window.location.origin;
  let parsed: URL;
  try {
    parsed = new URL(base, window.location.origin);
  } catch {
    return null;
  }

  const protocol = toWebSocketProtocol(parsed.protocol);
  if (!protocol) {
    return null;
  }

  parsed.protocol = protocol;
  parsed.pathname = "/api/realtime/applications/ws";
  parsed.search = "";
  parsed.hash = "";
  parsed.searchParams.set("access_token", token);
  return parsed.toString();
}

function withAccessToken(url: string, token: string): string | null {
  let parsed: URL;
  try {
    parsed = new URL(url, window.location.origin);
  } catch {
    return null;
  }

  const protocol = toWebSocketProtocol(parsed.protocol);
  if (!protocol) {
    return null;
  }
  parsed.protocol = protocol;
  parsed.searchParams.set("access_token", token);
  return parsed.toString();
}

function toWebSocketProtocol(protocol: string): string | null {
  if (protocol === "http:") {
    return "ws:";
  }
  if (protocol === "https:") {
    return "wss:";
  }
  if (protocol === "ws:" || protocol === "wss:") {
    return protocol;
  }
  return null;
}

function resolveAccessToken(): string | null {
  const session = loadAuthSession();
  if (!session) {
    return null;
  }
  return session.token;
}

function extractRealtimeEvent(value: unknown): ApplicationsRealtimeEvent | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const asRecord = value as Record<string, unknown>;
  if (isRealtimeEvent(asRecord)) {
    return asRecord;
  }

  const nestedEvent = asRecord.event;
  if (isRealtimeEvent(nestedEvent)) {
    return nestedEvent;
  }

  return null;
}

function isRealtimeEvent(value: unknown): value is ApplicationsRealtimeEvent {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  const asRecord = value as Record<string, unknown>;
  if (typeof asRecord.version !== "number") {
    return false;
  }

  const application = asRecord.application;
  if (!application || typeof application !== "object" || Array.isArray(application)) {
    return false;
  }

  const app = application as Record<string, unknown>;
  return (
    typeof app.id === "string" &&
    typeof app.country === "string" &&
    typeof app.status_code === "string" &&
    typeof app.requested_amount === "number" &&
    typeof app.created_at === "string" &&
    typeof app.updated_at === "string"
  );
}
