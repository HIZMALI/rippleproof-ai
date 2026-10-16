import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { api, ApiError, request } from "../src/api/client";

// Explicit HTTP mocks: contract boundaries and errors, never integration evidence.
describe("HTTP boundary (mocked transport)", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("agent capability blocks before any transport call", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await expect(
      api.agent(
        "test",
        {
          supplier_id: "S-04",
          as_of: "2026-10-15",
          outage_start: "2026-10-16",
          outage_end_exclusive: "2026-10-24",
          include_mitigation: true,
        },
        {
          guided_available: true,
          agent_available: false,
          execution_kind: "disabled",
          limits: {
            max_model_requests: 2,
            max_tool_calls: 2,
            model_timeout_seconds: 5,
            run_timeout_seconds: 30,
            max_output_tokens_per_request: 1200,
            max_accumulated_input_bytes: 131072,
          },
        },
      ),
    ).rejects.toMatchObject({ code: "provider_not_authorized" });
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each([502, 504])(
    "retains a non-JSON proxy failure status %s",
    async (status) => {
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockResolvedValue(
            new Response("<html>upstream unavailable</html>", { status }),
          ),
      );
      await expect(request("/api/test", z.object({}))).rejects.toMatchObject({
        status,
        code: "invalid_contract",
      });
    },
  );
  it("fails closed on a mismatched response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response('{"count":"invented"}')),
    );
    await expect(
      request("/api/test", z.object({ count: z.number() })),
    ).rejects.toMatchObject({ code: "invalid_contract" });
  });
  it("preserves status without echoing a validation input", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response('{"detail":[{"input":"private"}]}', { status: 422 }),
        ),
    );
    await expect(request("/api/test", z.object({}))).rejects.toEqual(
      new ApiError(422, "request_failed"),
    );
  });
  it("bounds response bytes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("x".repeat(6 * 1024 * 1024 + 1))),
    );
    await expect(request("/api/test", z.object({}))).rejects.toMatchObject({
      code: "result_too_large",
    });
  });
  it("maps network failure honestly", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("connection refused")),
    );
    await expect(request("/api/test", z.object({}))).rejects.toMatchObject({
      code: "network_error",
    });
  });
  it("supports cancellation without retry", async () => {
    const controller = new AbortController();
    controller.abort();
    const fetch = vi
      .fn()
      .mockRejectedValue(new DOMException("abort", "AbortError"));
    vi.stubGlobal("fetch", fetch);
    await expect(
      request("/api/test", z.object({}), { signal: controller.signal }),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("guided mode only sends guided, without authorization", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetch);
    await expect(
      api.guided("explain", {
        supplier_id: "S-04",
        as_of: "2026-10-15",
        outage_start: "2026-10-16",
        outage_end_exclusive: "2026-10-24",
        include_mitigation: true,
      }),
    ).rejects.toMatchObject({ code: "invalid_contract" });
    const [, options] = fetch.mock.calls[0]!;
    expect(JSON.parse(options.body).mode).toBe("guided");
    expect(options.headers.has("Authorization")).toBe(false);
  });
});
