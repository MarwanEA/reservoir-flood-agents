"""
LangGraph orchestrator for the reservoir flood-ops multi-agent pipeline.

Sequential wiring: Agent 1 (Perception & Data-QA) -> Agent 2 (Inflow
Forecasting) -> Agent 3 (Reservoir Routing & Scenario Simulation) ->
Agent 4 (Downstream Risk & Impact) -> Agent 5 (Regulatory & Constraints)
-> Agent 6 (Decision Synthesis). Agents 3-5 are rule-based; only Agent 6
calls an LLM (Claude Code headless, see agents/agent6_synthesis.py).

If Agent 1's QA fails (n_errors > 0), the graph short-circuits straight to
END - no downstream agent should run against data that failed validation.
"""
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agents import (
    agent1_perception,
    agent2_forecasting,
    agent3_routing,
    agent4_downstream_risk,
    agent5_regulatory,
    agent6_synthesis,
)


class PipelineState(TypedDict, total=False):
    forecast_df: Any
    observed_df: Any
    dam_params: dict
    dgm_bulletins: dict
    qa_report: dict
    inflow_df: Any
    routing_results: dict
    risk_df: Any
    risk_first_flags: dict
    regulatory_df: Any
    synthesis: dict


def _node1(state: PipelineState) -> PipelineState:
    return agent1_perception.run(dict(state))


def _node2(state: PipelineState) -> PipelineState:
    return agent2_forecasting.run(dict(state))


def _node3(state: PipelineState) -> PipelineState:
    return agent3_routing.run(dict(state))


def _node4(state: PipelineState) -> PipelineState:
    return agent4_downstream_risk.run(dict(state))


def _node5(state: PipelineState) -> PipelineState:
    return agent5_regulatory.run(dict(state))


def _node6(state: PipelineState) -> PipelineState:
    return agent6_synthesis.run(dict(state))


def _qa_gate(state: PipelineState) -> str:
    if state["qa_report"]["passed"]:
        return "continue"
    print("[Orchestrator] Agent 1 QA FAILED - halting pipeline before Agent 2. "
          "See qa_report.issues for details.")
    return "halt"


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("agent1_perception", _node1)
    graph.add_node("agent2_forecasting", _node2)
    graph.add_node("agent3_routing", _node3)
    graph.add_node("agent4_downstream_risk", _node4)
    graph.add_node("agent5_regulatory", _node5)
    graph.add_node("agent6_synthesis", _node6)

    graph.set_entry_point("agent1_perception")
    graph.add_conditional_edges("agent1_perception", _qa_gate, {"continue": "agent2_forecasting", "halt": END})
    graph.add_edge("agent2_forecasting", "agent3_routing")
    graph.add_edge("agent3_routing", "agent4_downstream_risk")
    graph.add_edge("agent4_downstream_risk", "agent5_regulatory")
    graph.add_edge("agent5_regulatory", "agent6_synthesis")
    graph.add_edge("agent6_synthesis", END)

    return graph.compile()


def run_pipeline() -> PipelineState:
    app = build_graph()
    final_state = app.invoke({}, config={"recursion_limit": 25})
    return final_state


if __name__ == "__main__":
    run_pipeline()
