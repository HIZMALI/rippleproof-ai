// Generated from live FastAPI OpenAPI. Run npm run contracts; do not hand-edit.
import { z } from "zod";

export const AgentLimitsSchema = z
  .object({
    max_model_requests: z.number().int().min(1),
    max_tool_calls: z.number().int().min(1),
    model_timeout_seconds: z.number().gt(0),
    run_timeout_seconds: z.number().min(1),
    max_output_tokens_per_request: z.literal(1200).default(1200),
    max_accumulated_input_bytes: z.literal(131072).default(131072),
  })
  .strict();
export type AgentLimits = z.infer<typeof AgentLimitsSchema>;

export const AgentCapabilitiesSchema = z
  .object({
    guided_available: z.literal(true).default(true),
    agent_available: z.boolean(),
    execution_kind: z.enum(["disabled", "controlled", "remote_provider"]),
    provider: z.union([z.string(), z.null()]).optional(),
    model: z.union([z.string(), z.null()]).optional(),
    reason_code: z
      .union([
        z.enum(["provider_not_authorized", "provider_not_configured"]),
        z.null(),
      ])
      .optional(),
    limits: AgentLimitsSchema,
  })
  .strict();
export type AgentCapabilities = z.infer<typeof AgentCapabilitiesSchema>;

export const ScenarioRequestSchema = z
  .object({
    supplier_id: z.string().max(7).regex(new RegExp("^S-[0-9]{2,5}$")),
    as_of: z.iso.date(),
    outage_start: z.iso.date(),
    outage_end_exclusive: z.iso.date(),
    include_mitigation: z.boolean().default(true),
  })
  .strict();
export type ScenarioRequest = z.infer<typeof ScenarioRequestSchema>;

export const AgentRequestSchema = z
  .object({
    question: z.string().min(1).max(2000).regex(new RegExp("\\S")),
    scenario: z.union([ScenarioRequestSchema, z.null()]).optional(),
    mode: z.enum(["guided", "agent"]).default("guided"),
  })
  .strict();
export type AgentRequest = z.infer<typeof AgentRequestSchema>;

export const ToolTraceSchema = z
  .object({
    name: z.string(),
    arguments: z.record(z.string(), z.json()),
    started_at: z.string(),
    finished_at: z.string(),
    status: z.enum(["ok", "error"]),
    evidence_refs: z.array(z.string()),
    output_bytes: z.number().int(),
    output_sha256: z.string(),
  })
  .strict();
export type ToolTrace = z.infer<typeof ToolTraceSchema>;

export const TokenUsageSchema = z
  .object({
    input_tokens: z.union([z.number().int().min(0), z.null()]).optional(),
    output_tokens: z.union([z.number().int().min(0), z.null()]).optional(),
    total_tokens: z.union([z.number().int().min(0), z.null()]).optional(),
  })
  .strict();
export type TokenUsage = z.infer<typeof TokenUsageSchema>;

export const ProviderRequestMetadataSchema = z
  .object({
    sequence: z.number().int().min(1),
    started_at: z.string(),
    duration_ms: z.number().min(0),
    transport: z.enum(["default", "injected"]),
    http_status: z.union([z.number().int().min(100), z.null()]).optional(),
    request_id: z.union([z.string(), z.null()]).optional(),
    response_id: z.union([z.string(), z.null()]).optional(),
    model: z.union([z.string(), z.null()]).optional(),
    provider_status: z
      .union([
        z.enum([
          "queued",
          "in_progress",
          "completed",
          "failed",
          "incomplete",
          "cancelled",
        ]),
        z.null(),
      ])
      .optional(),
    outcome: z.enum([
      "completed",
      "rejected",
      "timeout",
      "network_error",
      "malformed_response",
      "response_too_large",
      "interrupted",
      "incomplete",
    ]),
    error_code: z
      .union([
        z.enum([
          "provider_authentication_failed",
          "provider_error",
          "model_timeout",
          "provider_unavailable",
          "invalid_model_output",
          "interrupted",
        ]),
        z.null(),
      ])
      .optional(),
    usage: TokenUsageSchema.optional(),
    usage_consistent: z.union([z.boolean(), z.null()]).optional(),
    redacted_fields: z
      .array(z.enum(["request_id", "response_id", "model"]))
      .optional(),
  })
  .strict();
export type ProviderRequestMetadata = z.infer<
  typeof ProviderRequestMetadataSchema
>;

