# AI Interview Platform Backend – Production Deployment Runbook & Checklist

**Document Version:** 1.0.0  
**Target Environment:** Production (AWS EC2 / Render / Kubernetes)  

---

## 1. AWS EC2 & Systemd Setup Guide

### 1.1 EC2 Instance Initialization
1. Launch an AWS EC2 instance (`Ubuntu 22.04 LTS`, `t3.medium` minimum instance type).
2. Attach Security Group rules:
   - Port `22` (SSH - Restricted to Admin IP)
   - Port `80` (HTTP - Public)
   - Port `443` (HTTPS - Public)
3. Install Docker, Docker Compose & Nginx:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx
   sudo systemctl enable --now docker nginx
   ```

### 1.2 Systemd Service (`/etc/systemd/system/ai-interview.service`)
```ini
[Unit]
Description=AI Interview Platform FastAPI Backend Container
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/ai-interview-platform
ExecStart=/usr/bin/docker-compose up --build
ExecStop=/usr/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 1.3 SSL Certification (Let's Encrypt)
```bash
sudo certbot --nginx -d interview-ai.com -d www.interview-ai.com
```

---

## 2. Database Backup & Disaster Recovery

### 2.1 Daily Automated Backup Script (`/opt/scripts/backup_db.sh`)
```bash
#!/bin/bash
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/var/backups/postgres"
mkdir -p $BACKUP_DIR

docker exec ai_interview_postgres pg_dump -U postgres -F c ai_interview_db > "$BACKUP_DIR/backup_$TIMESTAMP.dump"
# Retain backups for 30 days
find $BACKUP_DIR -type f -mtime +30 -name "*.dump" -delete
```

### 2.2 Database Restore Procedure
To restore PostgreSQL database from dump:
```bash
docker exec -i ai_interview_postgres pg_restore -U postgres -d ai_interview_db --clean < /var/backups/postgres/backup_TIMESTAMP.dump
```

---

## 3. Pre-Deployment Verification Checklist

- [ ] Environment secrets configured in Secrets Manager (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`).
- [ ] Database migrations tested (`alembic upgrade head`).
- [ ] SSL certificates valid and auto-renewing.
- [ ] Health check endpoint [`GET /health`](file:///d:/Projects/AI%20Interview%20Platform/app/api/v1/endpoints/health.py) returning HTTP 200.
- [ ] Readiness check endpoint [`GET /ready`](file:///d:/Projects/AI%20Interview%20Platform/app/api/v1/endpoints/health.py) probing PostgreSQL, Redis, and Gemini.
- [ ] Prometheus scraper endpoint [`GET /metrics`](file:///d:/Projects/AI%20Interview%20Platform/app/api/v1/endpoints/health.py) outputting metric text.
- [ ] WebSocket handshake URI `ws://domain/ws/interviews/{id}?token=<jwt>` connecting successfully.
