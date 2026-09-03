# Prometheus 指标模拟服务器(Python 移植版,对应 Go 版 manifest/docker/prometheusTestServer/main.go)
# 监听 :2112,/metrics 暴露 Prometheus 指标(每秒 ticker 更新一次),模拟 5 个接口的业务指标。
# 当前场景强制为 scAlert(告警场景,方便测试)——保留 Normal/Degraded 分支代码供学习。
# 与 Go 版差异:场景名打印去掉 emoji(Windows cmd GBK 控制台会 UnicodeEncodeError)。

import math
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# ---------- 指标定义(名称/标签/桶与 Go 版完全一致,histogram 桶必须一致否则 alert.rules 不触发) ----------
http_requests_total = Counter(
    "http_requests_total", "Total number of HTTP requests", ["handler", "method", "status_code"]
)
http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["handler", "method"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)
active_connections = Gauge("active_connections", "Current number of active connections")
error_rate = Gauge("error_rate_per_minute", "Error rate per minute (percentage)", ["handler"])
cpu_usage = Gauge("process_cpu_usage_percent", "Process CPU usage percentage (simulated)")
memory_usage = Gauge("process_memory_bytes", "Process memory usage in bytes (simulated)")
db_pool_used = Gauge("db_pool_connections_used", "Database pool connections used")
db_pool_max = Gauge("db_pool_connections_max", "Database pool max connections")
queue_depth = Gauge("message_queue_depth", "Message queue depth", ["queue"])

HANDLERS = ["/api/v1/order", "/api/v1/user", "/api/v1/payment", "/api/v1/inventory", "/api/v1/notification"]

SCENARIOS = {
    "normal": {"base_qps": 30, "error_rate": 1.0, "latency": 0.05, "cpu": 20, "queue": (10, 50), "pool": (5, 15)},
    "degraded": {"base_qps": 60, "error_rate": 10.0, "latency": 0.3, "cpu": 45, "queue": (100, 200), "pool": (30, 50)},
    "alert": {"base_qps": 120, "error_rate": 35.0, "latency": 1.5, "cpu": 85, "queue": (500, 700), "pool": (90, 100)},
}


def current_scenario() -> str:
    # 强制全天候处于告警状态,方便测试(Go 版同样写死返回 scAlert)
    return "alert"


def scenario_name_zh(sc: str) -> str:
    return {"normal": "正常", "degraded": "降级", "alert": "告警"}.get(sc, sc)


def simulate_loop():
    """每秒更新一次指标(镜像 Go ticker)"""
    while True:
        sc = current_scenario()
        params = SCENARIOS[sc]
        ts = time.time()

        for handler in HANDLERS:
            # QPS 基础值 + 正弦波动
            qps = params["base_qps"] * (1 + 0.2 * math.sin(ts / 5 + hash(handler) % 7))
            # 每秒发一次请求计数(Counter 累加,让 /metrics 有持续增量)
            for _ in range(max(1, int(qps))):
                http_requests_total.labels(handler=handler, method="POST", status_code="200").inc()
            # 部分请求进入耗时分布桶(模拟 P99 延迟≈1.5s 需要尾部大桶计数)
            err = params["error_rate"] + 5 * math.sin(ts / 3)
            http_request_duration.labels(handler=handler, method="POST").observe(params["latency"] * (1 + 0.1 * math.sin(ts / 4)))
            error_rate.labels(handler=handler).set(max(0, err))

        active_connections.set(qps * random.uniform(0.8, 1.2))
        cpu_usage.set(params["cpu"] + 5 * math.sin(ts / 2))
        memory_usage.set(512 * 1024 * 1024 + 10 * 1024 * 1024 * math.sin(ts))
        db_pool_max.set(100)
        db_pool_used.set(random.uniform(*params["pool"]))
        queue_depth.labels(queue="order_queue").set(random.uniform(*params["queue"]))
        queue_depth.labels(queue="notify_queue").set(random.uniform(*params["queue"]) * 0.5)
        queue_depth.labels(queue="payment_queue").set(random.uniform(*params["queue"]) * 0.8)

        time.sleep(1)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            body = generate_latest(REGISTRY)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/":
            body = ("test-server (Python port): Prometheus metrics simulator\n"
                    "metrics at /metrics\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # 静默访问日志


def main():
    random.seed()
    threading.Thread(target=simulate_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", 2112), MetricsHandler)
    print(f"[test-server] 指标模拟器启动 http://localhost:2112/metrics,当前场景:{scenario_name_zh(current_scenario())}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
