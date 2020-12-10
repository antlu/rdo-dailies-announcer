from io import BytesIO

import aiohttp
import discord
from bs4 import BeautifulSoup

from rdo_dailies.setup import DB_PATH, SOURCE_URL, TRANSLATORS
from rdo_dailies.utils import io


def separate_number_from_text(strings_generator):
    for string in strings_generator:
        number = string
        text = next(strings_generator)
        split_text = text.split(maxsplit=1)
        if split_text[0].isnumeric() or split_text[0].startswith('$'):
            yield (split_text[0], split_text[1])
        else:
            yield (number, text)


def parse_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    parsed_day = str(soup.find('span', class_='daily-challenges-date-selection').string)
    categories = ('general', 'bounty hunter', 'trader', 'collector', 'moonshiner', 'naturalist')
    dailies = {}
    for category in categories:
        cat_challenges = soup.find(id='{0}-challenges-container'.format(category.split()[0]))
        strings = cat_challenges.stripped_strings
        dailies[category] = [
            {'number': number, 'text': text}
            for number, text in separate_number_from_text(strings)
        ]
    return {
        'day': parsed_day,
        'dailies': dailies,
        'nazar_loc_img_url': soup.select_one('img[alt^="Madam"]')['src'],
        'sent_to_channels': [],
    }


async def get_data(day):
    if (data := await io.read_file(DB_PATH)) is not None and data['day'] == day:
        return data
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.get(SOURCE_URL) as response:
            html = await response.text(encoding='UTF-8')
            parsed_data = parse_data(html)
            if parsed_data['day'] != day:
                return None
        async with session.get(parsed_data['nazar_loc_img_url']) as response:  # noqa: WPS440
            nazar_img = await response.read()  # noqa: WPS441
    parsed_data.update({'nazar_img': nazar_img})
    return parsed_data


def render_data(data, lang):
    TRANSLATORS[lang].install()
    strings = ['{0}\n'.format(data['day'])]
    for category, tasks in data['dailies'].items():
        cat_title = '{0} challenges'.format(category.capitalize())
        strings.append('__{0}__'.format(_(cat_title)))
        for task in tasks:
            strings.append('{0}: **{1}**'.format(
                _(task['text']), task['number'],
            ))
        strings.append('')
    return '\n'.join(strings)


async def send(bot, channel, data):
    discord_channel = bot.get_channel(channel.id)
    await discord_channel.send(
        render_data(data, channel.lang),
        file=discord.File(BytesIO(data['nazar_img']), filename='nazar.png'),
    )
    return channel.id
