import { z } from "zod";
import {
  AgentCapabilitiesSchema,
  AgentResponseSchema,
  AlternativesResponseSchema,
  DecisionPreviewSchema,
  DecisionRecordSchema,
  GraphSummarySchema,
  HealthResponseSchema,
  ImpactResponseSchema,
  ScenarioRequestSchema,
  ScenarioResponseSchema,
  type ApprovalRequest,
  type AgentCapabilities,
  type PrepareRequest,
  type ScenarioRequest,
} from "./contracts";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
  ) {
    super(code);
    this.name = "ApiError";
  }
}

export function errorCopy(error: unknown): string {
  if (!(error instanceof ApiError))
    return "The request could not be completed. Please try again.";
  if (
    error.code === "provider_not_authorized" ||
    error.code === "provider_not_configured"
  )
    return "Real AI agent not configured. Guided tools do not require a model or API key.";
  if (error.code === "approval_not_configured")
    return "Approval unavailable. An operator must configure the backend approval secret first.";
  if (error.status === 401)
    return "Authorization was not accepted. Check your local operator token. It has been cleared.";
  if (error.status === 404)
    return "No matching record was found. Check the identifier and data source.";
  if (error.status === 409)
    return "Preview is stale or the action conflicts with an existing record. Refresh and review again.";
  if (error.status === 422)
    return "The request could not be validated. Check the identifiers, dates, and required fields.";
  if (
    error.status === 503 ||
    error.status === 502 ||
    error.status === 504 ||
    error.code === "network_error"
  )
    return "Data source unavailable. Previous simulation is not shown as current. Retry when the service recovers.";
  if (error.code === "result_too_large")
    return "This result exceeds the workspace limit. Narrow the scope before retrying.";
  if (error.code === "request_timeout")
    return "The request timed out. Check the connection before retrying.";
  if (error.code === "invalid_contract")
    return "The service returned data this workspace could not verify. No result is shown.";
  return "The service could not complete the request. Please retry or contact the local operator.";
}

export const isLoopback = (hostname: string): boolean =>
  ["localhost", "127.0.0.1", "[::1]", "::1"].includes(hostname.toLowerCase());

export const sourceUnavailable = (error: unknown): boolean =>
  error instanceof ApiError &&
  (error.code === "database_unavailable" ||
    error.status === 0 ||
    error.status === 502 ||
    error.status === 504);

type Options = {
  method?: "GET" | "POST";
  body?: unknown;
  signal?: AbortSignal;
  token?: string;
  timeout?: number;
};
const MAX_BYTES = 6 * 1024 * 1024;

export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  options: Options = {},
): Promise<T> {
  const timeout = AbortSignal.timeout(options.timeout ?? 30000);
  const signal = options.signal
    ? AbortSignal.any([options.signal, timeout])
    : timeout;
  try {
    const headers = new Headers({ Accept: "application/json" });
    if (options.body !== undefined)
      headers.set("Content-Type", "application/json");
    if (options.token) headers.set("Authorization", `Bearer ${options.token}`);
    const response = await fetch(path, {
      method: options.method ?? "GET",
      headers,
      signal,
      credentials: "omit",
      cache: "no-store",
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
    });
    const reader = response.body?.getReader();
    if (!reader) throw new ApiError(502, "invalid_contract");
    let size = 0;
    const chunks: Uint8Array[] = [];
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BYTES) {
        await reader.cancel();
        throw new ApiError(413, "result_too_large");
      }
      chunks.push(value);
    }
    const buffer = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      buffer.set(chunk, offset);
      offset += chunk.byteLength;
    }
    let data: unknown;
    try {
      data = JSON.parse(new TextDecoder().decode(buffer));
    } catch {
      throw new ApiError(
        response.ok ? 502 : response.status,
        "invalid_contract",
      );
    }
    if (!response.ok) {
      // Never echo backend validation inputs or arbitrary error text: those may contain a secret.
      const envelope = z
        .object({
          error: z.object({ code: z.string() }).optional(),
          error_code: z.string().nullable().optional(),
        })
        .safeParse(data);
      throw new ApiError(
        response.status,
        envelope.success
          ? (envelope.data.error?.code ??
              envelope.data.error_code ??
              "request_failed")
          : "request_failed",
      );
    }
    const parsed = schema.safeParse(data);
    if (!parsed.success) throw new ApiError(502, "invalid_contract");
    return parsed.data;
  } catch (error) {
    if (options.signal?.aborted)
      throw new DOMException("Request cancelled", "AbortError");
    if (timeout.aborted) throw new ApiError(0, "request_timeout");
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, "network_error");
  }
}

