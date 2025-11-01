import os
import pytest
from secrets import token_hex


@pytest.fixture(scope="session", autouse=True)
def setup_test_paseto_key():
    if "PASETO_SECRET_KEY" not in os.environ:
        # generate a fresh 32-byte key for tests
        test_key = token_hex(32)
        os.environ["PASETO_SECRET_KEY"] = test_key
    yield
