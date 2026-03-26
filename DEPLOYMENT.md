# 🚀 Digital Twins Sync: Deployment Handbook

This guide outlines the steps to move from a **Local Prototype** to a **Production Cloud Deployment**.

## 1. Environment Hardening
For production, you must rotate all security keys. Use a 64-character hex string for the `SECRET_KEY` and `JWT_SECRET_KEY`.

**Recommended `.env` for Production:**
```bash
# Core Security
SECRET_KEY=generate_a_new_secure_key_here
JWT_SECRET_KEY=generate_a_new_secure_jwt_key_here

# Cloud Infrastructure
DATABASE_URL=postgresql://user:pass@db:5432/twin_db
REDIS_URL=redis://redis:6379/0

# AI & Automation
GEMINI_API_KEY=your_production_gemini_key
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
```

## 2. Docker Cloud Deployment
We recommend deploying using the included `docker-compose.yml`. This ensures all services (PostgreSQL, Redis, Celery, and Flask) are perfectly synchronized.

**To Deploy:**
1. Upload the project to your VPS (e.g., AWS EC2, DigitalOcean Droplet).
2. Ensure Docker and Docker Compose are installed.
3. Run the following command:
   ```bash
   docker-compose up -d --build
   ```

## 3. Public URL & SSL (Nginx)
To access the app over a public domain (e.g., `https://twinsync.yourdomain.com`), you should use Nginx as a reverse proxy.

**Nginx Configuration Sample:**
```nginx
server {
    listen 80;
    server_name twinsync.yourdomain.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade; # Important for WebSockets
        proxy_set_header Connection "Upgrade";
    }
}
```

## 4. Scaling the AI Pipeline
- **Multiple Workers:** Increase Celery workers if you have thousands of users.
  ```bash
  docker-compose up -d --scale worker=3
  ```
- **CDN:** For the fastest frontend, serve the `/static` folder via a CDN or Nginx directly.

---
**Need help with a specific Cloud Provider?** Ask me for a provider-specific implementation (e.g. AWS Lightsail or Heroku).
