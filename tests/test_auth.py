from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hashing_and_verification():
    raw_pwd = "SuperSecretHospitalPassword2026!"
    hashed = hash_password(raw_pwd)
    
    assert hashed != raw_pwd
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False

def test_jwt_token_creation_and_payload_decode():
    data = {"sub": "doctor@aiims.edu", "user_id": 42, "role": "BLOOD_BANK_STAFF"}
    token = create_access_token(data)
    
    assert isinstance(token, str)
    assert len(token) > 20
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "doctor@aiims.edu"
    assert decoded["user_id"] == 42
    assert decoded["role"] == "BLOOD_BANK_STAFF"
    assert "exp" in decoded

def test_invalid_jwt_returns_none():
    invalid_token = "invalid.jwt.token.string"
    assert decode_access_token(invalid_token) is None
