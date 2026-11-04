import pytest
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token

def test_password_hashing():
    pw = "SuperSecureLocalPassword123!"
    hashed = get_password_hash(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_jwt_token_flow():
    user_id = "user-123456"
    token = create_access_token(user_id)
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == user_id
