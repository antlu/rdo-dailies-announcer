import asyncio
from datetime import datetime, date, time, timedelta
from pathlib import Path
import pickle
from io import BytesIO

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from decouple import config
import discord
from discord.ext import tasks, commands

filepath = Path('db.pickle')
filepath.touch()
SOURCE_URL = 'https://rdodailies.com/'
bot = commands.Bot(command_prefix='^')

async def read_db():
    if filepath.stat().st_size == 0:
        return
    async with aiofiles.open(filepath, 'rb') as file:
        return pickle.loads(await file.read())

async def update_db(data):
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

def parse_data(html):
    CATEGORIES = ('general', 'bounty', 'trader', 'collector', 'moonshiner', 'naturalist')
    soup = BeautifulSoup(html, 'html.parser')
    parsed_day = str(soup.find('span', class_='daily-challenges-date-selection').string)
    dailies = {}
    for category in CATEGORIES:
        cat_challenges = soup.find(id='{}-challenges-container'.format(category))
        strings = cat_challenges.stripped_strings
        dailies[category] = [{'number': string, 'text': next(strings)} for string in strings]
    return {
        'day': parsed_day,
        'dailies': dailies,
        'nazar_loc_img_url': soup.select_one('img[alt^="Madam"]')['src'],
        'sent_to_channels': [],
    }

async def get_data(day):
    if (data := await read_db()) is not None and data['day'] == day:
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

def render_data(data):
    strings = []
    for category, tasks in data.items():
        strings.append('**{} challenges**'.format(category.capitalize()))
        for task in tasks:
            strings.append('{0}: {1}'.format(task['text'], task['number']))
        strings.append('')
    strings.append('')
    return '\n'.join(strings)

@tasks.loop()
async def print_dailies():
    if print_dailies.current_loop > 0:
        delay = seconds_for_next_update()
        print('Sleeping for {} seconds'.format(delay))
        await asyncio.sleep(delay)
    channel = bot.get_channel(config('CHANNEL_ID', cast=int))
    day = current_day()
    while (day_data := await get_data(day)) is None:
        await asyncio.sleep(5 * 60)
    if channel.id in day_data['sent_to_channels']:
        return
    await channel.send(
        '{0}\n\n{1}'.format(day, render_data(day_data['dailies'])),
        file=discord.File(BytesIO(day_data['nazar_img']), filename='nazar.png'),
    )
    day_data['sent_to_channels'].append(channel.id)
    await update_db(day_data)

@print_dailies.before_loop
async def before():
    await bot.wait_until_ready()
    print("Bot started")

print_dailies.start()
bot.run(config('BOT_TOKEN'))
