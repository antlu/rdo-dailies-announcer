import asyncio
from collections import namedtuple
from contextlib import suppress
from datetime import datetime, date, time, timedelta
import gettext
from pathlib import Path
import pickle
from io import BytesIO

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from decouple import config
import discord
from discord.ext import tasks, commands

SETTINGS_PATH = Path('settings.pickle')
SETTINGS_PATH.touch()
DB_PATH = Path('db.pickle')
DB_PATH.touch()
DOMAIN = 'messages'
LOCALEDIR_PATH = Path('locales')

SOURCE_URL = 'https://rdodailies.com/'
CATEGORIES = ('general', 'bounty hunter', 'trader', 'collector', 'moonshiner', 'naturalist')

locales = ['en'] + [child.name for child in LOCALEDIR_PATH.iterdir()]
translators = {}
for locale in locales:
    translators[locale] = gettext.translation(DOMAIN, LOCALEDIR_PATH, languages=[locale], fallback=True)

bot = commands.Bot(command_prefix=config('COMMAND_PREFIX', '^'))
Channel = namedtuple('Channel', ['id', 'lang'], defaults=['en'])

async def read_file(filepath):
    if filepath.stat().st_size == 0:
        return
    async with aiofiles.open(filepath, 'rb') as file:
        return pickle.loads(await file.read())

async def update_file(filepath, data):
    async with aiofiles.open(filepath, 'wb') as file:
        await file.write(pickle.dumps(data))

def current_day():
    return datetime.utcnow().strftime('%B %d')

def seconds_for_next_update():
    tommorow_6GMT = datetime.combine(
        date.today() + timedelta(days=1),
        time(6, second=30)
    )
    delta = tommorow_6GMT - datetime.utcnow()
    return delta.seconds

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
    dailies = {}
    for category in CATEGORIES:
        cat_challenges = soup.find(id='{}-challenges-container'.format(category.split()[0]))
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
    if (data := await read_file(DB_PATH)) is not None and data['day'] == day:
        return data
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.get(SOURCE_URL) as response:
            response.headers['date']
            html = await response.text(encoding='UTF-8')
            parsed_data = parse_data(html)
            if parsed_data['day'] != day:
                return
        async with session.get(parsed_data['nazar_loc_img_url']) as response:
            nazar_img = await response.read()
    parsed_data.update({'nazar_img': nazar_img})
    return parsed_data

def render_data(data, lang):
    translators[lang].install()
    strings = ['{}\n'.format(data['day'])]
    for category, tasks in data['dailies'].items():
        cat_title = '{} challenges'.format(category.capitalize())
        strings.append('__{}__'.format(_(cat_title)))
        for task in tasks:
            strings.append('{0}: **{1}**'.format(_(task['text']), task['number']))
        strings.append('')
    return '\n'.join(strings)

async def send(channel, data):
    if channel.id in data['sent_to_channels']:
        return (channel.id, False)
    discord_channel = bot.get_channel(channel.id)
    await discord_channel.send(
        render_data(data, channel.lang),
        file=discord.File(BytesIO(data['nazar_img']), filename='nazar.png'),
    )
    return (channel.id, True)

@tasks.loop()
async def print_dailies():
    delay = seconds_for_next_update()
    if print_dailies.current_loop > 0:
        print('Sleeping for {} seconds'.format(delay))
        await asyncio.sleep(delay)
    day = current_day()
    while (day_data := await get_data(day)) is None:
        print('Waiting for new data')
        await asyncio.sleep(min(delay, 5 * 60))
    channels = (
        Channel(guild['channel_id'], guild['lang_code'])
        for guild in bot.guilds_settings.values()
    )
    tasks_results = await asyncio.gather(*(send(channel, day_data) for channel in channels))
    day_data['sent_to_channels'].extend([result[0] for result in tasks_results if result[1]])
    await update_file(DB_PATH, day_data)

@print_dailies.before_loop
async def before():
    bot.guilds_settings = data if (data := await read_file(SETTINGS_PATH)) is not None else {}
    await bot.wait_until_ready()
    print("Bot started")

@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def add(ctx, channel_id: int, lang_code: str = 'en'):
    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send('Wrong channel ID!')
        return
    if lang_code not in locales:
        await ctx.send('Available locales: {}'.format(', '.join(locales)))
        return
    bot.guilds_settings[ctx.guild.id] = {
        'channel_id': channel_id,
        'lang_code': lang_code,
    }
    await update_file(SETTINGS_PATH, bot.guilds_settings)
    await ctx.message.add_reaction('🆗')
    print_dailies.restart()

@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def delete(ctx, channel_id: int):
    channels_ids = (guild['channel_id'] for guild in bot.guilds_settings.values())
    if channel_id not in channels_ids:
        await ctx.send('Wrong channel ID!')
        return
    del bot.guilds_settings[ctx.guild.id]
    await update_file(SETTINGS_PATH, bot.guilds_settings)
    await ctx.message.add_reaction('🆗')
    print_dailies.restart()

@bot.event
async def on_guild_remove(guild):
    with suppress(KeyError):
        del bot.guilds_settings[guild.id]
        await update_file(SETTINGS_PATH, bot.guilds_settings)

print_dailies.start()
bot.run(config('BOT_TOKEN'))
