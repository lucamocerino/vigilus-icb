#!/bin/bash
# ============================================
# VIGILUS — Oracle Cloud Free Tier Deploy Script
# ============================================
# Eseguire su una VM Oracle Cloud ARM (Ampere A1)
# Ubuntu 22.04 / Oracle Linux 8+
#
# Uso: curl -sSL https://raw.githubusercontent.com/lucamocerino/vigilus-icb/main/infra/deploy-oracle.sh | bash
# Oppure: bash infra/deploy-oracle.sh
# ============================================

set -e

echo "╔══════════════════════════════════════╗"
echo "║  VIGILUS — Italy Crisis Board        ║"
echo "║  Oracle Cloud Deploy                 ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Aggiorna sistema ──
echo "[1/7] Aggiornamento sistema..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# ── 2. Installa Docker ──
echo "[2/7] Installazione Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
    echo "Docker installato. Potrebbe servire logout/login per i permessi."
fi

# ── 3. Installa Docker Compose ──
echo "[3/7] Installazione Docker Compose..."
if ! command -v docker compose &> /dev/null; then
    sudo apt-get install -y -qq docker-compose-plugin
fi

# ── 4. Clona repository ──
echo "[4/7] Clonazione repository..."
cd ~
if [ -d "vigilus-icb" ]; then
    cd vigilus-icb && git pull
else
    git clone https://github.com/lucamocerino/vigilus-icb.git
    cd vigilus-icb
fi

# ── 5. Configura environment ──
echo "[5/7] Configurazione environment..."
if [ ! -f .env ]; then
    cp .env.production.example .env

    # Genera API key e password DB casuali
    API_KEY=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    DB_PASS=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 24)

    # Rileva IP pubblico
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "localhost")

    sed -i "s/API_KEY=CHANGE_ME/API_KEY=$API_KEY/" .env
    sed -i "s/DB_PASSWORD=CHANGE_ME/DB_PASSWORD=$DB_PASS/" .env
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://$PUBLIC_IP:3000,http://$PUBLIC_IP|" .env
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://postgres:$DB_PASS@db:5432/sentinella|" .env

    echo ""
    echo "  ┌─────────────────────────────────────┐"
    echo "  │ .env generato automaticamente        │"
    echo "  │ API_KEY: $API_KEY                    │"
    echo "  │ DB_PASS: $DB_PASS                    │"
    echo "  │ IP:      $PUBLIC_IP                  │"
    echo "  └─────────────────────────────────────┘"
    echo ""
fi

# ── 6. Configura firewall OS ──
echo "[6/8] Configurazione firewall..."
if command -v iptables &> /dev/null; then
    sudo iptables -I INPUT -p tcp --dport 80  -j ACCEPT 2>/dev/null || true
    sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
    sudo netfilter-persistent save 2>/dev/null || sudo iptables-save | sudo tee /etc/iptables/rules.v4 >/dev/null 2>&1 || true
fi
if command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=80/tcp  2>/dev/null || true
    sudo firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
    sudo firewall-cmd --reload 2>/dev/null || true
fi

# ── 7. Avvia con Docker Compose ──
echo "[7/8] Avvio servizi..."
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# ── 8. Applica migrazioni DB ──
echo "[8/8] Migrazioni database..."
sleep 10  # Attendi che PostgreSQL sia pronto
sudo docker compose exec -T backend alembic upgrade head 2>/dev/null || echo "Migrazioni: tabelle già aggiornate"

# ── Riepilogo ──
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_IP")
echo ""
echo "╔══════════════════════════════════════╗"
echo "║  ✅ VIGILUS DEPLOY COMPLETATO        ║"
echo "╠══════════════════════════════════════╣"
echo "║                                      ║"
echo "║  Dashboard: http://$PUBLIC_IP        ║"
echo "║  API:       http://$PUBLIC_IP/api    ║"
echo "║  Health:    http://$PUBLIC_IP/health  ║"
echo "║                                      ║"
echo "║  Comandi utili:                      ║"
echo "║  docker compose logs -f backend      ║"
echo "║  docker compose restart              ║"
echo "║  docker compose down                 ║"
echo "║                                      ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "NOTA: Apri le porte 80 e 443 nel Security List di Oracle Cloud"
echo "      Networking → Virtual Cloud Networks → Security List → Ingress Rules"
