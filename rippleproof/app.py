"""Graph analysis, bounded agent and authenticated internal-decision API."""

import logging
from typing import Annotated

from fastapi import FastAPI, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import field_validator

from rippleproof import __version__
from rippleproof.agent import AgentCoordinator
from rippleproof.agent_models import AgentCapabilities, AgentRequest, AgentResponse, capabilities
from rippleproof.config import Phase3Settings, Settings
from rippleproof.decisions import (
    ApprovalRequest,
    DecisionPreview,
    DecisionRecord,
    DecisionService,
    PrepareRequest,
)
from rippleproof.errors import DatabaseUnavailable, EntityNotFound, GraphQueryError, OperationError
from rippleproof.models import (
    AlternativesQuery,
    AlternativesResponse,
    ErrorDetail,
    ErrorResponse,
    GraphSummary,
    HealthResponse,
    ImpactQuery,
    ImpactResponse,
)
from rippleproof.repository import GraphRepository
from rippleproof.service import GraphService
from rippleproof.simulation.engine import simulate
from rippleproof.simulation.models import ScenarioRequest, ScenarioResponse
from rippleproof.simulation.snapshot import normalize
from rippleproof.tool_models import DecisionId, HistoryInput
from rippleproof.tools import history_item

logger = logging.getLogger(__name__)


class DecisionHistoryQuery(HistoryInput):
    """HTTP query strings carry digits, while MCP inputs remain strict JSON ints."""

    @field_validator("offset", "limit", mode="before")
    @classmethod
    def query_integer(cls, value):
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            return int(value)
        return value


ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Operator approval token rejected"},
    404: {"model": ErrorResponse, "description": "Graph entity does not exist"},
    409: {"model": ErrorResponse, "description": "Stale preview or conflicting replay"},
    500: {"model": ErrorResponse, "description": "Graph command or evidence failure"},
    503: {"model": ErrorResponse, "description": "Database or required configuration unavailable"},
}


def error_response(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status, content=body.model_dump())


def create_app(
    settings: Settings | None = None, phase3: Phase3Settings | None = None, *, provider=None
) -> FastAPI:
    settings = settings or Settings()
    repository = GraphRepository(settings)
    service = GraphService(repository)
    phase3 = phase3 or Phase3Settings()
    decisions = DecisionService(repository, phase3)
    app = FastAPI(
        title="RippleProof AI",
        version=__version__,
        description=(
            "Graph Hacks 2026 · Track 1 · Graph evidence and deterministic material simulation."
        ),
    )
    app.state.phase3_settings = phase3

    @app.exception_handler(OperationError)
    async def operation_error(request: Request, exc: OperationError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(DatabaseUnavailable)
    async def database_unavailable(request: Request, exc: DatabaseUnavailable) -> JSONResponse:
        logger.warning("FalkorDB unavailable for %s: %s", request.url.path, exc.__cause__)
        return error_response(
            503, "database_unavailable", "FalkorDB is unavailable. Try again later."
        )

    @app.exception_handler(GraphQueryError)
    async def graph_query_error(request: Request, exc: GraphQueryError) -> JSONResponse:
        logger.error("Graph failure for %s", request.url.path, exc_info=exc)
        return error_response(
            500, "graph_query_failed", "A graph command or evidence check failed."
        )

    @app.exception_handler(EntityNotFound)
    async def entity_not_found(request: Request, exc: EntityNotFound) -> JSONResponse:
        return error_response(404, "entity_not_found", str(exc))

    @app.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
    def health(response: Response) -> HealthResponse:
        try:
            exists = repository.ready()
        except (DatabaseUnavailable, GraphQueryError) as exc:
            logger.warning("FalkorDB readiness failed: %s", exc.__cause__)
            response.status_code = 503
            return HealthResponse(
                status="unavailable",
                database="unavailable",
                graph=settings.graph,
                graph_exists=None,
            )
        return HealthResponse(
            status="ready", database="ready", graph=settings.graph, graph_exists=exists
        )

    @app.get("/api/graph/summary", response_model=GraphSummary, responses=ERROR_RESPONSES)
    def graph_summary() -> GraphSummary:
        return repository.summary()

    @app.get("/api/impact-paths", response_model=ImpactResponse, responses=ERROR_RESPONSES)
    def impact_paths(query: Annotated[ImpactQuery, Query()]) -> ImpactResponse:
        return service.impact(query.supplier_id)

    @app.get("/api/alternatives", response_model=AlternativesResponse, responses=ERROR_RESPONSES)
    def alternatives(query: Annotated[AlternativesQuery, Query()]) -> AlternativesResponse:
        return service.alternatives(query.part_id, query.as_of)

    @app.post("/api/scenarios/simulate", response_model=ScenarioResponse, responses=ERROR_RESPONSES)
    def simulate_scenario(scenario: ScenarioRequest) -> ScenarioResponse:
        nodes, edges = repository.snapshot_facts(scenario.supplier_id)
        return simulate(normalize(nodes, edges), scenario)

    @app.get("/api/agent/capabilities", response_model=AgentCapabilities)
    def agent_capabilities(response: Response) -> AgentCapabilities:
        response.headers["Cache-Control"] = "no-store"
        return capabilities(phase3, controlled_provider=provider is not None)

    @app.post("/api/agent/run", response_model=AgentResponse, responses=ERROR_RESPONSES)
    async def agent_run(body: AgentRequest, response: Response) -> AgentResponse:
        result = await AgentCoordinator(settings, phase3, provider).run(body)
        response.status_code = result.http_status
        return result

    @app.post("/api/decisions/prepare", response_model=DecisionPreview, responses=ERROR_RESPONSES)
    def prepare_decision(body: PrepareRequest) -> DecisionPreview:
        return decisions.prepare(body)

    @app.post("/api/decisions/approve", response_model=DecisionRecord, responses=ERROR_RESPONSES)
    def approve_decision(
        body: ApprovalRequest, authorization: Annotated[str | None, Header(max_length=300)] = None
    ) -> DecisionRecord:
        return decisions.approve(body, authorization)

    @app.get(
        "/api/decisions/{decision_id}", response_model=DecisionRecord, responses=ERROR_RESPONSES
    )
    def get_decision(decision_id: DecisionId) -> DecisionRecord:
        return decisions.get(decision_id)

    @app.get("/api/decisions", responses=ERROR_RESPONSES)
    def get_decisions(query: Annotated[DecisionHistoryQuery, Query()]):
        total, rows = repository.decision_history(query.scenario_id, query.offset, query.limit)
        return {
            "total": total,
            "offset": query.offset,
            "items": [history_item(p) for p in rows],
            "next_offset": query.offset + len(rows) if query.offset + len(rows) < total else None,
        }

    return app


app = create_app()
