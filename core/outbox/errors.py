class UnknownOutboxEventTypeError(Exception):
    """Для типа события не задан routing key — публиковать его некуда."""
