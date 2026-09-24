import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_e2e_check_all_schemes():
    """
    Test end-to-end flow for checking all schemes.
    """
    payload = {
        "age": 65,
        "has_bpl": True,
        "is_organised_worker": False,
        "is_farmer": True,
        "land_holding_hectares": 1.5,
        "occupation": "farmer",
        "annual_income": 50000,
        "is_government_employee": False
    }

    response = client.post("/api/check-all-schemes", json=payload)

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "schemes" in data
    assert "summary" in data
    assert "eligible_count" in data["summary"]

    # Verify structure
    for scheme_id, result in data["schemes"].items():
        assert "eligible" in result
        assert "reason" in result
