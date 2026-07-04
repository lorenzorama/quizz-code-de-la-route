from app.security import hash_password, verify_password


def test_hash_is_not_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$argon2")


def test_verify_accepts_correct_password():
    hashed = hash_password("s3cret-password")
    assert verify_password("s3cret-password", hashed) is True


def test_verify_rejects_wrong_password():
    hashed = hash_password("s3cret-password")
    assert verify_password("wrong-password", hashed) is False


def test_verify_rejects_malformed_hash():
    assert verify_password("anything", "not-a-real-hash") is False


def test_hashes_are_salted_and_differ():
    assert hash_password("same") != hash_password("same")
