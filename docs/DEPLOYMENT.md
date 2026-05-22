# Bwtz War Machine - Server Deployment Guide (Hetzner)

**Target Server**: Hetzner VPS  
**IP**: `91.98.121.41`  
**Domain (current)**: `war.xtremerippleprotocol.online`  
**Brand**: Xtreme Ripple Protocol – Bear Witness $BWTZ

---

## 1. DNS Setup (Do this first)

1. Go to your domain registrar / DNS provider for `xtremerippleprotocol.online`
2. Create an **A record**:
   - Name: `war`
   - Value: `91.98.121.41`
   - TTL: 300 (or lowest available)

Wait for DNS to propagate (usually 5–30 minutes). You can check with:
```bash
dig war.xtremerippleprotocol.online
```

---

## 2. Initial Server Setup

SSH into your Hetzner server:

```bash
ssh root@91.98.121.41
```

Run the following commands:

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose plugin
apt install docker-compose-plugin -y

# Install Caddy (automatic HTTPS)
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install caddy -y

# Verify installations
docker --version
docker compose version
caddy version
```

---

## 3. Prepare the Project on the Server

```bash
# Create project directory
mkdir -p /opt/bwtz-war-machine
cd /opt/bwtz-war-machine

# Clone the repository (replace with your actual repo URL after pushing to GitHub)
git clone <your-repo-url> .

# Copy environment file (you must create this with real values)
cp .env.example .env
nano .env   # Edit with real credentials (especially X API keys + Postgres password)
```

**Important**: Never commit real secrets. Use a strong random password for `POSTGRES_PASSWORD`.

---

## 4. Deploy with Production Compose

```bash
# Start the full production stack (Caddy + services)
docker compose -f docker-compose.prod.yml up -d --build

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f caddy agent-orchestrator worker
```

---

## 5. Firewall Recommendations (Very Important)

### Hetzner Cloud Firewall (Control Panel)
Create a firewall and attach it to the server with these rules:

**Inbound**:
- Allow SSH (port 22) from your IP only (strongly recommended)
- Allow HTTP (80) and HTTPS (443) from anywhere
- **Deny everything else** (especially do not allow 5432, 8001, 8008, etc.)

### UFW on the Server (optional but recommended)
```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 5432
ufw deny 8001
ufw deny 8008
ufw enable
```

---

## 6. Accessing the Dashboard

Once DNS has propagated and the stack is running:

→ **https://war.xtremerippleprotocol.online**

Caddy will automatically obtain a Let's Encrypt certificate.

---

## 7. Updating the Code Later

```bash
cd /opt/bwtz-war-machine
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 8. Monitoring & Maintenance

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs --tail=100 -f

# Restart a specific service
docker compose -f docker-compose.prod.yml restart worker

# Check database
docker exec -it bwtz-postgres psql -U bwtz -d bwtz_war_machine
```

---

## Next Steps / Future Improvements

- Move domain from `war.xtremerippleprotocol.online` → `bwtz.online`
- Add monitoring (Prometheus + Grafana or Uptime Kuma)
- Set up automated backups for Postgres
- Add fail2ban for SSH
- Consider using Docker Swarm or Portainer for easier management

---

**Need help?**  
Run this on the server and paste the output if you get stuck:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=50
```

This setup is designed to be simple, secure, and easy to maintain on Hetzner.