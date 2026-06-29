from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
import json
import requests
from uipath.platform import UiPath

class GraphInput(BaseModel):
    order_id: str = Field(description="The WooCommerce order ID")

class GraphOutput(BaseModel):
    order_data_json: str = Field(description="The fetched WooCommerce order details as a JSON string")
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

def fetch_woo_order_node(state: GraphState) -> dict:
    order_data_json = ""
    error_type = ""
    error_message = ""
    
    try:
        if not state.input_data.order_id:
            raise ValueError("order_id is required")

        consumer_key_asset = sdk().assets.retrieve("WooCommerce_ConsumerKey", folder_path="Shared")
        consumer_secret_asset = sdk().assets.retrieve("WooCommerce_ConsumerSecret", folder_path="Shared")
        
        consumer_key = str(consumer_key_asset.value)
        consumer_secret = str(consumer_secret_asset.value)

        base_url = "https://store.0tt.uk/wp-json/wc/v3/orders"
        url = f"{base_url}/{state.input_data.order_id}"

        response = requests.get(url, auth=(consumer_key, consumer_secret), timeout=30)
        response.raise_for_status()
        
        order_data = response.json()
        order_data_json = json.dumps(order_data)

    except Exception as exc:
        error_type = type(exc).__name__
        error_message = str(exc)
        
    out = GraphOutput(
        order_data_json=order_data_json,
        error_type=error_type,
        error_message=error_message
    )
    return {"output_data": out}

builder = StateGraph(GraphState, input_schema=GraphInput, output_schema=GraphOutput)
builder.add_node("fetch_woo_order", fetch_woo_order_node)
builder.add_edge(START, "fetch_woo_order")
builder.add_edge("fetch_woo_order", END)

graph = builder.compile()
