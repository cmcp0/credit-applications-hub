import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useApplicationsStore } from "@/features/applications/store/applications_store";

describe("applications_store realtime reconciliation", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("ignores stale realtime updates by version", () => {
    const store = useApplicationsStore();

    store.applyRealtimeSummary(
      {
        id: "app-1",
        country: "MX",
        status_code: "PENDING_REVIEW",
        requested_amount: 5000,
        created_at: "2026-02-17T00:00:00Z",
        updated_at: "2026-02-17T00:00:00Z",
      },
      3,
    );

    store.applyRealtimeSummary(
      {
        id: "app-1",
        country: "MX",
        status_code: "APPROVED",
        requested_amount: 5000,
        created_at: "2026-02-17T00:00:00Z",
        updated_at: "2026-02-17T00:01:00Z",
      },
      2,
    );

    expect(store.items).toHaveLength(1);
    expect(store.items[0].status_code).toBe("PENDING_REVIEW");
    expect(store.latestVersionById["app-1"]).toBe(3);
  });

  it("updates item when newer version arrives", () => {
    const store = useApplicationsStore();

    store.applyRealtimeSummary(
      {
        id: "app-1",
        country: "MX",
        status_code: "PENDING_REVIEW",
        requested_amount: 5000,
        created_at: "2026-02-17T00:00:00Z",
        updated_at: "2026-02-17T00:00:00Z",
      },
      2,
    );

    store.applyRealtimeSummary(
      {
        id: "app-1",
        country: "MX",
        status_code: "APPROVED",
        requested_amount: 5000,
        created_at: "2026-02-17T00:00:00Z",
        updated_at: "2026-02-17T00:02:00Z",
      },
      4,
    );

    expect(store.items[0].status_code).toBe("APPROVED");
    expect(store.latestVersionById["app-1"]).toBe(4);
  });
});
