# -*- coding: utf-8 -*-
# Copyright 2018-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import json
import websocket

from .exceptions import AlreadyConnectedException, NotRunningException

logger = logging.getLogger(__name__)


class websocketdClient:

    _url_fmt = '{scheme}://{host}{port}{prefix}'

    def __init__(self,
                 host,
                 port='',
                 prefix='/api/websocketd',
                 token=None,
                 verify_certificate=True,
                 wss=True,
                 debug=False,
                 **kwargs):
        self.host = host
        self._port = port
        self._prefix = prefix
        self._token_id = token
        self._wss = wss
        self._verify_certificate = verify_certificate

        if debug:
            websocket.enableTrace(debug)

        self._ws_app = None
        self._is_running = False
        self._callbacks = {}

    def set_token(self, token):
        if self._is_running:
            raise AlreadyConnectedException()
        self._token_id = token

    def subscribe(self, event_name):
        self._ws_app.send(json.dumps({
            'op': 'subscribe',
            'data': {
                'event_name': event_name
            }
        }))

    def on(self, event, callback):
        self._callbacks[event] = callback

    def trigger_callback(self, event, data):
        if self._callbacks.get(event):
            self._callbacks[event](data)

    def _start(self):
        msg = {'op': 'start'}
        self._ws_app.send(json.dumps(msg))

    def init(self, msg):
        if msg.get('op') == 'init':
            for event in self._callbacks.keys():
                self.subscribe(event)
            self._start()

        if msg.get('op') == 'start':
            self._is_running = True

    def ping(self, payload):
        if not self._ws_app:
            raise NotRunningException()

        self._ws_app.send(json.dumps({
            'op': 'ping',
            'data': {
                'payload': payload
            }
        }))

    def on_message(self, ws, message):
        msg = json.loads(message)

        if not self._is_running:
            self.init(msg)
        else:
            if msg.get('op') == 'event':
                self.trigger_callback(msg['data']['name'], msg['data'])

    def on_error(self, ws, error):
        logger.warning('Error "%s"', error)

    def on_close(self, ws):
        logger.debug('Stopping connection ...')

    def on_open(self, ws):
        logger.debug('Starting connection ...')

    def update_token(self, token):
        self._ws_app.send(json.dumps({
            'op': 'token',
            'data': {
                'token': token
            }
        }))

    def url(self):
        base = self._url_fmt.format(
            scheme='wss' if self._wss else 'ws',
            host=self.host,
            port=':{}'.format(self._port) if self._port else '',
            prefix=self._prefix,
        )
        return '{}/?version=2'.format(base)

    def headers(self):
        return ["X-Auth-Token: {}".format(self._token_id)]

    def run(self):

        # websocket-client doesn't play nice with methods
        def on_open(ws):
            self.on_open(ws)

        def on_close(ws):
            self.on_close(ws)

        def on_message(ws, message):
            self.on_message(ws, message)

        def on_error(ws, error):
            self.on_error(ws, error)

        try:
            self._ws_app = websocket.WebSocketApp(
                self.url(),
                header=self.headers(),
                on_message=on_message,
                on_open=on_open,
                on_error=on_error,
                on_close=on_close,
            )

            kwargs = {}
            if not self._verify_certificate:
                kwargs['sslopt'] = {'cert_reqs': False}
            self._ws_app.run_forever(**kwargs)

        except Exception as e:
            logger.warning('Websocketd connection error %s', e)
