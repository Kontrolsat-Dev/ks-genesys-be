# app/domains/procurement/usecases/feeds/test_feed.py
from __future__ import annotations
from collections.abc import Awaitable, Callable

from app.core.errors import BadRequest
from app.schemas.feeds import FeedTestRequest, FeedTestResponse

PreviewFn = Callable[[FeedTestRequest], Awaitable[FeedTestResponse]]


async def execute(payload: FeedTestRequest, *, preview_feed: PreviewFn) -> FeedTestResponse:
    try:
        return await preview_feed(payload)
    except Exception as e:
        raise BadRequest(f"Could not preview feed: {e}") from e
