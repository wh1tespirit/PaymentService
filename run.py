import asyncio

import uvicorn


async def main():
    uvicorn.run("api.asgi:app", host="0.0.0.0", port=1337, reload=True)


if __name__ == "__main__":
    asyncio.run(main())
