import asyncio
import inspect
import os
import sys
from typing import TypedDict

from dotenv import load_dotenv

from langsmith import Client, get_current_run_tree, traceable
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END

# Load environment variables (e.g. LANGSMITH_API_KEY from .env)
# As noted in D03 review: .env is an ephemeral fallback for local proving.
# All live deployments will graduate to Azure Key Vault secrets for D12.
load_dotenv()

# We need LANGSMITH_API_KEY explicitly to prove this maps to a real backend per D03
if not os.environ.get("LANGSMITH_API_KEY"):
    print("ERROR: LANGSMITH_API_KEY is not set.")
    print("D03 requires a live trace. Please set your LangSmith key as a temporary environment variable or in a .env file.")
    sys.exit(1)

# Ensure tracing is forced on
os.environ["LANGSMITH_TRACING"] = "true"

TOKEN_USAGE = {
    "input_tokens": 120,
    "output_tokens": 45,
    "total_tokens": 165,
}
LANGSMITH_CLIENT = Client()


def flush_langsmith_traces() -> None:
    """Block until buffered trace operations are submitted before process exit."""
    flush = getattr(LANGSMITH_CLIENT, "flush", None)
    if flush is None:
        return

    flush_result = flush()
    if inspect.isawaitable(flush_result):
        asyncio.run(flush_result)


class OrchestratorState(TypedDict):
    supplier_id: str
    risk_level: str
    tokens_used: int

# 1. Mock Retrieval Span
@traceable(
    client=LANGSMITH_CLIENT,
    name="retrieval.reach_kb",
    run_type="retriever",
    tags=["azure-ai-search"],
)
def search_reach_knowledge_base(supplier_id: str) -> str:
    """Simulates querying a vector database for REACH documents."""
    return f"REACH compliance verified for supplier {supplier_id}"

# 2. Mock Tool Span
@traceable(
    client=LANGSMITH_CLIENT,
    name="tool.lookup_export_control",
    run_type="tool",
    tags=["erp-simulation"],
)
def check_export_controls(supplier_id: str) -> str:
    """Simulates an explicit tool call for export checks."""
    return "Export controls cleared: HS Code 8471"

# 3. Graph Node containing Model / GenAI augmentations
@traceable(client=LANGSMITH_CLIENT, name="node.risk_classifier")
def risk_classifier_node(state: OrchestratorState) -> OrchestratorState:
    supplier_id = state["supplier_id"]

    # Trigger sub-spans physically mapping to the D03 taxonomy
    reach_text = search_reach_knowledge_base(supplier_id)
    export_text = check_export_controls(supplier_id)

    # 4. Mock Model Call with GenAI augmentation metadata
    @traceable(
        client=LANGSMITH_CLIENT,
        name="model.gpt-4o.reach_evaluation",
        run_type="llm",
        tags=["azure-openai", "compliance-bot"],
        metadata={
            "gen_ai.system": "azure-openai",
            "ls_provider": "openai",
            "ls_model_name": "gpt-4o",
        },
    )
    def mock_llm_eval(text1: str, text2: str) -> str:
        # Attach token usage to the current run so LangSmith aggregates usage and cost fields.
        current_run = get_current_run_tree()
        if current_run is not None:
            current_run.set(usage_metadata=TOKEN_USAGE)
        return "elevated"

    decision = mock_llm_eval(reach_text, export_text)

    return {
        "supplier_id": supplier_id,
        "risk_level": decision,
        "tokens_used": state.get("tokens_used", 0) + TOKEN_USAGE["total_tokens"],
    }

# Build Local Graph
graph = StateGraph(OrchestratorState)
graph.add_node("classify", risk_classifier_node)
graph.add_edge(START, "classify")
graph.add_edge("classify", END)

# D03 uses an in-memory checkpointer for local proof. Production should use a durable saver.
app = graph.compile(checkpointer=InMemorySaver())

if __name__ == "__main__":
    print(f"Executing LangGraph Hello World to LangSmith project: {os.environ.get('LANGSMITH_PROJECT', 'default')}")

    # Run graph with configuration mapped to D03 taxonomy
    # Thread ID now points at a real checkpoint namespace for this local sample.
    invoke_config = {
        "configurable": {"thread_id": "req-qual-9912"},
        "run_name": "meridian-compliance-qualification-chain",
        "tags": ["d03-telemetry-validation", "dev-test"],
    }

    try:
        result = app.invoke(
            {"supplier_id": "SUPP-001", "risk_level": "unknown", "tokens_used": 0},
            config=invoke_config,
        )
    finally:
        flush_langsmith_traces()

    print("\nGraph Execution Complete.")
    print(f"State Result: {result}")
    print(
        "\nTrace has been flushed to LangSmith. Please verify the "
        "`usage_metadata.input_tokens`, `usage_metadata.output_tokens`, and nested span taxonomy visually."
    )
