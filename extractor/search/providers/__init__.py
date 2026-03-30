"""Search providers for papers, repos, and patents."""
from .arxiv import search_arxiv
from .github import search_github
from .google_patents import search_google_patents

__all__ = ["search_arxiv", "search_github", "search_google_patents"]
