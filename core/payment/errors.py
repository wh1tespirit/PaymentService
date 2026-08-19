class PaymentProcessingError(Exception):
    """Ошибка обработки платежа: сообщение уходит в retry, затем в DLQ."""


class WebhookDeliveryError(PaymentProcessingError):
    """Webhook не доставлен (сетевая ошибка, таймаут или не-2xx ответ)."""
