# wazo-websocketd-client

A python library to connect to xivo-websocketd.


Usage:

```python
from wazo_websocketd_client import Client

c = Client(host, token=token, verify_certificate=False)

def callback(data):
    print data

c.on('call_created', callback)
c.on('call_ended', callback)

c.run()
```
