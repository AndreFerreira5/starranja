"""
Unit Tests for Password Service
"""

import pytest
from unittest.mock import patch, MagicMock
from argon2.exceptions import (
    VerificationError,
    HashingError,
    InvalidHashError
)
from src.authentication.hashing import (
    PasswordService,
    hash_password,
    check_password
)
from src.authentication.exceptions import (
    PasswordHashingError,
    PasswordVerificationError,
    InvalidPasswordError
)
from src.authentication.config import settings

@pytest.fixture(autouse=True)
def reset_singleton_instance():
    """
    Reset the PasswordService singleton after each test.
    This prevents mocking in one test from affecting another.
    """
    yield  # This is where the test runs
    PasswordService._instance = None


class TestPasswordService:
    """Test suite for PasswordService class."""

    @pytest.fixture
    def password_service(self):
        """Fixture to provide a fresh PasswordService instance."""
        return PasswordService()

    @pytest.fixture
    def valid_password(self):
        """Fixture providing a valid test password."""
        return "SecureP@ssw0rd123!"

    @pytest.fixture
    def weak_password(self):
        """Fixture providing a weak test password."""
        return "weak"

    # ==================== Hash Password Tests ====================

    def test_hash_password_success(self, password_service, valid_password):
        """
        Test successful password hashing.
        """
        hashed = password_service.hash_password(valid_password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith("$argon2id$")

    def test_hash_password_deterministic_salt(self, password_service, valid_password):
        """
        Test that hashing the same password twice produces different hashes.

        This verifies that unique salts are generated for each hash
        """
        hash1 = password_service.hash_password(valid_password)
        hash2 = password_service.hash_password(valid_password)

        assert hash1 != hash2

    def test_hash_password_minimum_length(self, password_service):
        """Test password hashing with minimum valid length."""
        min_password = "a" * settings.MIN_PASSWORD_LENGTH
        hashed = password_service.hash_password(min_password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2id$")

    def test_hash_password_too_short(self, password_service):
        """Test that hashing fails for passwords below minimum length."""
        short_password = "a" * (settings.MIN_PASSWORD_LENGTH - 1)

        with pytest.raises(InvalidPasswordError) as exc_info:
            password_service.hash_password(short_password)

        assert "at least" in str(exc_info.value).lower()

    def test_hash_password_too_long(self, password_service):
        """Test that hashing fails for excessively long passwords."""
        long_password = "a" * (settings.MAX_PASSWORD_LENGTH + 1)

        with pytest.raises(InvalidPasswordError) as exc_info:
            password_service.hash_password(long_password)

        assert "exceed" in str(exc_info.value).lower()

    def test_hash_password_empty_string(self, password_service):
        """Test that hashing fails for empty passwords."""
        with pytest.raises(InvalidPasswordError) as exc_info:
            password_service.hash_password("")

        assert "empty" in str(exc_info.value).lower() or "at least" in str(exc_info.value).lower()

    def test_hash_password_whitespace_only(self, password_service):
        """Test that hashing fails for whitespace-only passwords."""
        with pytest.raises(InvalidPasswordError) as exc_info:
            password_service.hash_password("        ")

        assert "empty" in str(exc_info.value).lower() or "whitespace" in str(exc_info.value).lower()

    def test_hash_password_non_string(self, password_service):
        """Test that hashing fails for non-string inputs."""
        with pytest.raises(InvalidPasswordError):
            password_service.hash_password(12345)

        with pytest.raises(InvalidPasswordError):
            password_service.hash_password(None)

        with pytest.raises(InvalidPasswordError):
            password_service.hash_password(['password'])

    def test_hash_password_special_characters(self, password_service):
        """Test hashing passwords with various special characters."""
        special_passwords = [
            "P@ssw0rd!#$%",
            "密碼test123",  # Unicode characters
            "pass\nword\t123",  # Control characters
            "café_résumé_123"  # Accented characters
        ]

        for pwd in special_passwords:
            if len(pwd) >= settings.MIN_PASSWORD_LENGTH:
                hashed = password_service.hash_password(pwd)
                assert isinstance(hashed, str)
                assert hashed.startswith("$argon2id$")

    @patch('src.authentication.hashing.PasswordHasher')
    def test_hash_password_hashing_error(self, mock_hasher_class, password_service, valid_password):
        """Test proper error handling when Argon2 hashing fails."""
        mock_hasher = MagicMock()
        mock_hasher.hash.side_effect = HashingError("Hashing failed")
        password_service._hasher = mock_hasher

        with pytest.raises(PasswordHashingError) as exc_info:
            password_service.hash_password(valid_password)

        assert "system error" in str(exc_info.value).lower()

    # ==================== Check Password Tests ====================

    def test_check_password_correct(self, password_service, valid_password):
        """Test password verification with correct password."""
        hashed = password_service.hash_password(valid_password)
        result = password_service.check_password(hashed, valid_password)

        assert result is True

    def test_check_password_incorrect(self, password_service, valid_password):
        """Test password verification with incorrect password."""
        hashed = password_service.hash_password(valid_password)
        result = password_service.check_password(hashed, "WrongPassword123!")

        assert result is False

    def test_check_password_case_sensitive(self, password_service):
        """Test that password verification is case-sensitive."""
        password = "TestPassword123"
        hashed = password_service.hash_password(password)

        assert password_service.check_password(hashed, password) is True
        assert password_service.check_password(hashed, "testpassword123") is False
        assert password_service.check_password(hashed, "TESTPASSWORD123") is False

    def test_check_password_whitespace_sensitive(self, password_service):
        """Test that password verification is sensitive to whitespace."""
        password = "TestPassword123"
        hashed = password_service.hash_password(password)

        assert password_service.check_password(hashed, password) is True
        assert password_service.check_password(hashed, " TestPassword123") is False
        assert password_service.check_password(hashed, "TestPassword123 ") is False

    def test_check_password_invalid_hash_format(self, password_service, valid_password):
        """Test verification fails gracefully with invalid hash format."""
        invalid_hashes = [
            "",
            "not_a_valid_hash",
            "$argon2id$invalid",
            "bcrypt_hash_format",
            None
        ]

        for invalid_hash in invalid_hashes[:-1]:  # Exclude None
            with pytest.raises(PasswordVerificationError):
                password_service.check_password(invalid_hash, valid_password)

    def test_check_password_non_string_password(self, password_service):
        """Test that verification fails for non-string passwords."""
        hashed = password_service.hash_password("ValidPassword123")

        with pytest.raises(InvalidPasswordError):
            password_service.check_password(hashed, 12345)

        with pytest.raises(InvalidPasswordError):
            password_service.check_password(hashed, None)

    @patch('src.authentication.hashing.PasswordHasher')
    def test_check_password_verification_error(self, mock_hasher_class, password_service, valid_password):
        """Test proper error handling when Argon2 verification fails."""
        mock_hasher = MagicMock()
        mock_hasher.verify.side_effect = VerificationError("Verification failed")
        password_service._hasher = mock_hasher

        with pytest.raises(PasswordVerificationError) as exc_info:
            password_service.check_password("$argon2id$...", valid_password)

        assert "system error" in str(exc_info.value).lower()

    @patch('src.authentication.hashing.PasswordHasher')
    def test_check_password_invalid_hash_error(self, mock_hasher_class, password_service, valid_password):
        """Test proper error handling for corrupted hash."""
        mock_hasher = MagicMock()
        mock_hasher.verify.side_effect = InvalidHashError("Invalid hash")
        password_service._hasher = mock_hasher

        with pytest.raises(PasswordVerificationError) as exc_info:
            password_service.check_password("corrupted_hash", valid_password)

        assert "invalid" in str(exc_info.value).lower() or "corrupted" in str(exc_info.value).lower()

    # ==================== Rehashing Tests ====================

    def test_check_needs_rehash_same_parameters(self, password_service, valid_password):
        """Test that newly hashed passwords don't need rehashing."""
        hashed = password_service.hash_password(valid_password)
        needs_rehash = password_service.check_needs_rehash(hashed)

        # With current parameters, should not need rehashing
        assert needs_rehash is False

    @patch('src.authentication.hashing.PasswordHasher')
    def test_check_needs_rehash_updated_parameters(self, mock_hasher_class, password_service, valid_password):
        """Test that old hashes are detected as needing rehash."""
        mock_hasher = MagicMock()
        mock_hasher.check_needs_rehash.return_value = True
        password_service._hasher = mock_hasher

        needs_rehash = password_service.check_needs_rehash("$argon2id$old_params")
        assert needs_rehash is True

    def test_check_needs_rehash_error_handling(self, password_service):
        """Test that rehash check handles errors gracefully."""
        # Should return False on error rather than raising
        result = password_service.check_needs_rehash("invalid_hash")
        assert result is False

    # ==================== Verify and Update Tests ====================

    def test_verify_and_update_correct_no_rehash(self, password_service, valid_password):
        """Test verify_and_update with correct password and no rehashing needed."""
        hashed = password_service.hash_password(valid_password)
        is_valid, new_hash = password_service.verify_and_update(hashed, valid_password)

        assert is_valid is True
        assert new_hash is None  # No rehashing needed

    def test_verify_and_update_incorrect_password(self, password_service, valid_password):
        """Test verify_and_update with incorrect password."""
        hashed = password_service.hash_password(valid_password)
        is_valid, new_hash = password_service.verify_and_update(hashed, "WrongPassword")

        assert is_valid is False
        assert new_hash is None

    @patch('src.authentication.hashing.PasswordHasher')
    def test_verify_and_update_with_rehash(self, mock_hasher_class, password_service, valid_password):
        """Test verify_and_update when rehashing is needed."""
        # First create a real hash
        real_service = PasswordService()
        old_hash = real_service.hash_password(valid_password)

        # Mock to indicate rehashing is needed
        mock_hasher = MagicMock()
        mock_hasher.verify.return_value = None  # Successful verification
        mock_hasher.check_needs_rehash.return_value = True
        mock_hasher.hash.return_value = "$argon2id$new_hash"
        password_service._hasher = mock_hasher

        is_valid, new_hash = password_service.verify_and_update(old_hash, valid_password)

        assert is_valid is True
        assert new_hash is not None
        assert isinstance(new_hash, str)

    # ==================== Singleton Pattern Tests ====================

    def test_singleton_pattern(self):
        """Test that PasswordService implements singleton pattern correctly."""
        service1 = PasswordService()
        service2 = PasswordService()

        assert service1 is service2
        assert id(service1) == id(service2)

    # ==================== Module-Level Function Tests ====================

    def test_module_level_hash_password(self, valid_password):
        """Test module-level hash_password convenience function."""
        hashed = hash_password(valid_password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2id$")

    def test_module_level_check_password(self, valid_password):
        """Test module-level check_password convenience function."""
        hashed = hash_password(valid_password)

        assert check_password(hashed, valid_password) is True
        assert check_password(hashed, "WrongPassword") is False

    # ==================== Integration Tests ====================

    def test_full_authentication_flow(self, password_service):
        """
        Test complete authentication flow.

        Simulates:
        1. User registration (hash password)
        2. User login (verify password)
        3. Multiple login attempts
        """
        # Registration
        user_password = "UserPassword123!"
        stored_hash = password_service.hash_password(user_password)

        # Successful login
        assert password_service.check_password(stored_hash, user_password) is True

        # Failed login attempts
        assert password_service.check_password(stored_hash, "wrong1") is False
        assert password_service.check_password(stored_hash, "wrong2") is False

        # Another successful login
        assert password_service.check_password(stored_hash, user_password) is True

    def test_multiple_users_different_hashes(self, password_service):
        """
        Test that same password for different users produces different hashes.

        This is critical for security - even if two users have the same
        password, their hashes should be different due to unique salts.
        """
        password = "CommonPassword123!"

        hash1 = password_service.hash_password(password)
        hash2 = password_service.hash_password(password)
        hash3 = password_service.hash_password(password)

        # All hashes should be different
        assert hash1 != hash2
        assert hash2 != hash3
        assert hash1 != hash3

        # But all should verify correctly
        assert password_service.check_password(hash1, password) is True
        assert password_service.check_password(hash2, password) is True
        assert password_service.check_password(hash3, password) is True

    def test_unicode_password_support(self, password_service):
        """Test support for Unicode characters in passwords."""
        unicode_passwords = [
            "Пароль123!",  # Cyrillic
            "密码Password1!",  # Chinese
            "كلمة_سر123",  # Arabic
            "Contraseña123!",  # Spanish
            "Mot_de_passe123!",  # French
            "🔐Password123"  # Emoji
        ]

        for pwd in unicode_passwords:
            if len(pwd) >= settings.MIN_PASSWORD_LENGTH:
                hashed = password_service.hash_password(pwd)
                assert password_service.check_password(hashed, pwd) is True
                # Verify wrong password fails
                assert password_service.check_password(hashed, pwd + "x") is False

    # ==================== Security Property Tests ====================

    def test_timing_attack_resistance(self, password_service, valid_password):
        """
        Test that verification time is constant regardless of password correctness.

        Note: This is a basic test. Argon2 is designed to be timing-attack
        resistant, but comprehensive testing would require statistical analysis.
        """
        hashed = password_service.hash_password(valid_password)

        import time

        # Measure time for correct password
        times_correct = []
        for _ in range(10):
            start = time.perf_counter()
            password_service.check_password(hashed, valid_password)
            times_correct.append(time.perf_counter() - start)

        # Measure time for incorrect password
        times_incorrect = []
        for _ in range(10):
            start = time.perf_counter()
            password_service.check_password(hashed, "WrongPassword123!")
            times_incorrect.append(time.perf_counter() - start)

        # Times should be similar (within reasonable variance)
        avg_correct = sum(times_correct) / len(times_correct)
        avg_incorrect = sum(times_incorrect) / len(times_incorrect)

        # Allow for some variance, but should be in same order of magnitude
        ratio = max(avg_correct, avg_incorrect) / min(avg_correct, avg_incorrect)
        assert ratio < 2.0  # Should be relatively close

    def test_no_password_in_hash(self, password_service, valid_password):
        """Verify that the plaintext password is not contained in the hash."""
        hashed = password_service.hash_password(valid_password)

        # Password should not appear anywhere in the hash
        assert valid_password not in hashed
        assert valid_password.lower() not in hashed.lower()
        assert valid_password.upper() not in hashed.upper()

    # ==================== Performance Tests ====================

    def test_hash_performance_acceptable(self, password_service, valid_password):
        """
        Test that hashing performance is within acceptable bounds.

        Argon2 is intentionally slow to resist brute-force attacks,
        but should still complete in reasonable time for user experience.
        """
        import time

        start = time.time()
        password_service.hash_password(valid_password)
        duration = time.time() - start

        # Should complete in less than 2 seconds for good UX
        assert duration < 2.0
        # But should take at least some time (not instant)
        assert duration > 0.01

    def test_verify_performance_acceptable(self, password_service, valid_password):
        """Test that verification performance is within acceptable bounds."""
        import time

        hashed = password_service.hash_password(valid_password)

        start = time.time()
        password_service.check_password(hashed, valid_password)
        duration = time.time() - start

        # Verification should be similar speed to hashing
        assert duration < 2.0
        assert duration > 0.01


# ==================== Parametrized Tests ====================

@pytest.mark.parametrize("password,should_be_valid", [
    ("ValidPass123!", True),
    ("Short1!", False),  # Too short (< MIN_PASSWORD_LENGTH)
    ("a" * 200, False),  # Too long (> MAX_PASSWORD_LENGTH)
    ("", False),  # Empty
    ("   ", False),  # Whitespace only
    ("12345678", True),  # Minimum length (MIN_PASSWORD_LENGTH)
    ("Pass Word 123!", True),  # With spaces
    ("Pássword123", True),  # Accented
])
def test_password_validation_parametrized(password, should_be_valid):
    """Parametrized test for password validation."""
    service = PasswordService()

    if should_be_valid:
        hashed = service.hash_password(password)
        assert isinstance(hashed, str)
    else:
        with pytest.raises(InvalidPasswordError):
            service.hash_password(password)


@pytest.mark.parametrize("correct_password,test_password,should_match", [
    ("Password123!", "Password123!", True),
    ("Password123!", "password123!", False),  # Case sensitivity
    ("Password123!", "Password123! ", False),  # Trailing space
    ("Password123!", " Password123!", False),  # Leading space
    ("Password1V3!", "Password123", False),  # Missing character
    ("Test@123", "Test@123", True),
    ("Test@123", "Test@124", False),  # Different character
])
def test_password_verification_parametrized(correct_password, test_password, should_match):
    """Parametrized test for password verification."""
    service = PasswordService()
    hashed = service.hash_password(correct_password)

    result = service.check_password(hashed, test_password)
    assert result is should_match


# ==================== Fixtures for Integration Tests ====================

@pytest.fixture
def sample_users():
    """Fixture providing sample user data for testing."""
    return [
        {"email": "mechanic@starranja.pt", "password": "Mechanic123!"},
        {"email": "manager@starranja.pt", "password": "Manager456!"},
        {"email": "admin@starranja.pt", "password": "Admin789!"},
    ]


def test_multiple_users_authentication(sample_users):
    """Test authentication for multiple users with different passwords."""
    service = PasswordService()
    user_hashes = {}

    # Register all users
    for user in sample_users:
        user_hashes[user["email"]] = service.hash_password(user["password"])

    # Verify all users can authenticate
    for user in sample_users:
        hashed = user_hashes[user["email"]]
        assert service.check_password(hashed, user["password"]) is True

        # Verify other users' passwords don't work
        for other_user in sample_users:
            if other_user["email"] != user["email"]:
                assert service.check_password(hashed, other_user["password"]) is False