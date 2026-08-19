import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from api.asgi import app
from common.db.connect import Session
from core.outbox.models import OutboxModel
from core.payment.models import PaymentModel

HEADERS = {"X-API-Key": "test-api-key", "Idempotency-Key": "key-1"}
BODY = {
    "amount": "100.50",
    "currency": "RUB",
    "description": "Заказ №1",
    "metadata": {"order_id": 42},
    "webhook_url": "http://localhost:9000/webhook",
}


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def count_rows(model) -> int:
    async with Session() as session:
        return (await session.execute(select(func.count(model.id)))).scalar_one()


async def test_create_payment_returns_202(client):
    resp = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    assert resp.status_code == 202
    data = resp.json()
    assert data["payment_id"]
    assert data["status"] == "pending"
    assert data["created_at"]


async def test_create_payment_writes_payment_and_outbox(client):
    resp = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    payment_id = resp.json()["payment_id"]
    assert await count_rows(PaymentModel) == 1
    async with Session() as session:
        outbox = (await session.execute(select(OutboxModel))).scalar_one()
    assert outbox.event_type == "payment.created"
    assert outbox.payload == {"payment_id": payment_id}
    assert outbox.status == "pending"


async def test_same_idempotency_key_returns_same_payment(client):
    first = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    second = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    assert second.status_code == 202
    assert second.json()["payment_id"] == first.json()["payment_id"]
    assert await count_rows(PaymentModel) == 1
    assert await count_rows(OutboxModel) == 1


async def test_outbox_failure_rolls_back_payment(client, monkeypatch):
    def broken_outbox(**kwargs):
        raise RuntimeError("outbox unavailable")

    monkeypatch.setattr("core.payment.cases.create_payment.OutboxModel", broken_outbox)
    resp = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    assert resp.status_code == 500
    assert await count_rows(PaymentModel) == 0


async def test_missing_api_key_returns_401(client):
    resp = await client.post("/api/v1/payments", json=BODY, headers={"Idempotency-Key": "key-1"})
    assert resp.status_code == 401


async def test_wrong_api_key_returns_401(client):
    headers = {"X-API-Key": "wrong", "Idempotency-Key": "key-1"}
    resp = await client.post("/api/v1/payments", json=BODY, headers=headers)
    assert resp.status_code == 401


async def test_missing_idempotency_key_returns_422(client):
    resp = await client.post("/api/v1/payments", json=BODY, headers={"X-API-Key": "test-api-key"})
    assert resp.status_code == 422


async def test_invalid_body_returns_422(client):
    bad = {**BODY, "amount": "-5", "currency": "GBP"}
    resp = await client.post("/api/v1/payments", json=bad, headers=HEADERS)
    assert resp.status_code == 422


async def test_get_payment_returns_details(client):
    from tests.factories import create_pending_payment

    payment = await create_pending_payment(description="Заказ №1", metadata_={"order_id": 42})
    resp = await client.get(f"/api/v1/payments/{payment.id}", headers={"X-API-Key": "test-api-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_id"] == payment.id
    assert data["status"] == "pending"
    assert data["currency"] == "RUB"
    assert data["metadata"] == {"order_id": 42}
    assert data["webhook_url"] == "http://localhost:9000/webhook"
    assert data["processed_at"] is None


async def test_get_unknown_payment_returns_404(client):
    resp = await client.get("/api/v1/payments/no-such-id", headers={"X-API-Key": "test-api-key"})
    assert resp.status_code == 404
