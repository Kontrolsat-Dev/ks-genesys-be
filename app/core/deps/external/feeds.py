from app.external.feed_downloader import FeedDownloader


def get_feed_downloader() -> FeedDownloader:
    """Factory para injetar FeedDownloader nos routers."""
    return FeedDownloader()
