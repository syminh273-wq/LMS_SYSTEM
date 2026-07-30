"""
to_async_iterator — bridges a blocking sync generator into a real async
generator for StreamingHttpResponse.

Why this exists
────────────────
Django's ASGIHandler (used by Daphne, required here for Channels/WebSocket)
can only stream a StreamingHttpResponse natively if `streaming_content` is
itself async-iterable. When it's a plain sync generator (which is what all
of our AI SSE services yield), Django's own StreamingHttpResponse.__aiter__
falls back to `sync_to_async(list)(self.streaming_content)` — this drains
the ENTIRE generator (i.e. runs the full RAG + LLM call to completion) in a
background thread before sending a single byte to the client. The SSE
response then arrives as one buffered burst instead of streaming token by
token (see django/http/response.py, StreamingHttpResponse.__aiter__).

Wrapping the sync generator with `to_async_iterator()` turns it into a
genuine async generator: Django detects this and streams natively, no
buffering fallback involved.
"""

from typing import AsyncGenerator, Generator, TypeVar

from asgiref.sync import sync_to_async

T = TypeVar("T")

_SENTINEL = object()


def _safe_next(it):
    return next(it, _SENTINEL)


async def to_async_iterator(sync_gen: Generator[T, None, None]) -> AsyncGenerator[T, None]:
    """Step a blocking sync generator one item at a time via a worker thread."""
    it = iter(sync_gen)
    step = sync_to_async(_safe_next, thread_sensitive=False)
    while True:
        item = await step(it)
        if item is _SENTINEL:
            return
        yield item
