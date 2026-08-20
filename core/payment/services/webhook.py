import httpx

from core.payment.errors import WebhookDeliveryError
from core.payment.models import PaymentModel


class WebhookSender:
    """Шлёт уведомление о результате платежа. Клиент общий на процесс — см. провайдер."""

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def send(self, payment: PaymentModel) -> None:
        body = {
            "payment_id": payment.id,
            "status": payment.status,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "metadata": payment.metadata_,
            "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
        }
        try:
            response = await self.client.post(payment.webhook_url, json=body)
        except httpx.HTTPError as exc:
            raise WebhookDeliveryError(f"Webhook request failed: {exc}") from exc
        if response.status_code // 100 != 2:
            raise WebhookDeliveryError(f"Webhook returned {response.status_code}")
