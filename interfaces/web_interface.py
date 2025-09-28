from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import uvicorn
from datetime import datetime

from core.chat_manager import LegalChatManager

# Pydantic models for API
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    session_stats: Dict
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    stats: Dict
    timestamp: str

class LegalRAGAPI:
    def __init__(self, chat_manager: LegalChatManager):
        self.app = FastAPI(title="Legal RAG API", version="1.0.0")
        self.chat_manager = chat_manager
        self._setup_middleware()
        self._setup_routes()

    def _setup_middleware(self):
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            return {"message": "Legal RAG API is running"}
        
        @self.app.post("/chat", response_model=ChatResponse)
        async def chat_endpoint(request: ChatRequest):
            try:
                session_id = request.session_id or f"web_{datetime.now().timestamp()}"
                
                response = await self.chat_manager.chat(
                    request.query, 
                    session_id, 
                    request.context
                )
                
                session_stats = self.chat_manager.get_session_stats(session_id)
                
                return ChatResponse(
                    response=response,
                    session_id=session_id,
                    session_stats=session_stats,
                    error=None
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            return HealthResponse(
                status="healthy",
                stats=self.chat_manager.get_global_stats(),
                timestamp=datetime.now().isoformat()
            )
        
        @self.app.get("/sessions/{session_id}/history")
        async def get_session_history(session_id: str):
            try:
                history = await self.chat_manager.get_conversation_history(session_id)
                return {
                    "session_id": session_id,
                    "message_count": len(history),
                    "messages": history
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the API server"""
        uvicorn.run(self.app, host=host, port=port)