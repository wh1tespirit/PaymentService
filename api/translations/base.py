import logging

from babel import Locale
from babel.core import UnknownLocaleError
from babel.support import Translations

from common.logger import Loggers
from common.utils import get_moscow_time

# Add new exception codes in /common/errors.py ExceptionCodes and descriptions in /translations .po files
# Then compile .po files to .mo files using command:
#   pybabel compile -d translations or pybabel compile -d translations --use-fuzzy


def get_translations(locale):
    return Translations.load(dirname="api/translations/", locales=locale.language)


def get_locale_from_header(accept_language_header):
    if accept_language_header:
        try:
            languages = accept_language_header.split(",")
            if languages:
                return Locale.parse(languages[0].strip(), sep="-")
        except UnknownLocaleError as e:
            logger = logging.getLogger(Loggers.API_CONSOLE)
            logger.warning(f"({get_moscow_time()})\n{e}")
    return Locale("en")


def get_translations_from_header(accept_language_header: str):
    locale = get_locale_from_header(accept_language_header)
    translations = get_translations(locale)

    return translations
