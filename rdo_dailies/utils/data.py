import datetime
from io import BytesIO
from types import MappingProxyType

import aiohttp
import discord

from rdo_dailies.settings import DB_PATH, LOCATION_TO_URL_MAPPINGS, NAZAR_SOURCE_URL, SOURCE_URL, TRANSLATORS
from rdo_dailies.utils import io
from rdo_dailies.utils.datetime import day_from_iso, is_before_update_time


def separate_number_from_text(challenges):
    for challenge in challenges:
        full_description = challenge['description']['localizedFull']
        if full_description[0].isdigit():
            number_with_text = full_description.split('/', maxsplit=1)
            yield number_with_text[1].split(maxsplit=1)
        else:
            yield ['1', full_description]


CATEGORIES_MAPPING = MappingProxyType({
    'CHARACTER_RANK': 'general',
    'CHARACTER_RANK_BOUNTY_HUNTER': 'bounty hunter',
    'CHARACTER_RANK_TRADER': 'trader',
    'CHARACTER_RANK_COLLECTOR': 'collector',
    'CHARACTER_RANK_MOONSHINER': 'moonshiner',
    'CHARACTER_RANK_NATURALIST': 'naturalist',
})


def parse(dict_):
    data = dict_.get('challengeSets') or dict_.get('data')
    date = datetime.date.fromtimestamp(data[0]['startTime']).isoformat()
    dailies = {}
    for category in data:
        cat_name = CATEGORIES_MAPPING[category['role']]
        challenges = (challenge for challenge in category['challenges'])
        dailies[cat_name] = [
            {'number': number, 'text': text}
            for number, text in separate_number_from_text(challenges)
        ]
    return {
        'date': date,
        'dailies': dailies,
        'sent_to_channels': [],
    }


async def get_data(date):
    if (data := await io.read_file(DB_PATH)) is not None:
        if data['date'] == date or is_before_update_time():
            return data
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        dailies_data = await io.get_by_session(session, SOURCE_URL, 'json')
        parsed_data = parse(dailies_data)
        if parsed_data['date'] != date:
            return None
        nazar_data = await io.get_by_session(session, NAZAR_SOURCE_URL, 'json')
        location_id = nazar_data.get('nazar') or nazar_data['location']['id']
        parsed_data['nazar_img'] = await io.get_by_session(session, LOCATION_TO_URL_MAPPINGS[location_id], 'bytes')
    return parsed_data


def render(data, lang):
    TRANSLATORS[lang].install()
    strings = ['{0} — {1}\n'.format(_('Daily challenges'), day_from_iso(data['date']))]
    ordered_dailies = {cat: data['dailies'][cat] for cat in CATEGORIES_MAPPING.values()}
    for category, tasks in ordered_dailies.items():
        cat_title = '{0}'.format(category.capitalize())
        strings.append('__{0}__'.format(_(cat_title)))
        for task in tasks:
            strings.append('{0}: **{1}**'.format(
                _(task['text']), task['number'],
            ))
        strings.append('')
    strings.append('__{0}__'.format(_("Madam Nazar's Location")))
    return '\n'.join(strings)


async def send(bot, channel, data):
    discord_channel = bot.get_channel(channel.id)
    await discord_channel.send(
        render(data, channel.lang),
        file=discord.File(BytesIO(data['nazar_img']), filename='nazar.png'),
    )
    return channel.id
