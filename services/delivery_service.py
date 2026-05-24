"""
Delivery Service — CRUD, import/export, validation
"""

import csv
import json
import uuid
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from rich.console import Console
from models import get_session, Delivery, DistanceCache
from algorithms.genetic_algorithm import haversine
import numpy as np

console = Console()


def _generate_delivery_id() -> str:
    return "DLV-" + uuid.uuid4().hex[:8].upper()


def _validate_contact(contact: str) -> bool:
    return bool(re.match(r"^[\d\s\+\-\(\)]{7,20}$", contact)) if contact else True


def add_delivery(
    customer_name: str,
    address: str,
    contact_number: str = "",
    notes: str = "",
    latitude: float = None,
    longitude: float = None,
    user_id: int = None,
) -> Tuple[bool, str, Optional[Delivery]]:
    """
    Add a single delivery record.

    Returns:
        (success, message, delivery_object)
    """
    if not customer_name.strip():
        return False, "Customer name is required.", None
    if not address.strip():
        return False, "Address is required.", None

    session = get_session()
    try:
        # Duplicate check by address
        existing = session.query(Delivery).filter(
            Delivery.address == address.strip(),
            Delivery.is_active == True,
        ).first()
        if existing:
            return False, f"Address already exists (ID: {existing.delivery_id}).", None

        is_geocoded = False
        if latitude is not None and longitude is not None:
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                is_geocoded = True

        delivery = Delivery(
            delivery_id=_generate_delivery_id(),
            customer_name=customer_name.strip(),
            address=address.strip(),
            contact_number=contact_number.strip(),
            notes=notes.strip(),
            latitude=latitude,
            longitude=longitude,
            is_geocoded=is_geocoded,
            user_id=user_id,
        )
        session.add(delivery)
        session.commit()
        session.refresh(delivery)
        console.print(f"[green]✓ Added: {delivery.delivery_id} — {customer_name}[/green]")
        return True, "Delivery added successfully.", delivery
    except Exception as e:
        session.rollback()
        return False, f"Database error: {e}", None
    finally:
        session.close()


def update_delivery(
    delivery_id: str,
    **kwargs,
) -> Tuple[bool, str]:
    session = get_session()
    try:
        delivery = session.query(Delivery).filter_by(delivery_id=delivery_id).first()
        if not delivery:
            return False, "Delivery not found."
        for key, value in kwargs.items():
            if hasattr(delivery, key):
                setattr(delivery, key, value)
        delivery.updated_at = datetime.utcnow()
        session.commit()
        return True, "Delivery updated."
    except Exception as e:
        session.rollback()
        return False, f"Error: {e}"
    finally:
        session.close()


def delete_delivery(delivery_id: str) -> Tuple[bool, str]:
    session = get_session()
    try:
        delivery = session.query(Delivery).filter_by(delivery_id=delivery_id).first()
        if not delivery:
            return False, "Delivery not found."
        delivery.is_active = False
        session.commit()
        return True, "Delivery deleted."
    except Exception as e:
        session.rollback()
        return False, f"Error: {e}"
    finally:
        session.close()


def get_all_deliveries(user_id: int = None, geocoded_only: bool = False) -> List[Delivery]:
    session = get_session()
    try:
        q = session.query(Delivery).filter(Delivery.is_active == True)
        if user_id:
            q = q.filter(Delivery.user_id == user_id)
        if geocoded_only:
            q = q.filter(Delivery.is_geocoded == True)
        results = q.order_by(Delivery.created_at.desc()).all()
        session.expunge_all()
        return results
    finally:
        session.close()


def search_deliveries(query: str) -> List[Delivery]:
    session = get_session()
    try:
        q = "%" + query.lower() + "%"
        results = session.query(Delivery).filter(
            Delivery.is_active == True,
        ).filter(
            (Delivery.customer_name.ilike(q)) |
            (Delivery.address.ilike(q)) |
            (Delivery.delivery_id.ilike(q))
        ).all()
        session.expunge_all()
        return results
    finally:
        session.close()


def import_csv(filepath: str, user_id: int = None) -> Tuple[int, int, List[str]]:
    """
    Import deliveries from CSV file.
    Expected columns: customer_name, address, contact_number (optional), notes (optional)

    Returns:
        (success_count, failure_count, error_messages)
    """
    success = 0
    failure = 0
    errors = []

    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 2):
                name = row.get("customer_name", row.get("name", "")).strip()
                addr = row.get("address", "").strip()
                contact = row.get("contact_number", row.get("contact", "")).strip()
                notes = row.get("notes", "").strip()
                lat = row.get("latitude", "").strip()
                lon = row.get("longitude", "").strip()

                try:
                    lat_f = float(lat) if lat else None
                    lon_f = float(lon) if lon else None
                except ValueError:
                    lat_f = lon_f = None

                ok, msg, _ = add_delivery(name, addr, contact, notes, lat_f, lon_f, user_id)
                if ok:
                    success += 1
                else:
                    failure += 1
                    errors.append(f"Row {row_num}: {msg}")
    except FileNotFoundError:
        errors.append("File not found.")
    except Exception as e:
        errors.append(f"Import error: {e}")

    console.print(f"[green]CSV import: {success} added, {failure} failed[/green]")
    return success, failure, errors


def import_json(filepath: str, user_id: int = None) -> Tuple[int, int, List[str]]:
    """Import deliveries from JSON file (array of objects)."""
    success = 0
    failure = 0
    errors = []

    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = data.get("deliveries", [])

        for idx, item in enumerate(data):
            name = item.get("customer_name", item.get("name", "")).strip()
            addr = item.get("address", "").strip()
            contact = str(item.get("contact_number", item.get("contact", ""))).strip()
            notes = item.get("notes", "").strip()
            lat = item.get("latitude")
            lon = item.get("longitude")

            ok, msg, _ = add_delivery(name, addr, contact, notes, lat, lon, user_id)
            if ok:
                success += 1
            else:
                failure += 1
                errors.append(f"Item {idx + 1}: {msg}")
    except json.JSONDecodeError as e:
        errors.append(f"JSON parse error: {e}")
    except Exception as e:
        errors.append(f"Import error: {e}")

    console.print(f"[green]JSON import: {success} added, {failure} failed[/green]")
    return success, failure, errors


def build_and_cache_distance_matrix(deliveries: List[Delivery]) -> np.ndarray:
    """
    Build or retrieve cached pairwise distance matrix for a set of deliveries.
    Caches results in distance_cache table.
    """
    n = len(deliveries)
    matrix = np.zeros((n, n))
    session = get_session()

    try:
        for i in range(n):
            for j in range(i + 1, n):
                d_i = deliveries[i]
                d_j = deliveries[j]

                # Check cache
                cached = session.query(DistanceCache).filter(
                    DistanceCache.from_delivery_id == d_i.delivery_id,
                    DistanceCache.to_delivery_id == d_j.delivery_id,
                ).first()

                if cached:
                    dist = cached.distance_km
                else:
                    dist = haversine(d_i.latitude, d_i.longitude, d_j.latitude, d_j.longitude)
                    entry = DistanceCache(
                        from_delivery_id=d_i.delivery_id,
                        to_delivery_id=d_j.delivery_id,
                        distance_km=dist,
                    )
                    session.add(entry)

                matrix[i][j] = dist
                matrix[j][i] = dist

        session.commit()
    except Exception as e:
        session.rollback()
        console.print(f"[red]Distance cache error: {e}[/red]")
    finally:
        session.close()

    return matrix
