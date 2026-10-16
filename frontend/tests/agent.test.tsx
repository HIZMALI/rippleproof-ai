// Controlled transport/component fixtures only. No network or real model call.
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AgentPanel } from "../src/features/agent/AgentPanel";
import { api, ApiError } from "../src/api/client";
import type {
  AgentCapabilities,
  AgentResponse,
  ScenarioRequest,
} from "../src/api/contracts";

const scenario: ScenarioRequest = {
  supplier_id: "S-04",
  as_of: "2026-10-15",
  outage_start: "2026-10-16",
  outage_end_exclusive: "2026-10-24",
  include_mitigation: true,
};
const id = `SC-${"a".repeat(20)}`;
const enabled: AgentCapabilities = {
  guided_available: true,
  agent_available: true,
  execution_kind: "remote_provider",
  provider: "openai",
  model: "synthetic-model",
  reason_code: null,
  limits: {
    max_model_requests: 2,
    max_tool_calls: 3,
    model_timeout_seconds: 5,
    run_timeout_seconds: 30,
    max_output_tokens_per_request: 1200,
    max_accumulated_input_bytes: 131072,
  },
};
const disabled: AgentCapabilities = {
  ...enabled,
  agent_available: false,
  execution_kind: "disabled",
  provider: null,
  model: null,
  reason_code: "provider_not_authorized",
};
const result: AgentResponse = {
  mode: "agent",
  provider: "openai",
  status: "completed",
  response: "Controlled transport test only.",
  scenario_id: id,
  facts: { scenario_id: id, request: scenario },
  model_requests: 2,
  tool_trace: [
    {
      name: "simulate_supply_disruption",
      arguments: scenario,
      status: "ok",
      started_at: "2026-10-15T00:00:00Z",
      finished_at: "2026-10-15T00:00:01Z",
      evidence_refs: ["P-22"],
      output_bytes: 100,
      output_sha256: "0".repeat(64),
    },
  ],
};
function mount(scenarioId = id) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <AgentPanel
        scenario={scenario}
        scenarioId={scenarioId}
        onClose={vi.fn()}
        onRef={vi.fn()}
      />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.spyOn(api, "capabilities").mockResolvedValue(disabled);
  vi.spyOn(api, "health").mockResolvedValue({
    status: "ready",
    database: "ready",
    graph: "synthetic",
    graph_exists: true,
  });
  vi.spyOn(api, "agent").mockResolvedValue(result);
  vi.spyOn(api, "guided").mockResolvedValue({
    ...result,
    mode: "guided_walkthrough",
    provider: "none",
    model_requests: 0,
  });
});
describe("agent capability and intent boundary (mocked transport)", () => {
  it("disabled config checks never invoke a model and guided fallback stays explicit", async () => {
    mount();
    await expect(
      screen.findByText("Real AI agent not configured for this interface"),
    ).resolves.toBeVisible();
    expect(
      screen.getByRole("button", { name: "Run real agent" }),
    ).toBeDisabled();
    expect(api.agent).not.toHaveBeenCalled();
    await userEvent.click(
      screen.getByRole("button", { name: "Run guided tools" }),
    );
    expect(api.guided).toHaveBeenCalledOnce();
    expect(api.agent).not.toHaveBeenCalled();
  });
  it("capability failure fails closed", async () => {
    vi.mocked(api.capabilities).mockRejectedValue(
      new ApiError(503, "database_unavailable"),
    );
    mount();
    expect(
      await screen.findByText(
        "Capability unavailable. Agent invocation stays disabled.",
      ),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Run real agent" }),
    ).toBeDisabled();
  });
  it("requires explicit authorization then submits one intentional bounded request", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(enabled);
    mount();
    const ack = await screen.findByLabelText(
      "I have separate operator authorization for this remote model run.",
    );
    expect(
      screen.getByRole("button", { name: "Run real agent" }),
    ).toBeDisabled();
    expect(api.agent).not.toHaveBeenCalled();
    await userEvent.click(ack);
    await userEvent.dblClick(
      screen.getByRole("button", { name: "Run real agent" }),
    );
    await waitFor(() => expect(api.agent).toHaveBeenCalledOnce());
    expect(api.agent).toHaveBeenCalledWith(
      expect.any(String),
      scenario,
      enabled,
      expect.any(AbortSignal),
    );
    expect(
      await screen.findByText(
        /Agent provider response · real MCP tools · 2 model calls/,
      ),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Run real agent" }),
    ).toBeDisabled();
  });
  it("rechecks stale server capabilities before submitting intent", async () => {
    vi.mocked(api.capabilities)
      .mockResolvedValueOnce(enabled)
      .mockResolvedValue(disabled);
    mount();
    await userEvent.click(
      await screen.findByLabelText(
        "I have separate operator authorization for this remote model run.",
      ),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Run real agent" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Real AI agent not configured",
    );
    expect(api.agent).not.toHaveBeenCalled();
  });
  it("checks current backend availability before any model request", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(enabled);
    vi.mocked(api.health).mockRejectedValue(
      new ApiError(503, "database_unavailable"),
    );
    mount();
    await userEvent.click(
      await screen.findByLabelText(
        "I have separate operator authorization for this remote model run.",
      ),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Run real agent" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Data source unavailable",
    );
    expect(api.agent).not.toHaveBeenCalled();
  });
  it("cancels waiting and does not automatically retry an uncertain agent attempt", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(enabled);
    vi.mocked(api.agent).mockImplementation(
      (_q, _s, _c, signal) =>
        new Promise((_resolve, reject) =>
          signal?.addEventListener("abort", () =>
            reject(new DOMException("cancelled", "AbortError")),
          ),
        ),
    );
    mount();
    await userEvent.click(
      await screen.findByLabelText(
        "I have separate operator authorization for this remote model run.",
      ),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Run real agent" }),
    );
    await waitFor(() => expect(api.agent).toHaveBeenCalledOnce());
    await userEvent.click(screen.getByRole("button", { name: "Stop waiting" }));
    expect(await screen.findByText(/Stopped waiting/)).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Run real agent" }),
    ).toBeDisabled();
    expect(api.agent).toHaveBeenCalledOnce();
  });
  it("labels controlled provider execution distinctly and disables stale citations", async () => {
    vi.mocked(api.capabilities).mockResolvedValue({
      ...enabled,
      execution_kind: "controlled",
      provider: "controlled",
      model: null,
    });
    vi.mocked(api.agent).mockResolvedValue({
      ...result,
      provider: "mock-provider",
    });
    mount(`SC-${"b".repeat(20)}`);
    await userEvent.click(
      await screen.findByLabelText(
        "I understand this is a controlled model simulator, not a remote LLM.",
      ),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Run controlled test agent" }),
    );
    expect(
      await screen.findByText(
        /Controlled provider simulation · real MCP tools · 2 model calls/,
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "P-22" })).toBeDisabled();
  });
});
