# -*- coding: utf-8 -*-
# Copyright 2018-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import json
import websocket

from .exceptions import AlreadyConnectedException

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

    def on_message(self, message):
        msg = json.loads(message)

        if not self._is_running:
            self.init(msg)
        else:
            self.trigger_callback(msg['name'], msg['data'])

    def on_error(self, error):
        logger.warning('Error "%s"', error)

    def on_close(self):
        logger.debug('Stopping connection ...')

    def on_open(self):
        logger.debug('Starting connection ...')

    def url(self):
        base = self._url_fmt.format(
            scheme='wss' if self._wss else 'ws',
            host=self.host,
            port=':{}'.format(self._port) if self._port else '',
            prefix=self._prefix,
        )
        return '{}/'.format(base)

    def headers(self):
        return ["X-Auth-Token: {}".format(self._token_id)]

    def run(self):
        try:
            self._ws_app = websocket.WebSocketApp(
                self.url(),
                header=self.headers(),
                on_message=self.on_message,
                on_open=self.on_open,
                on_error=self.on_error,
                on_close=self.on_close,
            )

            kwargs = {}
            if not self._verify_certificate:
                kwargs['sslopt'] = {'cert_reqs': False}
            self._ws_app.run_forever(**kwargs)

        except Exception as e:
            logger.warning('Websocketd connection error %s', e)
