# Research: MVP UW Course Search Implementation (LangGraph)

## Decision: Use Python + LangGraph as the agent orchestration layer

**Rationale**: The project now follows the `TradingAgents` multi-agent LangGraph framework as its reference architecture. LangGraph's `StateGraph`, conditional routing, structured outputs, and `SqliteSaver` checkpointer map directly to the constitution's "Persistent and Explicit Workflow State" principle and to a testable, inspectable agent pipeline.

**Alternatives considered**:

- TypeScript + Fastify + custom retrieval service (earlier plan): simpler for a pure search service, but it lacks native agentic orchestration and resumable checkpoint state.
- LangChain `AgentExecutor`: simpler, but less control over graph shape, routing, and checkpointing than a hand-built `StateGraph`.

## Decision: Grounded answer synthesis only

**Rationale**: The constitution mandates source-grounded accuracy. The LLM is used for query understanding and for composing answers strictly from retrieved, cited facts; it must never generate course facts from parametric memory. For the implemented contract and verification limits, see [README: Optional model mode](../../README.md#optional-model-mode).

**Alternatives considered**:

- Free-form LLM answering with retrieval augmentation: faster to build, but risks hallucinated prerequisites, credits, or availability.
- No LLM at all (template answers): safest, but cannot satisfy scoped natural-language course discovery.

## Decision: DeepSeek as the default LLM provider

**Rationale**: User-selected provider. DeepSeek exposes an OpenAI-compatible endpoint, which `langchain-openai` can consume with a custom `base_url`. A tiered client factory keeps `deep` (answer synthesis) and `quick` (query understanding) models separately configurable, matching TradingAgents.

**Alternatives considered**:

- OpenAI, Anthropic, Gemini: supported through the same provider factory for later swaps.

## Decision: Deterministic retrieval nodes over SQLite/FTS5

**Rationale**: Course search retrieval is structured lookup (exact code, department, keyword, natural-language FTS) over approved snapshots — not a reasoning task. Deterministic Python functions are more testable and reproducible than LLM tool-calling loops for v1.

**Alternatives considered**:

- LangChain tool-calling retrieval loops (as in TradingAgents analysts): useful if retrieval becomes multi-step/discoverable, but unnecessary overhead for v1.

## Decision: `SqliteSaver` checkpointer per `workflow_id`

**Rationale**: LangGraph's SQLite checkpointer persists the full graph state, giving resumable and inspectable workflow state. A deterministic `thread_id` derived from the `workflow_id` (and query signature) prevents cross-run state contamination, mirroring TradingAgents' per-ticker checkpointer.

**Alternatives considered**:

- In-memory state: violates persistence requirements.
- Custom state store: redundant with LangGraph's built-in checkpointer.

## Decision: Explicit source registry as the ingestion allowlist

**Rationale**: `config/sources.yml` records approved sources, tiers, URL patterns, extraction policies, and freshness requirements. This prevents accidental broad crawling and keeps source coverage testable, matching TradingAgents' explicit vendor routing.

**Alternatives considered**:

- Hard-coded URLs in ingestion code: less transparent.
- Dynamic UW-domain crawling: too broad for v1.

## Decision: Strict department-page promotion policy

**Rationale**: Catalog/course-description sources own normalized facts. Department pages improve discovery and context but can only populate normalized facts when clearly structured and directly cited. This reduces extraction errors and source conflicts.

**Alternatives considered**:

- Department pages as equal fact sources: higher recall, greater conflict/parsing risk.
- Department pages never used for facts: safest but may miss structured department evidence.

## Decision: FastAPI + Typer CLI + static Web UI

**Rationale**: FastAPI serves the agent and static web UI in one process; Typer provides the manual ingestion/search CLI, mirroring TradingAgents' CLI. This keeps v1 deployable as a single Python service.

**Alternatives considered**:

- Separate frontend build (React/Vite): heavier; a simple static UI meets the "simple Web UI" requirement.
