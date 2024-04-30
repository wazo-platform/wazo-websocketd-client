# Copyright 2018-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import json
import logging
import time
from functools import cached_property
from typing import Any, Callable

from websocket import WebSocketApp, enableTrace

from .exceptions import AlreadyConnectedException, NotRunningException

logger = logging.getLogger(__name__)


class WebsocketdClient:
    _url_fmt = '{scheme}://{host}{port}{prefix}'

    def __init__(
        self,
        host: str,
        port: str = '',
        prefix: str = '/api/websocketd',
        token: str | None = None,
        verify_certificate: bool = True,
        wss: bool = True,
        debug: bool = False,
        **kwargs: Any,
    ):
        self.host = host
        self._port = port
        self._prefix = prefix
        self._token_id = token
        self._wss = wss
        self._verify_certificate = verify_certificate

        if debug:
            enableTrace(debug)

        self._ws_app: WebSocketApp | None = None
        self._is_running = False
        self._callbacks: dict[str, Callable[[dict[str, Any]], None]] = {}

    def set_token(self, token: str) -> None:
        if self._is_running:
            raise AlreadyConnectedException()
        self._token_id = token

    def subscribe(self, event_name: str) -> None:
        self._send_op('subscribe', {'event_name': event_name})

    def on(self, event: str, callback: Callable[[dict[str, Any]], None]) -> None:
        self._callbacks[event] = callback

    def trigger_callback(self, event: str, data: dict[str, Any]) -> None:
        if '*' in self._callbacks:
            self._callbacks['*'](data)
        elif self._callbacks.get(event):
            self._callbacks[event](data)

    def _start(self) -> None:
        self._send_op('start')

    def init(self, msg: dict[str, Any]) -> None:
        if msg.get('op') == 'init':
            for event in self._callbacks:
                self.subscribe(event)
            self._start()

        if msg.get('op') == 'start':
            self._is_running = True

    def _send_op(self, op: str, data: dict[str, Any] | None = None) -> None:
        if self._ws_app is None:
            raise NotRunningException()
        payload: dict[str, str | dict] = {'op': op}
        if data is not None:
            payload['data'] = data
        self._ws_app.send(json.dumps(payload))

    def ping(self, payload: str) -> None:
        self._send_op('ping', {'payload': payload})

    def on_message(self, ws: WebSocketApp, message: str) -> None:
        msg = json.loads(message)

        if not self._is_running:
            self.init(msg)
        else:
            if msg.get('op') == 'event':
                self.trigger_callback(msg['data']['name'], msg['data'])

    def on_error(self, ws: WebSocketApp, error: BaseException) -> None:
        logger.error('WS encountered an error: %s: %s', type(error).__name__, error)
        if isinstance(error, KeyboardInterrupt):
            raise error

    def on_close(self, ws: WebSocketApp) -> None:
        logger.debug('WS closed.')
        self._is_running = False

    def on_open(self, ws: WebSocketApp) -> None:
        logger.debug('Starting connection ...')

    def update_token(self, token: str) -> None:
        self._send_op('token', {'token': token})

    @cached_property
    def url(self) -> str:
        base = self._url_fmt.format(
            scheme='wss' if self._wss else 'ws',
            host=self.host,
            port=f':{self._port}' if self._port else '',
            prefix=self._prefix,
        )
        return f'{base}/?version=2'

    @property
    def headers(self) -> list[str]:
        return [f"X-Auth-Token: {self._token_id}"]

    @property
    def is_running(self) -> bool:
        return self._is_running

    def run(self) -> None:
        # websocket-client doesn't play nice with methods
        def on_open(ws: WebSocketApp) -> None:
            self.on_open(ws)

        def on_close(ws: WebSocketApp) -> None:
            self.on_close(ws)

        def on_message(ws: WebSocketApp, message: str) -> None:
            self.on_message(ws, message)

        def on_error(ws: WebSocketApp, error: BaseException) -> None:
            self.on_error(ws, error)

        try:
            self._ws_app = WebSocketApp(
                self.url,
                header=self.headers,
                on_message=on_message,
                on_open=on_open,
                on_error=on_error,
                on_close=on_close,
            )

            kwargs: dict[str, Any] = {}
            if not self._verify_certificate:
                kwargs['sslopt'] = {'cert_reqs': False}
            self._ws_app.run_forever(**kwargs)

        except Exception as e:
            logger.error('Websocketd connection error: %s: %s', type(e).__name__, e)

    def stop(self) -> None:
        if self._ws_app is not None:
            self._ws_app.close()
            self._is_running = False
        while self._is_running is True:
            logger.debug('Waiting for websocketd-client to exit')
            time.sleep(1)
        self._callbacks.clear()
        self._ws_app = None