// This endpoint has no typed OpenAPI response. Verified against tools.history_item
// and the actual GET response, separately checked by the live contract smoke test.
export const HistoryItemSchema = z.object({
  decision_id: z.string().regex(/^D-[a-f0-9]{24}$/),
  scenario_id: z.string(),
  status: z.literal("APPROVED_INTERNAL"),
  created_at: z.string(),
  plan_id: z.string(),
  evidence_ref: z.string(),
  operational_fingerprint: z.string(),
  estimated_additional_procurement_cost: z.string(),
  detail_endpoint: z.string(),
});
export const HistorySchema = z.object({
  total: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  items: z.array(HistoryItemSchema),
  next_offset: z.number().int().nullable(),
});
export type HistoryItem = z.infer<typeof HistoryItemSchema>;

export const api = {
  capabilities: (signal?: AbortSignal) =>
    request("/api/agent/capabilities", AgentCapabilitiesSchema, { signal }),
  health: (signal?: AbortSignal) =>
    request("/health", HealthResponseSchema, { signal }),
  summary: (signal?: AbortSignal) =>
    request("/api/graph/summary", GraphSummarySchema, { signal }),
  impact: (supplier: string, signal?: AbortSignal) =>
    request(
      `/api/impact-paths?supplier_id=${encodeURIComponent(supplier)}`,
      ImpactResponseSchema,
      { signal },
    ),
  alternatives: (part: string, date: string, signal?: AbortSignal) =>
    request(
      `/api/alternatives?part_id=${encodeURIComponent(part)}&as_of=${encodeURIComponent(date)}`,
      AlternativesResponseSchema,
      { signal },
    ),
  simulate: (scenario: ScenarioRequest, signal?: AbortSignal) =>
    request("/api/scenarios/simulate", ScenarioResponseSchema, {
      method: "POST",
      body: ScenarioRequestSchema.parse(scenario),
      signal,
    }),
  guided: async (
    question: string,
    scenario: ScenarioRequest,
    signal?: AbortSignal,
  ) => {
    const result = await request("/api/agent/run", AgentResponseSchema, {
      method: "POST",
      body: { question, scenario, mode: "guided" },
      signal,
      timeout: 105000,
    });
    if (result.mode !== "guided_walkthrough" || result.model_requests !== 0)
      throw new ApiError(502, "invalid_contract");
    return result;
  },
  agent: async (
    question: string,
    scenario: ScenarioRequest,
    capability: AgentCapabilities,
    signal?: AbortSignal,
  ) => {
    if (!capability.agent_available || !isLoopback(window.location.hostname))
      throw new ApiError(503, "provider_not_authorized");
    const result = await request("/api/agent/run", AgentResponseSchema, {
      method: "POST",
      body: {
        question,
        scenario: ScenarioRequestSchema.parse(scenario),
        mode: "agent",
      },
      signal,
      timeout: Math.min(
        125000,
        capability.limits.run_timeout_seconds * 1000 + 5000,
      ),
    });
    const source = ScenarioRequestSchema.safeParse(result.facts?.request);
    if (
      result.mode !== "agent" ||
      result.model_requests < 1 ||
      result.model_requests > capability.limits.max_model_requests ||
      (result.tool_trace ?? []).length > capability.limits.max_tool_calls ||
      !(result.tool_trace ?? []).some(
        (t) => t.name === "simulate_supply_disruption" && t.status === "ok",
      ) ||
      !source.success ||
      JSON.stringify(source.data) !==
        JSON.stringify(ScenarioRequestSchema.parse(scenario)) ||
      !result.scenario_id ||
      result.scenario_id !== result.facts?.scenario_id ||
      (capability.execution_kind === "remote_provider" &&
        result.provider !== capability.provider)
    )
      throw new ApiError(502, "invalid_contract");
    return result;
  },
  prepare: (body: PrepareRequest, signal?: AbortSignal) =>
    request("/api/decisions/prepare", DecisionPreviewSchema, {
      method: "POST",
      body,
      signal,
    }),
  approve: (body: ApprovalRequest, token: string, signal?: AbortSignal) => {
    if (!isLoopback(window.location.hostname))
      throw new ApiError(401, "non_local_approval");
    return request("/api/decisions/approve", DecisionRecordSchema, {
      method: "POST",
      body,
      token,
      signal,
    });
  },
  history: (scenarioId: string, offset: number, signal?: AbortSignal) =>
    request(
      `/api/decisions?offset=${offset}&limit=5${scenarioId ? `&scenario_id=${encodeURIComponent(scenarioId)}` : ""}`,
      HistorySchema,
      { signal },
    ),
  decision: (id: string, signal?: AbortSignal) =>
    request(`/api/decisions/${encodeURIComponent(id)}`, DecisionRecordSchema, {
      signal,
    }),
};

export const safeReadRetry = (count: number, error: Error): boolean =>
  count < 1 &&
  error instanceof ApiError &&
  (error.status === 0 || error.status >= 500);
