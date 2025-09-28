from typing import List, Dict, Any, Optional, Annotated, Literal
from pydantic import BaseModel, Field
import operator

class MultiCountryLegalState(BaseModel):
    messages: Annotated[List[Dict[str, Any]], operator.add] = Field(default_factory=list)
    legal_context: Dict[str, str] = Field(
        default_factory=lambda: {
            "jurisdiction": "Unknown",
            "user_type": "general",
            "document_type": "legal",
            "detected_country": "unknown"  # Changé de None à "unknown"
        }
    )
    session_id: Optional[str] = None
    last_search_query: Optional[str] = None
    detected_articles: Annotated[List[str], operator.add] = Field(default_factory=list)
    router_decision: Optional[str] = None
    search_results: Optional[str] = None
    route_explanation: Optional[str] = None

class RoutingResult(BaseModel):
    country: Literal["benin", "madagascar", "unclear"]
    confidence: Literal["high", "medium", "low"]
    method: str
    explanation: str

class SearchResult(BaseModel):
    documents: List[Any]
    detected_articles: List[str]
    applied_filters: Dict[str, Any]
    query: str
    country: str