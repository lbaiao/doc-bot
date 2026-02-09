We are having the following error when triggering the `DBSessionRegistry.ensure` method, via `post_message` endpoint at `apit/routers/chats.py`:

ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/uvicorn/protocols/http/httptools_impl.py", line 401, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/fastapi/applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/applications.py", line 113, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/middleware/errors.py", line 187, in __call__
    raise exc
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/middleware/errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/middleware/cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/middleware/cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/middleware/exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 62, in wrapped_app
    raise exc
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 51, in wrapped_app
    await app(scope, receive, sender)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/routing.py", line 715, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/routing.py", line 735, in app
    await route.handle(scope, receive, send)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 62, in wrapped_app
    raise exc
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 51, in wrapped_app
    await app(scope, receive, sender)
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/starlette/routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/fastapi/routing.py", line 301, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/home/lucas/dev/doc-bot/api/venv/lib/python3.14/site-packages/fastapi/routing.py", line 212, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/lucas/dev/doc-bot/api/app/routers/chats.py", line 120, in post_message
    default_registry.ensure(str(chat.document_id))
    ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/lucas/dev/doc-bot/api/session/db_registry.py", line 149, in ensure
    doc = self._run_sync(check_exists())
  File "/home/lucas/dev/doc-bot/api/session/db_registry.py", line 103, in _run_sync
    return loop.run_until_complete(coro)
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "uvloop/loop.pyx", line 1512, in uvloop.loop.Loop.run_until_complete
  File "uvloop/loop.pyx", line 1505, in uvloop.loop.Loop.run_until_complete
  File "uvloop/loop.pyx", line 1379, in uvloop.loop.Loop.run_forever
  File "uvloop/loop.pyx", line 524, in uvloop.loop.Loop._run
RuntimeError: Cannot run the event loop while another loop is running

---

This is related to the async loops at `DBSessionRegistry`. Fix this error, please.
