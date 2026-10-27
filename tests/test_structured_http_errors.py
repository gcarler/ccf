from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.app import http_exception_handler, structured_http_exception_handler
from backend.exceptions.http import StructuredHTTPException


def test_structured_errors_preserve_nested_contract_and_client_aliases():
    app = FastAPI()
    app.add_exception_handler(StructuredHTTPException, structured_http_exception_handler)

    @app.get("/validate")
    def validate():
        raise StructuredHTTPException(
            status_code=422,
            detail={"code": "REQUIRED", "field_id": "nombre", "message": "Required field"},
            headers={"X-Error-Source": "validation"},
        )

    response = TestClient(app).get("/validate")
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == {"code": "REQUIRED", "field_id": "nombre", "message": "Required field"}
    assert body["code"] == body["detail"]["code"]
    assert body["field_id"] == body["detail"]["field_id"]
    assert response.headers["x-error-source"] == "validation"


def test_existing_http_exception_contract_stays_flat():
    app = FastAPI()
    app.add_exception_handler(HTTPException, http_exception_handler)

    @app.get("/denied")
    def denied():
        raise HTTPException(status_code=403, detail={"code": "DENIED", "message": "Denied"})

    response = TestClient(app).get("/denied")
    assert response.status_code == 403
    assert response.json() == {"code": "DENIED", "message": "Denied", "detail": "Denied"}