export const ProviderTelemetrySchema = z
  .object({
    requests: z.array(ProviderRequestMetadataSchema),
    requests_recorded: z.number().int().min(0),
    usage_complete: z.boolean(),
    usage: TokenUsageSchema,
    observed_usage: TokenUsageSchema,
    total_provider_duration_ms: z.number().min(0),
  })
  .strict();
export type ProviderTelemetry = z.infer<typeof ProviderTelemetrySchema>;

export const AgentResponseSchema = z
  .object({
    mode: z.enum(["guided_walkthrough", "agent"]),
    provider: z.string(),
    status: z.enum(["completed", "needs_input", "safe_fallback", "error"]),
    response: z.string(),
    scenario_id: z.union([z.string(), z.null()]).optional(),
    facts: z.union([z.record(z.string(), z.json()), z.null()]).optional(),
    tool_trace: z.array(ToolTraceSchema).optional(),
    assumptions: z.array(z.string()).optional(),
    warnings: z.array(z.string()).optional(),
    error_code: z.union([z.string(), z.null()]).optional(),
    model_requests: z.number().int().default(0),
    provider_telemetry: z.union([ProviderTelemetrySchema, z.null()]).optional(),
  })
  .strict();
export type AgentResponse = z.infer<typeof AgentResponseSchema>;

export const AllocationSchema = z.object({
  receipt_id: z.string(),
  quantity: z.number().int(),
  arrival_date: z.iso.date(),
  evidence_refs: z.array(z.string()),
});
export type Allocation = z.infer<typeof AllocationSchema>;

export const JsonValueSchema = z.json();
export type JsonValue = z.infer<typeof JsonValueSchema>;

export const EvidenceNodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  properties: z.record(z.string(), JsonValueSchema),
});
export type EvidenceNode = z.infer<typeof EvidenceNodeSchema>;

export const SupplyTermsSchema = z.object({
  unit_cost: z.number().min(0),
  lead_days: z.number().int().min(0),
  daily_capacity: z.number().int().min(0),
  is_primary: z.boolean(),
});
export type SupplyTerms = z.infer<typeof SupplyTermsSchema>;

export const EvidenceRelationshipSchema = z.object({
  id: z.string(),
  type: z.string(),
  source_id: z.string(),
  target_id: z.string(),
  properties: z.record(z.string(), JsonValueSchema),
});
export type EvidenceRelationship = z.infer<typeof EvidenceRelationshipSchema>;

export const CertificateCheckSchema = z.object({
  certificate_id: z.string(),
  name: z.string(),
  status: z.enum(["valid", "expired", "missing"]),
  valid_until: z.union([z.iso.date(), z.null()]),
  requirement: EvidenceRelationshipSchema,
  holding: z.union([EvidenceRelationshipSchema, z.null()]),
});
export type CertificateCheck = z.infer<typeof CertificateCheckSchema>;

export const AlternativeSupplierSchema = z.object({
  supplier: EvidenceNodeSchema,
  supply_terms: SupplyTermsSchema,
  supplies_relationship: EvidenceRelationshipSchema,
  certifications_valid: z.boolean(),
  certificate_checks: z.array(CertificateCheckSchema),
});
export type AlternativeSupplier = z.infer<typeof AlternativeSupplierSchema>;

export const CertificateRequirementSchema = z.object({
  certificate_id: z.string(),
  name: z.string(),
  certificate: EvidenceNodeSchema,
  relationship: EvidenceRelationshipSchema,
});
export type CertificateRequirement = z.infer<
  typeof CertificateRequirementSchema
>;

export const AlternativesResponseSchema = z.object({
  part: EvidenceNodeSchema,
  as_of: z.iso.date(),
  interpretation: z
    .string()
    .default(
      "Non-primary suppliers offering this part, with modeled certificate checks only. This is not a purchase recommendation or a capacity/arrival feasibility assessment. Certificates are valid through valid_until, inclusive. Costs are synthetic units.",
    ),
  required_certificates: z.array(CertificateRequirementSchema),
  candidates: z.array(AlternativeSupplierSchema),
});
export type AlternativesResponse = z.infer<typeof AlternativesResponseSchema>;

