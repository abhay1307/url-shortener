# url-shortener
Distributed URL shortener with real-time click analytics. Built with FastAPI, PostgreSQL, Redis (cache-aside), RabbitMQ (async click events), and Docker. Handles 10K+ req/min with p99 &lt; 200ms.
