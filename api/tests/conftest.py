import os
import pytest
from fastapi.testclient import TestClient

# Point to the model artifact relative to the repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MODEL_PATH", os.path.join(_REPO_ROOT, "model", "model_v1.0.0.pkl"))
os.environ.setdefault("MODEL_VERSION", "1.0.0")
os.environ.setdefault("API_VERSION", "1.0.0")


@pytest.fixture(scope="session")
def api_client():
    from api.main import app
    with TestClient(app) as c:
        yield c
