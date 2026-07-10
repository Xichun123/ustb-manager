import base64
import os
import secrets
import tempfile


_TEST_HOME = tempfile.TemporaryDirectory(prefix="ustb-manager-tests-")
os.environ["HOME"] = _TEST_HOME.name
os.environ.setdefault(
    "SESSION_ENCRYPTION_KEY",
    base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
)
