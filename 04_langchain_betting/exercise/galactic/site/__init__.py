"""GalacticBets.gg and StarScoop: two sites, one stylesheet, one shell."""

from .render import betting_page, news_page
from .server import bind, open_betting, open_news, open_sites, stop_sites

__all__ = ["open_sites", "open_betting", "open_news", "stop_sites", "bind",
           "betting_page", "news_page"]
