wazo-websocketd-client
======================

A python library to connect to xivo-websocketd. WSS is used by default. Certificates
are verified by default: if you want to omit the check or use a different CA
bundle, use the verify_certificate argument when instantiating the client.

Usage:

```python
from wazo_websocketd_client import Client

events = [
    'call_created',
    'call_deleted'
]


c = Client(host, token, events)

def callback(data):
    ...data

c.on('call_created', callback) 
```