export const ApprovalRequestSchema = z
  .object({
    scenario: ScenarioRequestSchema,
    mitigation_plan_id: z
      .string()
      .regex(
        new RegExp(
          "^(cost_first|lead_first|no_procurement|supplier:S-[0-9]{2,5})$",
        ),
      ),
    expected_scenario_id: z.string().regex(new RegExp("^SC-[a-f0-9]{20}$")),
    expected_operational_fingerprint: z
      .string()
      .regex(new RegExp("^[a-f0-9]{64}$")),
    expected_plan_revision: z.string().regex(new RegExp("^[a-f0-9]{64}$")),
    idempotency_key: z.string().regex(new RegExp("^[A-Za-z0-9_-]{16,80}$")),
    operator_id: z.string().regex(new RegExp("^[A-Za-z][A-Za-z0-9_-]{2,39}$")),
    rationale: z.string().min(1).max(1000).regex(new RegExp("\\S")),
    confirm_internal_decision: z.boolean(),
  })
  .strict();
export type ApprovalRequest = z.infer<typeof ApprovalRequestSchema>;

export const ArrivalCertificateCheckSchema = z.object({
  certificate_id: z.string(),
  arrival_date: z.iso.date(),
  status: z.enum(["valid", "expired", "missing", "unknown"]),
  valid_until: z.union([z.iso.date(), z.null()]),
  requirement_ref: z.string(),
  holding_ref: z.union([z.string(), z.null()]),
});
export type ArrivalCertificateCheck = z.infer<
  typeof ArrivalCertificateCheckSchema
>;

export const CandidateEvaluationSchema = z.object({
  supplier_id: z.string(),
  part_id: z.string(),
  offer_ref: z.string(),
  status: z.enum(["eligible", "rejected", "insufficient_data"]),
  unit_cost: z.union([z.string(), z.null()]),
  lead_days: z.union([z.number().int(), z.null()]),
  daily_capacity: z.union([z.number().int(), z.null()]),
  earliest_dispatch_date: z.union([z.iso.date(), z.null()]),
  earliest_arrival_date: z.union([z.iso.date(), z.null()]),
  booked_dispatches: z.array(
    z.record(z.string(), z.union([z.string(), z.number().int()])),
  ),
  certificate_checks: z.array(ArrivalCertificateCheckSchema),
  reason_codes: z.array(z.string()),
});
export type CandidateEvaluation = z.infer<typeof CandidateEvaluationSchema>;

export const DataIssueSchema = z.object({
  entity_id: z.string(),
  code: z.string(),
  detail: z.string(),
});
export type DataIssue = z.infer<typeof DataIssueSchema>;

export const ReceiptSchema = z.object({
  id: z.string(),
  supplier_id: z.union([z.string(), z.null()]).optional(),
  part_id: z.string(),
  quantity: z.number().int(),
  dispatch_date: z.union([z.iso.date(), z.null()]).optional(),
  arrival_date: z.iso.date(),
  original_arrival_date: z.union([z.iso.date(), z.null()]).optional(),
  kind: z.enum(["initial_stock", "planned", "proposed"]),
  reason_codes: z.array(z.string()).optional(),
  evidence_refs: z.array(z.string()),
  unit_cost: z.union([z.string(), z.null()]).optional(),
  estimated_additional_procurement_cost: z.string().default("0.00"),
  certificate_checks: z.array(ArrivalCertificateCheckSchema).optional(),
});
export type Receipt = z.infer<typeof ReceiptSchema>;

export const DecisionPreviewSchema = z
  .object({
    scenario_id: z.string().regex(new RegExp("^SC-[a-f0-9]{20}$")),
    operational_fingerprint: z.string().regex(new RegExp("^[a-f0-9]{64}$")),
    scenario: ScenarioRequestSchema,
    mitigation_plan_id: z
      .string()
      .regex(
        new RegExp(
          "^(cost_first|lead_first|no_procurement|supplier:S-[0-9]{2,5})$",
        ),
      ),
    plan_revision: z.string().regex(new RegExp("^[a-f0-9]{64}$")),
    selected_suppliers: z.array(z.string()),
    restored_orders: z.array(z.string()),
    proposed_shipments: z.array(ReceiptSchema),
    estimated_additional_procurement_cost: z.string(),
    evidence_refs: z.array(z.string()),
    limitations: z.array(z.string()),
    engine_version: z.string(),
    action: z
      .literal("internal_decision_only")
      .default("internal_decision_only"),
  })
  .strict();
export type DecisionPreview = z.infer<typeof DecisionPreviewSchema>;

