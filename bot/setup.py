import gettext
from pathlib import Path
from types import MappingProxyType

from decouple import config

GUILDS_SETTINGS_PATH = Path('settings.pickle')
GUILDS_SETTINGS_PATH.touch()

DB_PATH = Path('db.pickle')
DB_PATH.touch()

LOCALEDIR_PATH = Path('locales')

LOCALES = ['en'] + [child.name for child in LOCALEDIR_PATH.iterdir()]
translators = {}
TRANSLATORS = MappingProxyType(translators)
for locale in LOCALES:
    translators[locale] = gettext.translation(
        'messages', LOCALEDIR_PATH, languages=[locale], fallback=True,
    )

COMMAND_PREFIX = config('COMMAND_PREFIX', '^')
BOT_TOKEN = config('BOT_TOKEN')

SOURCE_URL = 'https://rdodailies.com/'
