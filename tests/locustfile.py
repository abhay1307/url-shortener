"""
Load test — run with:
  pip install locust
  locust -f tests/locustfile.py --host http://localhost:8000

Then open http://localhost:8089 and start the test.
Target: 10,000 req/min = ~167 req/sec
"""
import random
from locust import HttpUser, task, between

SAMPLE_URLS = [
    "https://github.com/abhay1307",
    "https://www.linkedin.com/in/abhay-manchanda",
    "https://docs.python.org/3/library/asyncio.html",
    "https://fastapi.tiangolo.com/tutorial/",
    "https://redis.io/docs/manual/",
]

# Store created codes to reuse for redirect tests
created_codes = []


class URLShortenerUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        # Create a few short URLs on startup
        for url in SAMPLE_URLS[:2]:
            with self.client.post(
                "/api/shorten",
                json={"url": url},
                catch_response=True,
                name="/api/shorten [warmup]",
            ) as res:
                if res.status_code == 200:
                    code = res.json().get("short_code")
                    if code:
                        created_codes.append(code)

    @task(5)
    def redirect(self):
        """Most traffic is redirects — weight 5x higher than shorten."""
        if not created_codes:
            return
        code = random.choice(created_codes)
        with self.client.get(
            f"/{code}",
            allow_redirects=False,
            catch_response=True,
            name="GET /{code} [redirect]",
        ) as res:
            if res.status_code in (301, 302, 307):
                res.success()
            else:
                res.failure(f"Expected redirect, got {res.status_code}")

    @task(2)
    def shorten(self):
        url = random.choice(SAMPLE_URLS)
        with self.client.post(
            "/api/shorten",
            json={"url": url},
            catch_response=True,
            name="POST /api/shorten",
        ) as res:
            if res.status_code == 200:
                code = res.json().get("short_code")
                if code:
                    created_codes.append(code)
                    # Cap list size to avoid memory bloat
                    if len(created_codes) > 500:
                        created_codes.pop(0)
            else:
                res.failure(f"Shorten failed: {res.status_code}")

    @task(1)
    def analytics(self):
        if not created_codes:
            return
        code = random.choice(created_codes)
        self.client.get(f"/api/analytics/{code}", name="GET /api/analytics/{code}")

    @task(1)
    def health(self):
        self.client.get("/health", name="GET /health")
