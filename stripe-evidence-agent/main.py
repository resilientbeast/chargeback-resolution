from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
import json
import stripe
from uipath.platform import UiPath

class GraphInput(BaseModel):
    charge_id: str = Field(description="The Stripe charge ID or payment intent ID")

class GraphOutput(BaseModel):
    dispute_data_json: str = Field(description="The fetched Stripe dispute details as a JSON string")
    error_type: str = Field(description="Error type if any", default="")
    error_message: str = Field(description="Error message if any", default="")

class GraphState(BaseModel):
    input_data: GraphInput
    output_data: GraphOutput | None = None

_sdk: UiPath | None = None

def sdk() -> UiPath:
    global _sdk
    if _sdk is None:
        _sdk = UiPath()
    return _sdk

def fetch_stripe_charge_node(state: GraphState) -> dict:
    dispute_data_json = ""
    error_type = ""
    error_message = ""
    
    try:
        if not state.input_data.charge_id:
            raise ValueError("charge_id is required")

        secret_key_asset = sdk().assets.retrieve_credential("Stripe_SecretKey", folder_path="Shared")
        stripe.api_key = str(secret_key_asset.value)

        kwargs = {"expand": ["data.charge", "data.payment_intent"]}
        if state.input_data.charge_id.startswith("pi_"):
            kwargs["payment_intent"] = state.input_data.charge_id
        else:
            kwargs["charge"] = state.input_data.charge_id
            
        disputes = stripe.Dispute.list(**kwargs)
        if not disputes.data:
            raise ValueError(f"No dispute found for {state.input_data.charge_id}")
        dispute = disputes.data[0]
        
        dispute_data_json = json.dumps(dispute)

    except Exception as exc:
        error_type = type(exc).__name__
        error_message = str(exc)
        
    out = GraphOutput(
        dispute_data_json=dispute_data_json,
        error_type=error_type,
        error_message=error_message
    )
    return {"output_data": out}

builder = StateGraph(GraphState, input_schema=GraphInput, output_schema=GraphOutput)
builder.add_node("fetch_stripe_charge", fetch_stripe_charge_node)
builder.add_edge(START, "fetch_stripe_charge")
builder.add_edge("fetch_stripe_charge", END)

graph = builder.compile()
