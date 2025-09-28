from typing import Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

def dict_to_message_obj(d: Dict[str, Any]) -> BaseMessage:
    """Convert dictionary to LangChain message object"""
    role = d.get("role", "").lower()
    content = d.get("content", "")
    meta = d.get("meta", {}) or {}
    
    if role in ("user", "human", "humanmessage"):
        return HumanMessage(content=content, metadata=meta)
    if role in ("assistant", "ai", "aimessage"):
        return AIMessage(content=content, metadata=meta)
    return SystemMessage(content=content, metadata=meta)

def message_obj_to_dict(msg: Any) -> Dict[str, Any]:
    """Convert LangChain message object to dictionary"""
    content = getattr(msg, "content", str(msg))
    meta = getattr(msg, "metadata", {}) or {}
    
    if isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, AIMessage):
        role = "assistant"
    elif isinstance(msg, SystemMessage):
        role = "system"
    else:
        role = meta.get("role", "assistant")
        
    return {"role": role, "content": content, "meta": meta}

def validate_country_code(country: str) -> str:
    """Validate and normalize country code"""
    country = country.lower().strip()
    if country in ["benin", "bj", "bénin"]:
        return "benin"
    elif country in ["madagascar", "mg", "madagasikara"]:
        return "madagascar"
    else:
        return "unclear"

def format_legal_citation(article_number: str, law_title: str, country: str) -> str:
    """Format legal citation in standard format"""
    country_formats = {
        "benin": f"Article {article_number} du {law_title} (Bénin)",
        "madagascar": f"Article {article_number} du {law_title} (Madagascar)"
    }
    return country_formats.get(country, f"Article {article_number} du {law_title}")

def safe_get(dictionary: Dict, key: str, default: Any = None) -> Any:
    """Safely get value from dictionary with default"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, default)
    return default

def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def calculate_confidence_score(patterns_found: int, llm_confidence: str) -> float:
    """Calculate a numerical confidence score"""
    pattern_score = min(patterns_found * 0.3, 0.6)  # Max 0.6 from patterns
    llm_scores = {"high": 0.8, "medium": 0.5, "low": 0.2}
    llm_score = llm_scores.get(llm_confidence, 0.2)
    
    return min(pattern_score + llm_score, 1.0)