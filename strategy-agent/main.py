from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from uipath_langchain.chat.models import UiPathAzureChatOpenAI

class GraphInput(BaseModel):
    woo_order_json: str = Field(description="WooCommerce order details JSON")
    stripe_dispute_json: str = Field(description="Stripe dispute details JSON")
    evidence_quality_score: float = Field(description="Score from 1-100")
    evidence_summary: str = Field(description="Summary of evidence")

class GraphOutput(BaseModel):
    strategy_recommendation: str = Field(description="The recommended dispute strategy")
    confidence_level: str = Field(description="Confidence level: High, Medium, or Low")
    requires_human_review: bool = Field(description="True if human review is needed")

class GraphState(BaseModel):
    input_data: GraphInput
    output_data: GraphOutput | None = None

async def determine_strategy(state: GraphState) -> dict:
    llm = UiPathAzureChatOpenAI(
        model="gpt-4o-2024-11-20",
        temperature=0.0
    )
    
    prompt = f"""
    You are a Chargeback Dispute Strategist.
    Analyze the following data and determine the best defense strategy for a chargeback.
    
    WooCommerce Order: {state.input_data.woo_order_json}
    Stripe Dispute: {state.input_data.stripe_dispute_json}
    Evidence Score: {state.input_data.evidence_quality_score}
    Evidence Summary: {state.input_data.evidence_summary}
    
    If the score is below 50, recommend accepting the chargeback.
    If the score is 50 or above, recommend fighting it and detail the strategy.
    Set requires_human_review to true if confidence is Low or Medium.
    """
    
    structured_llm = llm.with_structured_output(GraphOutput)
    result = await structured_llm.ainvoke(prompt)
    
    return {"output_data": result}

builder = StateGraph(GraphState, input_schema=GraphInput, output_schema=GraphOutput)
builder.add_node("determine_strategy", determine_strategy)
builder.add_edge(START, "determine_strategy")
builder.add_edge("determine_strategy", END)

graph = builder.compile()
