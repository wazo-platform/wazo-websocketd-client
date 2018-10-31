#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import websocket
import json


class websocketdClient:
    def __init__(self, host, token, events):
        self.host = host
        self.token = token
        self.events = events
        self.started = False
        self.ws = None
        self.callbacks = dict()

    def subscribe(self, event_name):
        self.ws.send(json.dumps({
            'op': 'subscribe',
            'data': {
                'event_name': event_name
            }
        }))

    def on(self, event, callback):
        self.callbacks[event] = callback

    def triggerCallback(self, event, data):
        if self.callbacks.get(event):
            self.callbacks[event](data)

    def _start(self):
        msg = {'op': 'start'}
        self.ws.send(json.dumps(msg))

    def init(self, msg):
        if msg.get('op') == 'init':
            for event in self.events:
                self.subscribe(event)
            self._start()

        if msg.get('op') == 'start':
            self.started = True

    def on_message(self, message):
        msg = json.loads(message)

        if not self.started:
            self.init(msg)
        else:
            self.triggerCallback(msg['name'], msg['data'])

    def on_error(self, error):
        print "### error {} ###".format(error)

    def on_close(self):
        print "### closed ###"

    def on_open(self):
        print "### open ###"

    def run(self):
        websocket.enableTrace(False)
        try:
            self.ws = websocket.WebSocketApp("wss://{}/api/websocketd/".format(self.host),
                                        header=["X-Auth-Token: {}".format(self.token)],
                                        on_message = self.on_message,
                                        on_open = self.on_open,
                                        on_error = self.on_error,
                                        on_close = self.on_close)
            self.ws.on_open = self.on_open
            self.ws.run_forever(sslopt={"cert_reqs": False})
        except Exception as e:
            print 'connection error to wazo', e
