from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

class GraphInput(BaseModel):
    evidence_quality_score: float = Field(description="Evidence quality score", default=0.0)
    evidence_summary: str = Field(description="Summary of evidence", default="")

class GraphOutput(BaseModel):
    win_probability: float = Field(description="The calculated win probability", default=0.0)

class GraphState(BaseModel):
    input_data: GraphInput
    output_data: GraphOutput | None = None

def calculate_probability_node(state: GraphState) -> dict:
    win_probability = min(100.0, state.input_data.evidence_quality_score * 0.95)
    
    out = GraphOutput(
        win_probability=win_probability
    )
    return {"output_data": out}

builder = StateGraph(GraphState, input_schema=GraphInput, output_schema=GraphOutput)
builder.add_node("calculate_probability", calculate_probability_node)
builder.add_edge(START, "calculate_probability")
builder.add_edge("calculate_probability", END)

graph = builder.compile()
