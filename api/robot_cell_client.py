import asyncio
import random

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

WMS_CONFIRM_URL = "http://localhost:8081/confirmPick"


class PickRequest(BaseModel):
    pickId: int
    quantity: int


class PickConfirmation(BaseModel):
    pickId: int
    pickSuccessful: bool
    errorMessage: str | None
    itemBarcode: int


@app.post("/pick", status_code=202)
async def receive_pick(request: PickRequest):
    """Receive a pick request from WMS and process it asynchronously."""
    asyncio.create_task(_process_pick(request))
    return {"message": "Pick request received", "pickId": request.pickId}


async def _process_pick(request: PickRequest):
    """Fake the pick and send confirmation back to WMS."""
    print(f"[CELL] Processing pick {request.pickId}, quantity {request.quantity}...")

    # Simulate pick time
    await asyncio.sleep(2)

    # Fake barcode from scanner (5 random digits)
    barcode = random.randint(10000, 99999)
    pick_successful = True

    confirmation = PickConfirmation(
        pickId=request.pickId,
        pickSuccessful=pick_successful,
        errorMessage=None,
        itemBarcode=barcode,
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                WMS_CONFIRM_URL, json=confirmation.model_dump()
            )
            print(f"[CELL] Confirmation sent: {response.status_code}")
        except Exception as e:
            print(f"[CELL] Failed to send confirmation: {e}")
