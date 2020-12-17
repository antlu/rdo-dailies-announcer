import pickle  # noqa: S403

import aiofiles


async def read_file(filepath):
    if filepath.stat().st_size == 0:
        return None
    async with aiofiles.open(filepath, 'rb') as file:
        return pickle.loads(await file.read())  # noqa: S301


async def update_file(filepath, data):
    async with aiofiles.open(filepath, 'wb') as file:
        await file.write(pickle.dumps(data))


async def get_by_session(session, url, response_fmt):
    response = await session.get(url)
    if response_fmt == 'json':
        return await response.json(encoding='UTF-8')
    elif response_fmt == 'bytes':
        return await response.read()
    raise ValueError('Unknown response format')
