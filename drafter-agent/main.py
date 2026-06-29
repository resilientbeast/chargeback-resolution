from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from uipath_langchain.chat.models import UiPathAzureChatOpenAI

class GraphInput(BaseModel):
    woo_order_json: str = Field(description="WooCommerce order details JSON")
    stripe_dispute_json: str = Field(description="Stripe dispute details JSON")
    evidence_quality_score: float = Field(description="Score from 1-100")
    evidence_summary: str = Field(description="Summary of evidence")
    strategy_recommendation: str = Field(description="The recommended dispute strategy")

class GraphOutput(BaseModel):
    rebuttal_draft: str = Field(description="The drafted response for the bank/Stripe")

class GraphState(BaseModel):
    input_data: GraphInput
    output_data: GraphOutput | None = None

async def draft_response(state: GraphState) -> dict:
    llm = UiPathAzureChatOpenAI(
        model="gpt-4o-2024-11-20",
        temperature=0.7
    )
    
    prompt = f"""
    You are an expert Chargeback Dispute Responder.
    Draft a formal, professional rebuttal letter to the bank to fight this chargeback.
    Use the provided strategy and evidence to construct a compelling argument.
    
    WooCommerce Order: {state.input_data.woo_order_json}
    Stripe Dispute: {state.input_data.stripe_dispute_json}
    Evidence Score: {state.input_data.evidence_quality_score}
    Evidence Summary: {state.input_data.evidence_summary}
    Strategy: {state.input_data.strategy_recommendation}
    
    Write the letter ready to be submitted to Stripe/Bank. Keep it clear, concise, and assertive but polite.
    """
    
    # We use structured output to enforce the GraphOutput schema
    structured_llm = llm.with_structured_output(GraphOutput)
    result = await structured_llm.ainvoke(prompt)
    
    return {"output_data": result}

builder = StateGraph(GraphState, input_schema=GraphInput, output_schema=GraphOutput)
builder.add_node("draft_response", draft_response)
builder.add_edge(START, "draft_response")
builder.add_edge("draft_response", END)

graph = builder.compile()
