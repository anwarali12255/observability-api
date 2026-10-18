
import time
import uuid
import logging
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

EMAIL = "24f2006704@ds.study.iitm.ac.in"

app = FastAPI()
start_time = time.monotonic()

request_counter = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
)

logs = deque(maxlen=1000)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    request_counter.inc()

    try:
        response = await call_next(request)
    except Exception:
        logs.append({
            "level": "ERROR",
            "ts": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
            "request_id": request_id,
        })
        raise

    logs.append({
        "level": "INFO",
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "request_id": request_id,
        "method": request.method,
        "status_code": response.status_code,
        "duration_s": round(time.perf_counter() - start, 6),
    })

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/work")
async def work(n: int = Query(default=1, ge=0, le=1000000)):
    # Perform K simple units of work.
    done = 0
    for _ in range(n):
        done += 1

    return {"email": EMAIL, "done": done}


@app.get("/healthz")
async def health():
    return {
        "status": "ok",
        "uptime_s": float(max(0.0, time.monotonic() - start_time)),
    }


@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/logs/tail")
async def logs_tail(limit: int = Query(default=100, ge=1, le=1000)):
    return list(logs)[-limit:]
