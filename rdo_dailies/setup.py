import gettext
from logging import config as logging_config
from pathlib import Path
from types import MappingProxyType

import yaml
from decouple import config

BASE_DIR = Path(__file__).parent
HOME_DIR = Path.home() / '.rdo_dailies_announcer'
HOME_DIR.mkdir(exist_ok=True)

with open(BASE_DIR / 'logging.yml', encoding='utf-8') as logging_config_file:
    logging_config.dictConfig(yaml.safe_load(logging_config_file))

GUILDS_SETTINGS_PATH = HOME_DIR / 'settings.pickle'
GUILDS_SETTINGS_PATH.touch()

DB_PATH = HOME_DIR / 'db.pickle'
DB_PATH.touch()

LOCALEDIR_PATH = BASE_DIR / 'locales'
LOCALES = ['en'] + [child.name for child in LOCALEDIR_PATH.iterdir()]
translators = {}
TRANSLATORS = MappingProxyType(translators)
for locale in LOCALES:
    translators[locale] = gettext.translation(
        'messages', LOCALEDIR_PATH, languages=[locale], fallback=True,
    )

COMMAND_PREFIX = config('RDO_DAILIES_COMMAND_PREFIX', '^')
BOT_TOKEN = config('RDO_DAILIES_BOT_TOKEN')

SOURCE_URL = config('RDO_DAILIES_SOURCE_URL')
NAZAR_SOURCE_URL = config('RDO_DAILIES_NAZAR_SOURCE_URL')
