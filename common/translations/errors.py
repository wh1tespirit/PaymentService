class TranslationDomainNotFoundError(Exception):
    def __init__(self, domain: str):
        self.message = f"Translation domain {domain} not found"
        super().__init__(self.message)
