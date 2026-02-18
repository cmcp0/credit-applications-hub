import { afterEach, describe, expect, it, vi } from "vitest";

import {
  WorkflowsAdminApiError,
  listWebhookEvents,
  upsertWorkflowGraph,
} from "@/features/admin_workflows/api/workflows_admin_api";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("workflows_admin_api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends If-Match when upserting workflow graph", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        workflow_id: "wf-1",
        version: 2,
        graph_revision: 1,
        etag: 'W/"workflow:wf-1:v2:r1"',
        counts: { operations: 1, sub_operations: 1, triggers: 1 },
        updated_at: "2026-02-17T00:00:00Z",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await upsertWorkflowGraph(
      "wf-1",
      {
        expected_version: 2,
        operations: [],
        deleted_operation_ids: [],
        deleted_sub_operation_ids: [],
        deleted_trigger_ids: [],
      },
      { ifMatch: 'W/"workflow:wf-1:v2:r0"' },
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toContain("/api/workflows/wf-1/graph");
    expect(init.method).toBe("PUT");
    const headers = init.headers as Record<string, string>;
    expect(headers["If-Match"]).toBe('W/"workflow:wf-1:v2:r0"');
  });

  it("serializes webhook event query filters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        items: [],
        page: 1,
        page_size: 20,
        total: 0,
        sort_by: "occurred_at",
        sort_dir: "desc",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listWebhookEvents("wf-2", {
      direction: "egress",
      event_type: "ApplicationStatusUpdated",
      delivery_status: "failed",
      page: 1,
      page_size: 20,
      sort_by: "created_at",
      sort_dir: "asc",
    });

    const [path] = fetchMock.mock.calls[0] as [string];
    expect(path).toContain("/api/workflows/wf-2/webhooks/events?");
    expect(path).toContain("direction=EGRESS");
    expect(path).toContain("delivery_status=FAILED");
    expect(path).toContain("sort_by=created_at");
    expect(path).toContain("sort_dir=asc");
  });

  it("maps API error payloads into WorkflowsAdminApiError", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(
          { code: "INVALID_QUERY_PARAMS", message: "Invalid query parameters" },
          422,
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(listWebhookEvents("wf-3")).rejects.toEqual(
      expect.objectContaining<Partial<WorkflowsAdminApiError>>({
        name: "WorkflowsAdminApiError",
        status: 422,
        code: "INVALID_QUERY_PARAMS",
      }),
    );
  });
});

