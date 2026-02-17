import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createApplication,
  listApplications,
} from "@/features/applications/api/applications_api";

describe("applications_api", () => {
  const originalFetch = window.fetch;

  afterEach(() => {
    window.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("builds query params for list endpoint", async () => {
    const nativeFetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [],
          page: 2,
          page_size: 10,
          total: 0,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );
    window.fetch = nativeFetch as unknown as typeof window.fetch;

    await listApplications({
      country: "mx",
      status: "pending_review",
      page: 2,
      page_size: 10,
    });

    expect(nativeFetch).toHaveBeenCalledTimes(1);
    expect(String(nativeFetch.mock.calls[0][0])).toContain(
      "/api/applications?country=MX&status=PENDING_REVIEW&page=2&page_size=10",
    );
  });

  it("returns validation errors for 400 responses", async () => {
    const nativeFetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          code: "VALIDATION_ERROR",
          message: "Validation failed",
          errors: [
            {
              field: "identity_document",
              code: "INVALID_FORMAT",
              message: "Invalid document format",
            },
          ],
        }),
        {
          status: 400,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );
    window.fetch = nativeFetch as unknown as typeof window.fetch;

    await expect(
      createApplication({
        country: "MX",
        full_name: "Jane Doe",
        identity_document: "invalid",
        requested_amount: 5000,
        monthly_income: 2500,
      }),
    ).rejects.toMatchObject({
      status: 400,
      code: "VALIDATION_ERROR",
      validationErrors: [
        {
          field: "identity_document",
          code: "INVALID_FORMAT",
          message: "Invalid document format",
        },
      ],
    });
  });
});
