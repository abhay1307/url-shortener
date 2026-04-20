"""
Load test — run with:
  pip install locust
  locust -f tests/locustfile.py --host http://YOUR_EC2_IP:8000

Then open http://localhost:8089 and start the test.
Target: 10,000 req/min = ~167 req/sec

Or headless:
  locust -f tests/locustfile.py --host http://YOUR_EC2_IP:8000 \
    --users 200 --spawn-rate 20 --run-time 2m --headless --only-summary
"""
import random
import threading
from locust import HttpUser, task, between

SAMPLE_URLS = [
    "https://github.com/abhay1307",
    "https://www.linkedin.com/in/abhay-manchanda",
    "https://docs.python.org/3/library/asyncio.html",
    "https://fastapi.tiangolo.com/tutorial/",
    "https://redis.io/docs/manual/",
]

_lock = threading.Lock()
created_codes = []
MAX_CODES = 500


def add_code(code: str):
    with _lock:
        created_codes.append(code)
        if len(created_codes) > MAX_CODES:
            created_codes.pop(0)


def pick_code():
    with _lock:
        return random.choice(created_codes) if created_codes else None


class URLShortenerUser(HttpUser):
    wait_time = between(0.05, 0.3)

    def on_start(self):
        for url in SAMPLE_URLS[:2]:
            with self.client.post(
                "/api/shorten",
                json={"url": url},
                catch_response=True,
                name="/shorten [warmup]",
            ) as res:
                if res.status_code == 200:
                    code = res.json().get("short_code")
                    if code:
                        add_code(code)
                else:
                    res.success()

    @task(6)
    def redirect(self):
        code = pick_code()
        if not code:
            return
        with self.client.get(
            f"/{code}",
            allow_redirects=False,
            catch_response=True,
            name="/[code] redirect",
        ) as res:
            if res.status_code in (200, 301, 302, 307, 404):
                res.success()
            else:
                res.failure(f"Unexpected status: {res.status_code}")

    @task(2)
    def shorten(self):
        url = random.choice(SAMPLE_URLS)
        with self.client.post(
            "/api/shorten",
            json={"url": url},
            catch_response=True,
            name="/api/shorten",
        ) as res:
            if res.status_code == 200:
                code = res.json().get("short_code")
                if code:
                    add_code(code)
            elif res.status_code == 422:
                res.failure("Validation error")
            else:
                res.failure(f"Shorten failed: {res.status_code}")

    @task(1)
    def analytics(self):
        code = pick_code()
        if not code:
            return
        with self.client.get(
            f"/api/analytics/{code}",
            catch_response=True,
            name="/api/analytics/[code]",
        ) as res:
            if res.status_code in (200, 404):
                res.success()
            else:
                res.failure(f"Analytics error: {res.status_code}")

    @task(1)
    def health(self):
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health",
        ) as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure(f"Health check failed: {res.status_code}")