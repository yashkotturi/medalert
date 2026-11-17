"""Request/response shapes (Pydantic).

Why? FastAPI uses these to validate input automatically. Bad input gets a
clear 422 error instead of corrupting the database.
"""

from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["P1", "P2", "P3", "P4"]
Status = Literal["open", "in_progress", "resolved"]


class Ward(BaseModel):
    id: int
    name: str
    total_beds: int
    occupied_beds: int
    free_beds: int
    occupancy_pct: float
    near_full: bool


class WardUpdate(BaseModel):
    occupied_beds: int = Field(ge=0, description="New number of occupied beds")


class Medicine(BaseModel):
    id: int
    name: str
    quantity: int
    min_quantity: int
    unit: str
    low_stock: bool


class StockUpdate(BaseModel):
    # Positive = restock, negative = dispensed.
    change: int = Field(description="Amount to add (positive) or remove (negative)")


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    priority: Priority
    details: str = Field(default="", max_length=4000)


class IncidentUpdate(BaseModel):
    status: Status


class Incident(BaseModel):
    id: int
    title: str
    priority: Priority
    details: str
    status: Status
    created_at: str
    updated_at: str