export const DecisionRecordSchema = z
  .object({
    decision_id: z.string().regex(new RegExp("^D-[a-f0-9]{24}$")),
    status: z.literal("APPROVED_INTERNAL"),
    created_at: z.string(),
    operator_id: z.string(),
    rationale: z.string(),
    evidence_ref: z.string().regex(new RegExp("^[A-Za-z0-9:_-]{1,180}$")),
    preview: DecisionPreviewSchema,
  })
  .strict();
export type DecisionRecord = z.infer<typeof DecisionRecordSchema>;

export const ErrorDetailSchema = z.object({
  code: z.string(),
  message: z.string(),
});
export type ErrorDetail = z.infer<typeof ErrorDetailSchema>;

export const ErrorResponseSchema = z.object({ error: ErrorDetailSchema });
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

export const EvidencePathSchema = z.object({
  nodes: z.array(EvidenceNodeSchema),
  relationships: z.array(EvidenceRelationshipSchema),
  human_readable: z.string(),
});
export type EvidencePath = z.infer<typeof EvidencePathSchema>;

export const GraphSummarySchema = z.object({
  graph: z.string(),
  node_count: z.number().int().min(0),
  relationship_count: z.number().int().min(0),
  nodes_by_label: z.record(z.string(), z.number().int()),
  relationships_by_type: z.record(z.string(), z.number().int()),
});
export type GraphSummary = z.infer<typeof GraphSummarySchema>;

export const ValidationErrorSchema = z.object({
  loc: z.array(z.union([z.string(), z.number().int()])),
  msg: z.string(),
  type: z.string(),
  input: z.json().optional(),
  ctx: z.record(z.string(), z.json()).optional(),
});
export type ValidationError = z.infer<typeof ValidationErrorSchema>;

export const HTTPValidationErrorSchema = z.object({
  detail: z.array(ValidationErrorSchema).optional(),
});
export type HTTPValidationError = z.infer<typeof HTTPValidationErrorSchema>;

