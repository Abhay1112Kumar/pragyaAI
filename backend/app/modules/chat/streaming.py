from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar


TokenCallback = Callable[[str], None]

_token_callback: ContextVar[TokenCallback | None] = ContextVar(
    "pragyaai_token_callback",
    default=None,
)


@contextmanager
def capture_tokens(callback: TokenCallback):
    token = _token_callback.set(callback)
    try:
        yield
    finally:
        _token_callback.reset(token)


def emit_token(content: str) -> None:
    callback = _token_callback.get()
    if callback is not None and content:
        callback(content)
