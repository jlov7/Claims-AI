# from . import query_router
# from . import summarise_router
# from . import draft_router
from . import precedent_router
from . import speech_router
from . import redteam_router

# Document router needs to be imported as it's still used by the main app
from . import document_router

__all__ = [
    # "query_router",
    # "summarise_router",
    # "draft_router",
    "precedent_router",
    "speech_router",
    "redteam_router",
    "document_router",  # Ensure document_router is still exported
]
