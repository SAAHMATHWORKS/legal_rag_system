from datetime import datetime
from typing import Dict, List
import logging

class LegalRAGMonitor:
    """Monitoring and error tracking for the legal RAG system"""
    
    def __init__(self):
        self.error_log = []
        self.performance_metrics = {
            "query_times": [],
            "routing_accuracy": [],
            "retrieval_success_rate": 0
        }
        self.alerts = []

    def log_error(self, error_type: str, message: str, context: Dict = None):
        """Log errors for analysis"""
        error_entry = {
            "timestamp": datetime.now(),
            "type": error_type,
            "message": message,
            "context": context or {}
        }
        self.error_log.append(error_entry)
        logging.error(f"[{error_type}] {message}")
        
        # Check for alert conditions
        self._check_alerts(error_type, error_entry)

    def track_query_performance(self, query_time: float, success: bool):
        """Track query performance metrics"""
        self.performance_metrics["query_times"].append(query_time)
        
        # Update success rate
        current_rate = self.performance_metrics["retrieval_success_rate"]
        total_queries = len(self.performance_metrics["query_times"])
        
        if success:
            self.performance_metrics["retrieval_success_rate"] = (
                (current_rate * (total_queries - 1) + 1) / total_queries
            )

    def get_health_report(self) -> Dict:
        """Generate system health report"""
        query_times = self.performance_metrics["query_times"]
        
        return {
            "error_count": len(self.error_log),
            "recent_errors": self.error_log[-5:],
            "avg_query_time": sum(query_times) / len(query_times) if query_times else 0,
            "success_rate": self.performance_metrics["retrieval_success_rate"],
            "total_queries": len(query_times),
            "active_alerts": len(self.alerts)
        }

    def _check_alerts(self, error_type: str, error_entry: Dict):
        """Check if error should trigger an alert"""
        # Example alert conditions
        if error_type == "database_connection":
            self.alerts.append({
                "type": "critical",
                "message": "Database connection failure",
                "timestamp": datetime.now(),
                "error": error_entry
            })
        
        # Clean old alerts (keep only last 24 hours)
        cutoff_time = datetime.now().timestamp() - (24 * 3600)
        self.alerts = [
            alert for alert in self.alerts 
            if alert["timestamp"].timestamp() > cutoff_time
        ]

class AlertManager:
    """Manage system alerts and notifications"""
    
    def __init__(self):
        self.alerts = []
        self.subscribers = []

    def add_alert(self, alert_type: str, message: str, severity: str = "warning"):
        """Add a new alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now(),
            "acknowledged": False
        }
        self.alerts.append(alert)
        self._notify_subscribers(alert)

    def acknowledge_alert(self, alert_index: int):
        """Acknowledge an alert"""
        if 0 <= alert_index < len(self.alerts):
            self.alerts[alert_index]["acknowledged"] = True

    def subscribe(self, callback):
        """Subscribe to alert notifications"""
        self.subscribers.append(callback)

    def _notify_subscribers(self, alert):
        """Notify all subscribers of a new alert"""
        for subscriber in self.subscribers:
            try:
                subscriber(alert)
            except Exception as e:
                logging.error(f"Error notifying subscriber: {e}")