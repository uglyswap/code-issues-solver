from backend.app.security import encrypt_value, decrypt_value, hash_password, verify_password, create_access_token, decode_access_token


def test_encrypt_decrypt():
    original = "super-secret-value"
    encrypted = encrypt_value(original)
    decrypted = decrypt_value(encrypted)
    assert decrypted == original


def test_password_hashing():
    pwd = "my-password"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    token = create_access_token({"sub": "42"})
    payload = decode_access_token(token)
    assert payload["sub"] == "42"


def test_jwt_invalid():
    assert decode_access_token("invalid.token.here") is None
