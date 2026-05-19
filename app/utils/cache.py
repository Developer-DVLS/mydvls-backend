import json

from app.core.redis import redis_client


async def get_cache(key: str):
    data = await redis_client.get(key)

    if data:
        return json.loads(data)

    return None


async def set_cache(
    key: str,
    value,
    expire: int = 300
):
    await redis_client.set(
        key,
        json.dumps(value),
        ex=expire
    )


async def delete_cache(key: str):
    await redis_client.delete(key)