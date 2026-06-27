"""
WanderHUB Backend — Vehicles Router
GET  /api/vehicles/availability  — current fleet counts
POST /api/vehicles/book          — book one vehicle (decrement count)
"""

from __future__ import annotations
from typing import Any
import random

from fastapi import APIRouter, Depends, HTTPException

from database import get_db_dependency
from models.schemas import (
    VehicleAvailability,
    VehicleFleetResponse,
    VehicleBookRequest,
    VehicleBookResponse,
    DriverInfo,
)
from routers.auth import get_current_user_id

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])

MOCK_DRIVERS: dict[str, list[dict]] = {
    "motorbike": [
        {"name": "Anh Minh",  "rating": 4.9, "plate": "51F-789.01", "eta_minutes": 6},
        {"name": "Anh Tuấn",  "rating": 4.8, "plate": "51F-345.67", "eta_minutes": 4},
        {"name": "Anh Huy",   "rating": 4.7, "plate": "51F-456.78", "eta_minutes": 8},
        {"name": "Chị Mai",   "rating": 4.9, "plate": "51F-123.45", "eta_minutes": 5},
        {"name": "Anh Phúc",  "rating": 4.8, "plate": "51F-234.56", "eta_minutes": 7},
    ],
    "car7": [
        {"name": "Anh Nam",   "rating": 4.9, "plate": "51B-111.22", "eta_minutes": 8},
        {"name": "Chị Lan",   "rating": 4.8, "plate": "51B-222.33", "eta_minutes": 6},
        {"name": "Anh Phong", "rating": 4.9, "plate": "51B-333.44", "eta_minutes": 10},
        {"name": "Anh Khoa",  "rating": 4.7, "plate": "51B-444.55", "eta_minutes": 9},
    ],
}


def _get_fleet(conn: Any) -> VehicleFleetResponse:
    rows = conn.execute(
        "SELECT vehicle_type, label, total_count, available_count FROM vehicle_fleet ORDER BY id"
    ).fetchall()
    fleet = [VehicleAvailability(**dict(r)) for r in rows]
    return VehicleFleetResponse(
        fleet=fleet,
        has_wanderhub=any(v.available_count > 0 for v in fleet),
    )


@router.get("/availability", response_model=VehicleFleetResponse)
def get_availability(conn: Any = Depends(get_db_dependency)):
    return _get_fleet(conn)


@router.get("/images/{vehicle_type}")
def get_vehicle_image(vehicle_type: str, conn: Any = Depends(get_db_dependency)):
    """Get vehicle image by type"""
    row = conn.execute(
        "SELECT image_url, description, features, capacity FROM vehicle_images WHERE vehicle_type = ?",
        (vehicle_type,)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Loại xe không tìm thấy.")

    return {
        "vehicle_type": vehicle_type,
        "image_url": row["image_url"],
        "description": row["description"],
        "features": row["features"],
        "capacity": row["capacity"],
    }


@router.post("/book", response_model=VehicleBookResponse)
def book_vehicle(
    body: VehicleBookRequest,
    user_id: int | None = Depends(get_current_user_id),
    conn: Any = Depends(get_db_dependency),
):
    if body.vehicle_type not in MOCK_DRIVERS:
        raise HTTPException(status_code=400, detail="Loại xe không hợp lệ.")

    # Read current count
    fleet_row = conn.execute(
        "SELECT available_count, label FROM vehicle_fleet WHERE vehicle_type = ?",
        (body.vehicle_type,),
    ).fetchone()

    if not fleet_row or fleet_row["available_count"] <= 0:
        raise HTTPException(status_code=409, detail="Loại xe này đã hết chỗ.")

    # Atomic decrement (safe under SQLite serialisation)
    affected = conn.execute(
        """
        UPDATE vehicle_fleet
        SET available_count = available_count - 1,
            updated_at      = CURRENT_TIMESTAMP
        WHERE vehicle_type = ? AND available_count > 0
        """,
        (body.vehicle_type,),
    ).rowcount

    if affected == 0:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Xe vừa hết, vui lòng thử lại.")

    driver_data = random.choice(MOCK_DRIVERS[body.vehicle_type])

    conn.execute(
        """
        INSERT INTO vehicle_bookings
            (vehicle_type, user_id, itinerary_id, driver_name, driver_rating, plate_number, eta_minutes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.vehicle_type,
            user_id,
            body.itinerary_id,
            driver_data["name"],
            driver_data["rating"],
            driver_data["plate"],
            driver_data["eta_minutes"],
        ),
    )
    conn.commit()

    return VehicleBookResponse(
        success=True,
        driver=DriverInfo(
            name=driver_data["name"],
            rating=driver_data["rating"],
            plate=driver_data["plate"],
            eta_minutes=driver_data["eta_minutes"],
            vehicle_type=body.vehicle_type,
            vehicle_label=fleet_row["label"],
        ),
        remaining=_get_fleet(conn),
    )
