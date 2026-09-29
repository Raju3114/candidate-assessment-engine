# Deployment & Operations Guide

## 1. Local & Containerized Deployment (Docker Compose)

```bash
docker-compose up --build -d
```
Starts `fastapi`, `postgres:16-alpine`, and `redis:7-alpine`.

---

## 2. Managed Cloud Deployment (Render)

Deploy using [`render.yaml`](file:///d:/Projects/AI%20Interview%20Platform/render.yaml) blueprint:
1. Connect GitHub repository to Render.
2. Select **New Blueprint Instance**.
3. Render automatically provisions Web Service, PostgreSQL Database, and Redis Cluster.

---

## 3. Self-Hosted Deployment (AWS EC2 + Nginx)

1. Launch EC2 instance with Ubuntu 22.04 LTS.
2. Configure Nginx reverse proxy using [`nginx.conf`](file:///d:/Projects/AI%20Interview%20Platform/nginx.conf).
3. Issue Let's Encrypt SSL certificate via Certbot:
   ```bash
   sudo certbot --nginx -d interview-ai.com
   ```

---

## 4. Monitoring & Metrics Stack

- Prometheus scraping endpoint: [`GET /metrics`](file:///d:/Projects/AI%20Interview%20Platform/app/api/v1/endpoints/health.py).
- Grafana dashboard monitors HTTP request throughput, WebSocket connections count, and AI generation latency histograms.
