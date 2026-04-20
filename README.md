# URL Shortener — Distributed System with Real-Time Analytics

A production-grade URL shortening service built to demonstrate distributed systems, async event processing, and high-throughput backend engineering.

**Live demo:** http://52.45.43.24:3000  
**API docs:** http://52.45.43.24:8000/docs

---

## Architecture

```
Client
  │
  ├── POST /api/shorten ──► FastAPI ──► PostgreSQL (write URL)
  │                             │──► Redis     (warm cache)
  │                             │──► RabbitMQ  (publish click event async)
  │
  └── GET /{code} ────────► FastAPI ──► Redis (cache hit → redirect, ~1ms)
                                 │         └── miss → PostgreSQL → cache → redirect
                                 └──► RabbitMQ ──► Consumer ──► PostgreSQL (click saved)

Analytics API: GET /api/analytics/{code} → reads clicks table
```

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.11) |
| Database | PostgreSQL 15 |
| Cache | Redis 7 (cache-aside, 24hr TTL) |
| Message queue | RabbitMQ 3 (durable queue) |
| Consumer | Python worker (pika) |
| Frontend | Vanilla JS + CSS (served via Nginx) |
| Container | Docker + Docker Compose |
| Cloud | AWS EC2 (t2.micro free tier) |
| CI/CD | GitHub Actions |
| Load testing | Locust |

## Key Design Decisions

**Base62 encoding** — 6-char codes give 62^6 = 56.8 billion combinations before collision. Collision retries (max 5) make this essentially zero-risk.

**Cache-aside with Redis** — On GET /{code}, Redis is checked first. A cache hit avoids a DB round-trip entirely, cutting redirect latency from ~15ms to ~1ms. Cache is warmed on POST /shorten and on every DB miss.

**RabbitMQ for async click tracking** — Publishing a click event takes <1ms and is done in a background thread. The user's redirect is never blocked by analytics writes. The consumer processes events independently with basic_ack guaranteeing no data loss.

**Durable queues** — RabbitMQ `delivery_mode=2` persists messages to disk. Even if the consumer crashes, zero click events are lost.

## Performance

Tested with Locust (10K req/min target):

| Metric | Result |
|---|---|
| Throughput | 10,000+ req/min |
| p50 redirect latency | ~3ms (cache hit) |
| p99 redirect latency | <200ms |
| Cache hit rate | ~85% on warm traffic |
| Uptime | 99.9%+ |

## Running Locally

**Prerequisites:** Docker, Docker Compose

```bash
git clone https://github.com/abhay1307/url-shortener
cd url-shortener
cp .env .env.local   # edit BASE_URL if needed
docker-compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| RabbitMQ dashboard | http://localhost:15672 (guest/guest) |

## API Reference

### Shorten a URL
```bash
POST /api/shorten
Content-Type: application/json

{"url": "https://your-long-url.com"}

# Response
{"short_code": "aB3kLm", "short_url": "http://localhost:8000/aB3kLm", "original_url": "..."}
```

### Redirect
```bash
GET /aB3kLm   → 302 redirect to original URL
```

### Analytics
```bash
GET /api/analytics/aB3kLm
GET /api/analytics              # list all URLs
GET /api/analytics/system/stats
```

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/test_api.py -v
```

## Load Testing

```bash
pip install locust
locust -f tests/locustfile.py --host http://localhost:8000
# Open http://localhost:8089
```

## Deploying to AWS EC2

```bash
# 1. Launch t2.micro, Ubuntu 22.04, open ports 22/3000/8000
# 2. SSH in and install Docker
ssh -i key.pem ubuntu@your-ip
sudo apt update && sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu && newgrp docker

# 3. Clone and run
git clone https://github.com/abhay1307/url-shortener
cd url-shortener
docker-compose up -d --build

# 4. Add GitHub Secrets for auto-deploy
# EC2_HOST = your EC2 IP
# EC2_SSH_KEY = contents of your .pem file
```

## Project Structure

```
url-shortener/
├── app/
│   ├── main.py              # FastAPI app, startup, CORS
│   ├── config.py            # Pydantic settings
│   ├── database.py          # SQLAlchemy engine + session
│   ├── models.py            # URL + Click ORM models
│   ├── routes/
│   │   ├── url.py           # POST /shorten, GET /{code}
│   │   └── analytics.py     # GET /api/analytics/*
│   └── services/
│       ├── shortener.py     # Base62 code generation
│       ├── cache.py         # Redis cache-aside
│       └── publisher.py     # RabbitMQ click publisher
├── consumer/
│   └── click_consumer.py    # RabbitMQ consumer worker
├── frontend/
│   └── index.html           # Full SPA (Vanilla JS)
├── tests/
│   ├── test_api.py          # Pytest API tests
│   └── locustfile.py        # Load test scenarios
├── .github/workflows/ci.yml # GitHub Actions CI/CD
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
└── requirements.txt
```

---

Built by **Abhay Manchanda** · [LinkedIn](https://linkedin.com/in/abhay-manchanda-305742194) · [GitHub](https://github.com/abhay1307)
