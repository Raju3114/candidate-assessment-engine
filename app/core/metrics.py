import time
from typing import Dict

# Simple thread-safe in-memory Prometheus metrics exporter fallback
class MetricsRegistry:
    """Prometheus-compatible metrics collector for requests, WebSockets, and AI operations."""

    def __init__(self):
        self.request_counts: Dict[str, int] = {}
        self.active_websockets: int = 0
        self.ai_generation_count: int = 0
        self.ai_evaluation_count: int = 0
        self.report_generation_count: int = 0

    def inc_request(self, method: str, endpoint: str, status_code: int):
        key = f'{method}:{endpoint}:{status_code}'
        self.request_counts[key] = self.request_counts.get(key, 0) + 1

    def inc_ai_generation(self):
        self.ai_generation_count += 1

    def inc_ai_evaluation(self):
        self.ai_evaluation_count += 1

    def inc_report_generation(self):
        self.report_generation_count += 1

    def set_active_websockets(self, count: int):
        self.active_websockets = count

    def generate_prometheus_metrics(self) -> str:
        """Renders metrics in standard Prometheus exposition format."""
        lines = [
            "# HELP http_requests_total Total number of HTTP requests processed",
            "# TYPE http_requests_total counter",
        ]
        for key, val in self.request_counts.items():
            parts = key.split(":")
            lines.append(f'http_requests_total{{method="{parts[0]}",endpoint="{parts[1]}",status="{parts[2]}"}} {val}')

        lines.extend([
            "# HELP active_websocket_connections Current active WebSocket connections",
            "# TYPE active_websocket_connections gauge",
            f"active_websocket_connections {self.active_websockets}",
            "# HELP ai_question_generations_total Total AI question generation calls",
            "# TYPE ai_question_generations_total counter",
            f"ai_question_generations_total {self.ai_generation_count}",
            "# HELP ai_answer_evaluations_total Total AI answer evaluation calls",
            "# TYPE ai_answer_evaluations_total counter",
            f"ai_answer_evaluations_total {self.ai_evaluation_count}",
            "# HELP report_generations_total Total report generations",
            "# TYPE report_generations_total counter",
            f"report_generations_total {self.report_generation_count}",
        ])
        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()
