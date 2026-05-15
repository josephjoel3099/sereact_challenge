import asyncio

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

ROBOT_CELL_URL = "http://localhost:8080/pick"


class PickRequest(BaseModel):
    pickId: int
    quantity: int


class PickConfirmation(BaseModel):
    pickId: int
    pickSuccessful: bool
    errorMessage: str | None
    itemBarcode: int


@app.post("/pick", status_code=202)
async def send_pick(request: PickRequest):
    """Send a pick request to the robot cell asynchronously."""
    asyncio.create_task(_dispatch_pick(request))
    return {"message": "Pick request dispatched", "pickId": request.pickId}


async def _dispatch_pick(request: PickRequest):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(ROBOT_CELL_URL, json=request.model_dump())
            print(f"[WMS] Pick request sent: {response.status_code}")
        except Exception as e:
            print(f"[WMS] Failed to send pick request: {e}")


@app.post("/confirmPick")
async def confirm_pick(confirmation: PickConfirmation):
    """Receive pick confirmation from the robot cell."""
    print(f"[WMS] Pick confirmation received: {confirmation.model_dump()}")
    return {"message": "Confirmation received"}

@app.get("/health")
def health():
    return {"status": "ok"}
