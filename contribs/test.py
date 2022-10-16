#!/usr/bin/env python3

import asyncio

from wazo_auth_client import Client as Auth
from wazo_websocketd_client import Client as WebSocket


username = ""
password = ""
host = ""

events = [
    'call_created',
    'call_ended'
]

def get_token():
    auth = Auth(host, username=username, password=password, verify_certificate=False)
    token_data = auth.token.new('wazo_user', expiration=3600)
    return token_data['token']

async def callback(data):
    print(data)

async def main():
    token = get_token()
    ws = WebSocket(host, token=token, verify_certificate=False)
    for event in events:
        ws.on(event, callback) 

    await ws.run()

asyncio.run(main())
