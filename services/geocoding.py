"""
Geocoding Service — Geopy + Nominatim
Converts addresses to (lat, lon) coordinates with caching, retry, rate limiting.
"""

import time
import threading
from typing import Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from rich.console import Console
from models import get_session, Delivery

console = Console()
_lock = threading.Lock()
_last_request_time: float = 0.0
RATE_LIMIT_DELAY = 1.1  # Nominatim ToS: max 1 req/sec


def _rate_limit():
    global _last_request_time
    with _lock:
        elapsed = time.time() - _last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        _last_request_time = time.time()


def geocode_address(
    address: str,
    max_retries: int = 3,
) -> Optional[Tuple[float, float]]:
    """
    Geocode a single address string.

    Returns:
        (latitude, longitude) or None if geocoding fails.
    """
    geolocator = Nominatim(user_agent="delivery_route_optimizer_mca_2024")

    for attempt in range(1, max_retries + 1):
        try:
            _rate_limit()
            location = geolocator.geocode(address, timeout=10)
            if location:
                console.print(
                    f"  [green]✓[/green] Geocoded: [dim]{address[:60]}[/dim] "
                    f"→ ({location.latitude:.5f}, {location.longitude:.5f})"
                )
                return location.latitude, location.longitude
            else:
                console.print(f"  [yellow]⚠[/yellow] No result for: [dim]{address[:60]}[/dim]")
                return None
        except GeocoderTimedOut:
            console.print(f"  [yellow]Timeout (attempt {attempt}/{max_retries})[/yellow]")
            time.sleep(2 * attempt)
        except GeocoderServiceError as e:
            console.print(f"  [red]Service error: {e}[/red]")
            time.sleep(2 * attempt)
        except Exception as e:
            console.print(f"  [red]Unexpected error: {e}[/red]")
            return None

    console.print(f"  [red]✗ Failed after {max_retries} attempts: {address[:60]}[/red]")
    return None


def geocode_delivery(delivery_id: str) -> bool:
    """
    Geocode a single delivery record by its ID and persist coordinates.

    Returns:
        True if successful, False otherwise.
    """
    session = get_session()
    try:
        delivery = session.query(Delivery).filter_by(delivery_id=delivery_id).first()
        if not delivery:
            return False
        if delivery.is_geocoded and delivery.latitude and delivery.longitude:
            return True

        coords = geocode_address(delivery.address)
        if coords:
            delivery.latitude, delivery.longitude = coords
            delivery.is_geocoded = True
            delivery.geocode_attempts = (delivery.geocode_attempts or 0) + 1
            session.commit()
            return True
        else:
            delivery.geocode_attempts = (delivery.geocode_attempts or 0) + 1
            session.commit()
            return False
    except Exception as e:
        session.rollback()
        console.print(f"[red]DB error during geocoding: {e}[/red]")
        return False
    finally:
        session.close()


def geocode_all_pending(
    progress_callback=None,
    stop_event=None,
) -> Tuple[int, int]:
    """
    Geocode all deliveries that haven't been geocoded yet.

    Args:
        progress_callback: fn(current, total, delivery_id)
        stop_event: threading.Event to abort

    Returns:
        (success_count, failure_count)
    """
    session = get_session()
    try:
        pending = session.query(Delivery).filter(
            Delivery.is_geocoded == False,
            Delivery.geocode_attempts < 3,
            Delivery.is_active == True,
        ).all()
        ids = [(d.delivery_id, d.address) for d in pending]
    finally:
        session.close()

    total = len(ids)
    success = 0
    failure = 0
    console.print(f"[cyan]► Geocoding {total} pending address(es)…[/cyan]")

    for idx, (did, addr) in enumerate(ids, 1):
        if stop_event and stop_event.is_set():
            console.print("[yellow]Geocoding aborted.[/yellow]")
            break
        if progress_callback:
            progress_callback(idx, total, did)
        ok = geocode_delivery(did)
        if ok:
            success += 1
        else:
            failure += 1

    console.print(f"[green]✔ Geocoding done: {success} success, {failure} failed[/green]")
    return success, failure


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate that coordinates are within valid GPS range."""
    return -90 <= lat <= 90 and -180 <= lon <= 180
