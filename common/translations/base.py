from common.translations.enums import Locale

# Add new exception codes in /common/errors.py ExceptionCodes and descriptions in /translations .po files
# Then compile .po files to .mo files using command:
#   pybabel compile -d translations or pybabel compile -d translations --use-fuzzy


def get_locale_from_header(header_lang: str | None):
    if not header_lang:
        return Locale.EN

    try:
        return Locale(header_lang.strip().lower().split(",")[0])
    except ValueError:
        return Locale.EN
