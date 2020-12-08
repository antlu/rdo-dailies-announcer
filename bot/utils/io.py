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
