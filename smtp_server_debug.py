# this script is the same as the following command:
# aiosmtpd -n -c aiosmtpd.handlers.Debugging -l localhost:8025

import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Debugging


async def main():
    handler = Debugging()
    controller = Controller(handler, hostname='localhost', port=8025)
    controller.start()

    print(f"SMTP server running on localhost:8025")

    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    asyncio.run(main())
