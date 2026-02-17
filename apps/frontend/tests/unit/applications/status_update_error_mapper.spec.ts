import { describe, expect, it } from "vitest";

import { ApplicationsApiError } from "@/features/applications/api/applications_api";
import { mapStatusUpdateConflictMessage } from "@/features/applications/services/status_update_error_mapper";

describe("status_update_error_mapper", () => {
  it("maps INVALID_STATUS_TRANSITION into actionable message", () => {
    const message = mapStatusUpdateConflictMessage(
      new ApplicationsApiError(409, "INVALID_STATUS_TRANSITION", "invalid transition"),
    );

    expect(message).toContain("not allowed");
  });

  it("maps VERSION_CONFLICT into actionable message", () => {
    const message = mapStatusUpdateConflictMessage(
      new ApplicationsApiError(409, "VERSION_CONFLICT", "version conflict"),
    );

    expect(message).toContain("updated by another process");
  });

  it("returns null for non-conflict errors", () => {
    const message = mapStatusUpdateConflictMessage(
      new ApplicationsApiError(403, "PERMISSION_DENIED", "forbidden"),
    );

    expect(message).toBeNull();
  });
});
