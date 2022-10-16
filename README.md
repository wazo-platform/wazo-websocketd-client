# wazo-websocketd-client

An asyncio python3 library to connect to wazo-websocketd.


Usage:

```python
import asyncio
from wazo_websocketd_client import Client


async def callback(data):
    print(data)

async def main():
    c = Client(host, token=token, verify_certificate=False)
    c.on('call_created', callback)
    c.on('call_ended', callback)
    await c.run()

asyncio.run(main())
```
