from langgraph.graph import StateGraph, END
from app.agents.state import ReviewState
from app.agents import (
    stage_01_ingestion,
    stage_02_code_mapping,
    stage_03_architecture,
    stage_04_security,
    stage_05_scalability,
    stage_06_testing,
    stage_07_technical_debt,
    stage_08_requirements,
    stage_09_coaching,
    stage_10_prioritization,
    stage_11_synthesis,
)


def build_review_graph():
    workflow = StateGraph(ReviewState)

    workflow.add_node("ingestion", stage_01_ingestion.run)
    workflow.add_node("code_mapping", stage_02_code_mapping.run)
    workflow.add_node("architecture", stage_03_architecture.run)
    workflow.add_node("security", stage_04_security.run)
    workflow.add_node("scalability", stage_05_scalability.run)
    workflow.add_node("testing", stage_06_testing.run)
    workflow.add_node("technical_debt", stage_07_technical_debt.run)
    workflow.add_node("requirements", stage_08_requirements.run)
    workflow.add_node("coaching", stage_09_coaching.run)
    workflow.add_node("prioritization", stage_10_prioritization.run)
    workflow.add_node("synthesis", stage_11_synthesis.run)

    # Sequential pipeline (Ollama single-instance constraint)
    workflow.set_entry_point("ingestion")
    workflow.add_edge("ingestion", "code_mapping")
    workflow.add_edge("code_mapping", "architecture")
    workflow.add_edge("architecture", "security")
    workflow.add_edge("security", "scalability")
    workflow.add_edge("scalability", "testing")
    workflow.add_edge("testing", "technical_debt")
    workflow.add_edge("technical_debt", "requirements")
    workflow.add_edge("requirements", "coaching")
    workflow.add_edge("coaching", "prioritization")
    workflow.add_edge("prioritization", "synthesis")
    workflow.add_edge("synthesis", END)

    return workflow.compile()
