from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any

from app.core.config import settings
from app.database.models import init_db
from app.database.seed_data import seed
from app.database.connection import query_one, query_all
from app.api.auth import router as auth_router, get_current_user
from app.api.blood_banks import router as blood_banks_router
from app.api.donors import router as donors_router
from app.api.emergency import router as emergency_router
from app.api.ingestion import router as ingestion_router
from app.api.events import router as events_router
from app.api.admin import router as admin_router
import asyncio
from app.api.notifications import router as notifications_router
from app.services.inventory_service import calculate_availability_status, get_inventory_history, refresh_all_inventory_timestamps
from app.services.simulator_service import simulate_random_event
from app.api.events import broadcast_event

async def periodic_feed_worker():
    """Background worker that periodically simulates real-time activity and broadcasts via SSE."""
    while True:
        try:
            await asyncio.sleep(45)
            event = simulate_random_event()
            if event and "blood_bank_id" in event:
                await broadcast_event(event)
        except asyncio.CancelledError:
            break
        except Exception as e:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and seed initial development data
    init_db()
    seed()
    # Refresh all inventory timestamps so blood bank feeds show fresh, real-time availability
    refresh_all_inventory_timestamps()
    
    # Start gentle background real-time feed simulation worker
    worker_task = asyncio.create_task(periodic_feed_worker())
    try:
        yield
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Emergency Blood & Donor Finder with automated data ingestion from authorized blood banks.",
    lifespan=lifespan
)

# Static and Templates
BASE_PATH = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_PATH / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))

# Include API Routers
app.include_router(auth_router)
app.include_router(blood_banks_router)
app.include_router(donors_router)
app.include_router(emergency_router)
app.include_router(ingestion_router)
app.include_router(events_router)
app.include_router(admin_router)
app.include_router(notifications_router)

# ----------------- HTML WEB PAGES -----------------

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    user = await get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"current_user": user}
    )

@app.get("/search-blood", response_class=HTMLResponse)
async def search_blood_page(
    request: Request,
    blood_group: Optional[str] = "O+",
    component: Optional[str] = "RBC",
    location: Optional[str] = "Delhi",
    lat: Optional[float] = 28.6139,
    lng: Optional[float] = 77.2090
):
    user = await get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="search_blood.html",
        context={
            "current_user": user,
            "query_group": blood_group,
            "query_component": component,
            "location": location,
            "lat": lat,
            "lng": lng
        }
    )

@app.get("/search-donors", response_class=HTMLResponse)
async def search_donors_page(
    request: Request,
    blood_group: Optional[str] = "O+",
    component: Optional[str] = "RBC"
):
    user = await get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="search_donors.html",
        context={
            "current_user": user,
            "query_group": blood_group,
            "query_component": component
        }
    )

@app.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    user = await get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="map_view.html",
        context={"current_user": user}
    )

@app.get("/emergency-request", response_class=HTMLResponse)
async def emergency_request_page(request: Request):
    user = await get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="emergency_request.html",
        context={"current_user": user}
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        role = user.get("role")
        redirects = {
            "PATIENT": "/dashboard/user",
            "DONOR": "/dashboard/donor",
            "BLOOD_BANK_STAFF": "/dashboard/blood-bank",
            "ADMIN": "/dashboard/admin"
        }
        return RedirectResponse(redirects.get(role, "/dashboard/user"))
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"current_user": None}
    )

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse("/profile")
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"current_user": None}
    )

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_pwd_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context={"current_user": None}
    )

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    
    donor_profile = None
    assigned_bank = None
    if user["role"] == "DONOR":
        donor_profile = query_one("SELECT * FROM donor_profiles WHERE user_id = ?", (user["id"],))
    elif user["role"] == "BLOOD_BANK_STAFF" and user["assigned_blood_bank_id"]:
        assigned_bank = query_one("SELECT * FROM blood_banks WHERE id = ?", (user["assigned_blood_bank_id"],))

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "current_user": user,
            "donor_profile": donor_profile,
            "assigned_blood_bank": assigned_bank
        }
    )

# ----------------- ROLE DASHBOARDS -----------------

