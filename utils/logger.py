import logging
import sys
from datetime import datetime
from typing import Dict, Any

def setup_logging(level=logging.INFO):
    """Setup comprehensive logging configuration"""
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # File handler
    file_handler = logging.FileHandler(f'legal_rag_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=[console_handler, file_handler],
        force=True
    )
    
    # Specific logger configurations
    legal_logger = logging.getLogger('legal_rag')
    legal_logger.setLevel(logging.DEBUG)
    
    mongodb_logger = logging.getLogger('pymongo')
    mongodb_logger.setLevel(logging.WARNING)
    
    print("✅ Logging setup completed")

class PerformanceLogger:
    """Logger for performance monitoring"""
    
    def __init__(self):
        self.metrics = {
            "query_times": [],
            "routing_times": [],
            "retrieval_times": [],
            "generation_times": []
        }
    
    def log_query_time(self, session_id: str, duration: float):
        """Log query processing time"""
        self.metrics["query_times"].append({
            "session_id": session_id,
            "duration": duration,
            "timestamp": datetime.now()
        })
        logging.info(f"Query processed in {duration:.2f}s for session {session_id}")
    
    def log_routing_decision(self, session_id: str, decision: str, confidence: str, method: str):
        """Log routing decisions"""
        logging.debug(f"Routing: session={session_id}, decision={decision}, confidence={confidence}, method={method}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        query_times = [m["duration"] for m in self.metrics["query_times"]]
        
        return {
            "total_queries": len(query_times),
            "average_query_time": sum(query_times) / len(query_times) if query_times else 0,
            "max_query_time": max(query_times) if query_times else 0,
            "min_query_time": min(query_times) if query_times else 0
        }