export const HealthResponseSchema = z.object({
  status: z.enum(["ready", "unavailable"]),
  database: z.enum(["ready", "unavailable"]),
  graph: z.string(),
  graph_exists: z.union([z.boolean(), z.null()]),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

export const ImpactPathSchema = z.object({
  supplier_id: z.string(),
  part_id: z.string(),
  product_id: z.string(),
  order_id: z.string(),
  order_deadline: z.iso.date(),
  order_quantity: z.number().int().gt(0),
  units_per_product: z.number().int().gt(0),
  part_units_required: z.number().int().gt(0),
  evidence: EvidencePathSchema,
});
export type ImpactPath = z.infer<typeof ImpactPathSchema>;

export const ImpactResponseSchema = z.object({
  supplier_id: z.string(),
  analysis_type: z.literal("dependency_only").default("dependency_only"),
  interpretation: z
    .string()
    .default(
      "Open orders connected to this primary supplier. Dependency reachability does not predict lateness; stock allocation, outage duration and arrival dates are not evaluated.",
    ),
  order_ids: z.array(z.string()),
  paths: z.array(ImpactPathSchema),
});
export type ImpactResponse = z.infer<typeof ImpactResponseSchema>;

export const LotBalanceSchema = z.object({
  receipt_id: z.string(),
  part_id: z.string(),
  arrival_date: z.iso.date(),
  received_quantity: z.number().int(),
  allocated_quantity: z.number().int(),
  remaining_quantity: z.number().int(),
});
export type LotBalance = z.infer<typeof LotBalanceSchema>;

export const MaterialLineSchema = z.object({
  product_id: z.string(),
  product_quantity: z.number().int(),
  units_per_product: z.number().int(),
  quantity: z.number().int(),
  evidence: EvidencePathSchema,
});
export type MaterialLine = z.infer<typeof MaterialLineSchema>;

export const PendingReceiptSchema = z.object({
  receipt_id: z.string(),
  quantity: z.number().int(),
  arrival_date: z.iso.date(),
  evidence_refs: z.array(z.string()),
});
export type PendingReceipt = z.infer<typeof PendingReceiptSchema>;

export const MaterialResultSchema = z.object({
  part_id: z.string(),
  required_quantity: z.number().int(),
  available_by_deadline: z.union([z.number().int(), z.null()]),
  allocated_quantity: z.number().int(),
  shortfall_quantity: z.union([z.number().int(), z.null()]),
  allocations: z.array(AllocationSchema),
  late_receipts: z.array(PendingReceiptSchema),
  reason_codes: z.array(z.string()),
});
export type MaterialResult = z.infer<typeof MaterialResultSchema>;

export const MitigationPlanSummarySchema = z.object({
  id: z.string(),
  restored_orders: z.array(z.string()),
  additional_units: z.number().int(),
  unused_additional_units: z.number().int(),
  estimated_additional_procurement_cost: z.string(),
  selected: z.boolean().default(false),
  reason_codes: z.array(z.string()),
});
export type MitigationPlanSummary = z.infer<typeof MitigationPlanSummarySchema>;

export const PartDemandSchema = z.object({
  part_id: z.string(),
  quantity: z.number().int(),
  lines: z.array(MaterialLineSchema),
});
export type PartDemand = z.infer<typeof PartDemandSchema>;

export const OrderDemandSchema = z.object({
  order_id: z.string(),
  deadline: z.union([z.iso.date(), z.null()]),
  priority: z.union([z.number().int(), z.null()]),
  parts: z.array(PartDemandSchema),
  issues: z.array(z.string()).optional(),
});
export type OrderDemand = z.infer<typeof OrderDemandSchema>;

export const OrderResultSchema = z.object({
  order_id: z.string(),
  deadline: z.union([z.iso.date(), z.null()]),
  priority: z.union([z.number().int(), z.null()]),
  status: z.enum(["on_time", "at_risk", "insufficient_data"]),
  materials: z.array(MaterialResultSchema),
  latest_arriving_input: z.union([z.iso.date(), z.null()]),
  reason_codes: z.array(z.string()),
});
export type OrderResult = z.infer<typeof OrderResultSchema>;

export const PlanResultSchema = z.object({
  name: z.string(),
  on_time_orders: z.array(z.string()),
  at_risk_orders: z.array(z.string()),
  unresolved_orders: z.array(z.string()),
  orders: z.array(OrderResultSchema),
  receipts: z.array(ReceiptSchema),
  ledger: z.array(LotBalanceSchema),
  estimated_additional_procurement_cost: z.string(),
});
export type PlanResult = z.infer<typeof PlanResultSchema>;

export const PrepareRequestSchema = z
  .object({
    scenario: ScenarioRequestSchema,
    mitigation_plan_id: z
      .string()
      .regex(
        new RegExp(
          "^(cost_first|lead_first|no_procurement|supplier:S-[0-9]{2,5})$",
        ),
      ),
  })
  .strict();
export type PrepareRequest = z.infer<typeof PrepareRequestSchema>;

export const ShipmentTimingSchema = z.object({
  shipment_id: z.string(),
  supplier_id: z.string(),
  part_id: z.string(),
  quantity: z.number().int(),
  status: z.enum(["PLANNED", "DISPATCHED", "CANCELLED"]),
  original_dispatch_date: z.iso.date(),
  original_arrival_date: z.iso.date(),
  dispatch_date: z.iso.date(),
  arrival_date: z.iso.date(),
  included: z.boolean(),
  reason_code: z.string(),
});
export type ShipmentTiming = z.infer<typeof ShipmentTimingSchema>;

export const ScenarioResponseSchema = z.object({
  scenario_id: z.string(),
  snapshot_fingerprint: z.string(),
  request: ScenarioRequestSchema,
  assumptions: z.array(z.string()),
  shipment_timing: z.array(ShipmentTimingSchema),
  incomplete_data: z.boolean(),
  data_issues: z.array(DataIssueSchema),
  dependent_orders: z.array(z.string()),
  dependency_paths: z.array(EvidencePathSchema),
  order_demands: z.array(OrderDemandSchema),
  baseline: PlanResultSchema,
  disrupted: PlanResultSchema,
  mitigated: z.union([PlanResultSchema, z.null()]),
  baseline_at_risk_orders: z.array(z.string()),
  disrupted_at_risk_orders: z.array(z.string()),
  newly_at_risk_orders: z.array(z.string()),
  restored_orders: z.array(z.string()),
  candidate_evaluations: z.array(CandidateEvaluationSchema),
  mitigation_plans: z.array(MitigationPlanSummarySchema),
  proposed_shipments: z.array(ReceiptSchema),
  estimated_additional_procurement_cost: z.string(),
  evidence_nodes: z.record(z.string(), EvidenceNodeSchema),
  evidence_relationships: z.record(z.string(), EvidenceRelationshipSchema),
});
export type ScenarioResponse = z.infer<typeof ScenarioResponseSchema>;
