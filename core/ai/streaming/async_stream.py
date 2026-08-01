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
