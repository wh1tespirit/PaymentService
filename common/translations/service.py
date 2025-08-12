import contextlib
from pathlib import Path

from babel.support import Translations

from common.translations.enums import Locale, Scopes
from common.translations.errors import TranslationDomainNotFoundError


class TranslationService:
    def __init__(self, scope: Scopes, domains: list[str], locale: Locale):
        self.locale = locale
        self.__scope = scope
        self.__dir = Path("common/translations/") / self.__scope.value
        self.__translations = self.__get_translations(domains)

    def __get_translations(self, domains: list[str]):
        return {key: Translations.load(self.__dir, self.locale, key) for key in domains}

    def get_translation(self, domain: str, key: str, **kwargs):
        if domain not in self.__translations:
            raise TranslationDomainNotFoundError(domain)

        translation = self.__translations[domain].gettext(key)
        if kwargs:
            with contextlib.suppress(KeyError):
                translation = translation.format(**kwargs)

        return translation
