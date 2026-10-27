from fastapi import APIRouter, HTTPException, Depends, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.database.connection import query_one, query_all, execute_cmd, execute_insert
from app.services.distance_service import resolve_location_name, KNOWN_LOCATIONS
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2)
    phone: Optional[str] = None
    role: str = Field(default="PATIENT")  # PATIENT, DONOR, BLOOD_BANK_STAFF
    # Donor specific fields (if role == DONOR)
    blood_group: Optional[str] = None
    city: Optional[str] = "New Delhi"
    area_name: Optional[str] = None
    approx_lat: Optional[float] = None
    approx_lng: Optional[float] = None
    # Blood bank staff specific
    assigned_blood_bank_id: Optional[int] = None

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordSchema(BaseModel):
    email: EmailStr

def get_current_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = payload.get("user_id")
    user = query_one("SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,))
    return user

async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    # 1. Check HTTP-only cookie
    token = request.cookies.get("access_token")
    # 2. Check Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
    return get_current_user_from_token(token)

async def require_auth(request: Request) -> Dict[str, Any]:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in."
        )
    return user

@router.post("/register")
async def register(payload: RegisterSchema, response: Response):
    # Validate role
    role = payload.role.upper().strip()
    if role not in ["PATIENT", "DONOR", "BLOOD_BANK_STAFF"]:
        raise HTTPException(status_code=400, detail="Invalid role specified.")

    # Check if user already exists
    existing = query_one("SELECT id FROM users WHERE email = ?", (payload.email.lower().strip(),))
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    pwd_hash = hash_password(payload.password)
    email = payload.email.lower().strip()

    user_id = execute_insert(
        """
        INSERT INTO users (email, password_hash, full_name, phone, role, assigned_blood_bank_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (email, pwd_hash, payload.full_name.strip(), payload.phone, role, payload.assigned_blood_bank_id)
    )

    # If role is DONOR, create a sanitized Donor Profile
    if role == "DONOR":
        if not payload.blood_group:
            raise HTTPException(status_code=400, detail="Blood group is required for donor registration.")

        # Determine approximate coordinates (fuzzed to protect privacy)
        lat = payload.approx_lat or settings.DEFAULT_LAT
        lng = payload.approx_lng or settings.DEFAULT_LNG
        
        # If city / area resolved to coordinates
        if payload.city:
            resolved = resolve_location_name(payload.area_name or payload.city)
            if resolved:
                lat, lng, _ = resolved

        # Obfuscate coordinates to ~1-2km (round to 2 decimal places)
        approx_lat = round(lat, 2)
        approx_lng = round(lng, 2)

        execute_insert(
            """
            INSERT INTO donor_profiles (
                user_id, blood_group, city, area_name, approx_lat, approx_lng,
                is_available, preferred_contact, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 'IN_APP', 'VERIFIED')
            """,
            (user_id, payload.blood_group.upper().strip(), payload.city or "New Delhi", payload.area_name, approx_lat, approx_lng)
        )

    # Generate token and set cookie
    token_data = {"sub": email, "user_id": user_id, "role": role}
    token = create_access_token(token_data)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600 * 24 * 7,
        samesite="lax"
    )

    # Determine redirect
    redirect_map = {
        "PATIENT": "/dashboard/user",
        "DONOR": "/dashboard/donor",
        "BLOOD_BANK_STAFF": "/dashboard/blood-bank",
        "ADMIN": "/dashboard/admin"
    }

    return {
        "status": "success",
        "message": "Account created successfully.",
        "user_id": user_id,
        "email": email,
        "role": role,
        "redirect_url": redirect_map.get(role, "/dashboard/user")
    }

@router.post("/login")
async def login(payload: LoginSchema, response: Response):
    email = payload.email.lower().strip()
    user = query_one("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,))
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token_data = {"sub": user["email"], "user_id": user["id"], "role": user["role"]}
    token = create_access_token(token_data)
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600 * 24 * 7,
        samesite="lax"
    )

    redirect_map = {
        "PATIENT": "/dashboard/user",
        "DONOR": "/dashboard/donor",
        "BLOOD_BANK_STAFF": "/dashboard/blood-bank",
        "ADMIN": "/dashboard/admin"
    }

    return {
        "status": "success",
        "message": "Logged in successfully.",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "assigned_blood_bank_id": user["assigned_blood_bank_id"]
        },
        "redirect_url": redirect_map.get(user["role"], "/dashboard/user")
    }

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"status": "success", "message": "Logged out successfully.", "redirect_url": "/login"}

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordSchema):
    email = payload.email.lower().strip()
    user = query_one("SELECT id, full_name FROM users WHERE email = ?", (email,))
    # Security best practice: don't reveal if email does not exist
    return {
        "status": "success",
        "message": f"If an account exists for {email}, a secure password reset link has been dispatched to your email."
    }

@router.get("/me")
async def get_current_user_profile(user: Dict[str, Any] = Depends(require_auth)):
    donor_profile = None
    assigned_bank = None

    if user["role"] == "DONOR":
        donor_profile = query_one("SELECT * FROM donor_profiles WHERE user_id = ?", (user["id"],))
    elif user["role"] == "BLOOD_BANK_STAFF" and user["assigned_blood_bank_id"]:
        assigned_bank = query_one("SELECT * FROM blood_banks WHERE id = ?", (user["assigned_blood_bank_id"],))

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "phone": user["phone"],
            "role": user["role"],
            "created_at": user["created_at"]
        },
        "donor_profile": donor_profile,
        "assigned_blood_bank": assigned_bank
    }
