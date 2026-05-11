import time

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


REQUEST_COUNT = Counter(
    "aki_http_requests_total",
    "Total HTTP requests handled by the AKI API.",
    ["method", "path", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "aki_http_request_duration_seconds",
    "HTTP request latency in seconds for the AKI API.",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def get_route_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


async def prometheus_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    started_at = time.perf_counter()
    status_code = "500"
    route_path = request.url.path

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        route_path = get_route_path(request)
        return response
    finally:
        duration = time.perf_counter() - started_at
        REQUEST_COUNT.labels(
            method=request.method,
            path=route_path,
            status_code=status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            path=route_path,
        ).observe(duration)


def metrics_response():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