@app.get("/dashboard/user", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")

    requests = query_all("""
        SELECT * FROM emergency_requests 
        WHERE requester_id = ? 
        ORDER BY created_at DESC
    """, (user["id"],))

    detailed_requests = []
    for r in requests:
        responses = query_all("""
            SELECT resp.*, d.blood_group, d.city, u.full_name as donor_name
            FROM donor_responses resp
            JOIN donor_profiles d ON d.id = resp.donor_profile_id
            JOIN users u ON u.id = d.user_id
            WHERE resp.request_id = ?
            ORDER BY resp.responded_at DESC
        """, (r["id"],))
        detailed_requests.append({
            **r,
            "responses": responses
        })

    notifications = query_all("""
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 20
    """, (user["id"],))

    return templates.TemplateResponse(
        request=request,
        name="dashboards/user_dashboard.html",
        context={
            "current_user": user,
            "requests": detailed_requests,
            "notifications": notifications
        }
    )

@app.get("/dashboard/donor", response_class=HTMLResponse)
async def donor_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")

    donor = query_one("SELECT * FROM donor_profiles WHERE user_id = ?", (user["id"],))
    if not donor:
        return RedirectResponse("/profile")

    requests = query_all("""
        SELECT * FROM emergency_requests 
        WHERE status = 'OPEN' AND blood_group = ?
        ORDER BY created_at DESC LIMIT 20
    """, (donor["blood_group"],))

    return templates.TemplateResponse(
        request=request,
        name="dashboards/donor_dashboard.html",
        context={
            "current_user": user,
            "donor": donor,
            "requests": requests
        }
    )

@app.get("/dashboard/blood-bank", response_class=HTMLResponse)
async def blood_bank_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")

    bank_id = user["assigned_blood_bank_id"] or 1
    bank = query_one("SELECT * FROM blood_banks WHERE id = ?", (bank_id,))
    
    inventory = query_all("""
        SELECT * FROM blood_inventory 
        WHERE blood_bank_id = ? 
        ORDER BY blood_group, component
    """, (bank_id,))

    processed_inventory = []
    for item in inventory:
        stat = calculate_availability_status(
            units_available=item["units_available"],
            last_updated_at=item["last_updated_at"],
            facility_verification=bank["verification_status"],
            threshold_hours=settings.OUTDATED_THRESHOLD_HOURS
        )
        processed_inventory.append({
            **item,
            "status": stat["status"],
            "badge_class": stat["badge_class"]
        })

    history = get_inventory_history(bank_id, limit=30)

    return templates.TemplateResponse(
        request=request,
        name="dashboards/blood_bank_dashboard.html",
        context={
            "current_user": user,
            "bank": bank,
            "inventory": processed_inventory,
            "history": history
        }
    )

@app.get("/dashboard/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = await get_current_user(request)
    if not user or user["role"] != "ADMIN":
        return RedirectResponse("/login")

    stats = {
        "total_blood_banks": query_one("SELECT COUNT(*) as c FROM blood_banks")["c"],
        "total_donors": query_one("SELECT COUNT(*) as c FROM donor_profiles")["c"],
        "available_donors": query_one("SELECT COUNT(*) as c FROM donor_profiles WHERE is_available = 1")["c"],
        "total_units_in_stock": query_one("SELECT SUM(units_available) as s FROM blood_inventory")["s"] or 0,
        "open_emergency_requests": query_one("SELECT COUNT(*) as c FROM emergency_requests WHERE status = 'OPEN'")["c"],
        "pending_verifications": (
            query_one("SELECT COUNT(*) as c FROM blood_banks WHERE verification_status != 'VERIFIED'")["c"] +
            query_one("SELECT COUNT(*) as c FROM donor_profiles WHERE verification_status != 'VERIFIED'")["c"]
        )
    }

    blood_banks = query_all("""
        SELECT b.*, s.name as data_source_name,
               (SELECT SUM(units_available) FROM blood_inventory WHERE blood_bank_id = b.id) as total_units
        FROM blood_banks b
        LEFT JOIN data_sources s ON s.id = b.data_source_id
        ORDER BY b.id ASC
    """)

    donors = query_all("""
        SELECT d.*, u.full_name, u.email
        FROM donor_profiles d
        JOIN users u ON u.id = d.user_id
        ORDER BY d.id ASC
    """)

    data_sources = query_all("SELECT * FROM data_sources ORDER BY id ASC")

    audit_logs = query_all("""
        SELECT e.*, b.name as blood_bank_name
        FROM inventory_events e
        JOIN blood_banks b ON b.id = e.blood_bank_id
        ORDER BY e.recorded_at DESC LIMIT 50
    """)

    return templates.TemplateResponse(
        request=request,
        name="dashboards/admin_dashboard.html",
        context={
            "current_user": user,
            "stats": stats,
            "blood_banks": blood_banks,
            "donors": donors,
            "data_sources": data_sources,
            "audit_logs": audit_logs
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
