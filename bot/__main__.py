import asyncio
import logging
from collections import namedtuple
from contextlib import suppress

from discord.ext import commands, tasks

from bot.setup import BOT_TOKEN, COMMAND_PREFIX, DB_PATH, GUILDS_SETTINGS_PATH, LOCALES  # noqa: I001
from bot.utils import io
from bot.utils.data import get_data, send
from bot.utils.datetime import current_day, seconds_for_next_update

Channel = namedtuple('Channel', ['id', 'lang'], defaults=['en'])
bot = commands.Bot(command_prefix=COMMAND_PREFIX)


@tasks.loop()
async def print_dailies():
    delay = seconds_for_next_update()
    if print_dailies.current_loop > 0:
        logging.info('Sleeping for {0} seconds'.format(delay))
        await asyncio.sleep(delay)
    day = current_day()
    while (day_data := await get_data(day)) is None:
        logging.info('Waiting for new data')
        await asyncio.sleep(min(delay, 5 * 60))
    channels = (
        Channel(guild['channel_id'], guild['lang_code'])
        for guild in bot.guilds_settings.values()
    )
    channels_ids = await asyncio.gather(*(
        send(bot, channel, day_data) for channel in channels
        if channel.id not in day_data['sent_to_channels']
    ))
    day_data['sent_to_channels'].extend(channel_id for channel_id in channels_ids)
    await io.update_file(DB_PATH, day_data)


@print_dailies.before_loop
async def prepare_to_run():
    bot.guilds_settings = data if (data := await io.read_file(GUILDS_SETTINGS_PATH)) is not None else {}
    await bot.wait_until_ready()
    logging.info('Bot started')


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def add(ctx, channel_id: int, lang_code: str = 'en'):
    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send('Wrong channel ID!')
        return
    if lang_code not in LOCALES:
        await ctx.send('Available locales: {0}'.format(', '.join(LOCALES)))
        return
    bot.guilds_settings[ctx.guild.id] = {
        'channel_id': channel_id,
        'lang_code': lang_code,
    }
    await io.update_file(GUILDS_SETTINGS_PATH, bot.guilds_settings)
    await ctx.message.add_reaction('🆗')
    print_dailies.restart()


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def delete(ctx, channel_id: int):
    channels_ids = (guild['channel_id'] for guild in bot.guilds_settings.values())
    if channel_id not in channels_ids:
        await ctx.send('Wrong channel ID!')
        return
    del bot.guilds_settings[ctx.guild.id]  # noqa: WPS420
    await io.update_file(GUILDS_SETTINGS_PATH, bot.guilds_settings)
    await ctx.message.add_reaction('🆗')
    print_dailies.restart()


@bot.event
async def on_guild_remove(guild):
    with suppress(KeyError):
        del bot.guilds_settings[guild.id]  # noqa: WPS420
        await io.update_file(GUILDS_SETTINGS_PATH, bot.guilds_settings)

print_dailies.start()
bot.run(BOT_TOKEN)
