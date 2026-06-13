# Deployment Guide — Guinée Academy

## Table of Contents
1. [Prérequis](#prérequis)
2. [Développement Local](#développement-local)
3. [Déploiement Docker](#déploiement-docker)
4. [Déploiement Production](#déploiement-production)
5. [Configuration Base de Données](#configuration-base-de-données)
6. [Configuration Redis](#configuration-redis)
7. [Configuration Email](#configuration-email)
8. [Configuration Stockage Fichiers](#configuration-stockage-fichiers)
9. [Monitoring & Observabilité](#monitoring--observabilité)
10. [Dépannage](#dépannage)

---

## Prérequis

### Environnement de Développement
| Outil | Version | Requis |
|-------|---------|--------|
| Python | 3.11+ | ✅ |
| Node.js | 18+ | ✅ |
| PostgreSQL | 14+ | Recommandé (SQLite possible en dev) |
| Redis | 7+ | Recommandé (optionnel en dev) |
| Git | 2.30+ | ✅ |

### Environnement de Production
| Outil | Version | Requis |
|-------|---------|--------|
| Docker | 24+ | ✅ |
| Docker Compose | 2.20+ | ✅ |
| PostgreSQL | 15+ | ✅ |
| Redis | 7+ | ✅ |
| Nginx | 1.24+ | ✅ (reverse proxy) |

---

## Développement Local

### 1. Cloner et Configurer
```bash
git clone https://github.com/skaba89/guinee-academy.git
cd guinee-academy

# Backend
cd backend
cp .env.example .env
# Éditer .env avec vos paramètres

# Frontend
cd ..
npm install
```

### 2. Base de Données (Développement)
```bash
# Option A: SQLite (défaut en dev, pas besoin de PostgreSQL)
# L'application crée automatiquement les tables au démarrage

# Option B: PostgreSQL
# Configurer DATABASE_URL dans .env
cd backend
alembic upgrade head
```

### 3. Démarrer les Services
```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
npm run dev
```

### 4. Exécuter les Tests
```bash
# Backend
cd backend
DATABASE_URL="sqlite:///./test_guinee_academy.db" python -m pytest tests/ -v

# Frontend
npm test

# E2E (requiert un serveur en cours d'exécution)
npx playwright test
```

---

## Déploiement Docker

### Docker Compose (Recommandé)
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://sfp:${DB_PASSWORD}@postgres:5432/guinee_academy
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  frontend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://backend:8000

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: guinee_academy
      POSTGRES_USER: sfp
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redisdata:/data
    ports:
      - "6379:6379"

volumes:
  pgdata:
  redisdata:
```

### Commandes
```bash
# Démarrer
docker compose up -d

# Migrer la DB
docker compose exec backend alembic upgrade head

# Voir les logs
docker compose logs -f backend

# Arrêter
docker compose down
```

---

## Déploiement Production

### Variables d'Environnement Obligatoires
```env
# Sécurité
SECRET_KEY=votre-clé-secrète-de-minimum-32-caractères
DEBUG=False
ENVIRONMENT=production

# Base de données
DATABASE_URL=postgresql://user:pass@host:5432/dbname
DATABASE_URL_SYNC=postgresql://user:pass@host:5432/dbname
DATABASE_URL_ASYNC=postgresql+asyncpg://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://:password@host:6379/0

# CORS
CORS_ORIGINS=https://votre-domaine.com

# Sentry (recommandé)
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_ENVIRONMENT=production
```

### Configuration Nginx
```nginx
server {
    listen 443 ssl http2;
    server_name votre-domaine.com;

    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API Backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Rate limiting
        limit_req zone=api burst=20 nodelay;
    }

    # Docs API (restreindre en production)
    location /docs {
        # Optionnel: restreindre par IP
        # allow 10.0.0.0/8;
        # deny all;
        proxy_pass http://127.0.0.1:8000;
    }
}

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
```

### Sécurité PostgreSQL (RLS)
```sql
-- Activer RLS sur les tables critiques
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE grades ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Politique par défaut: deny all
CREATE POLICY "Tenant isolation" ON students
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- Le super-utilisateur de l'app peut tout voir
CREATE POLICY "Super admin bypass" ON students
    USING (current_setting('app.is_super_admin', true) = 'true');
```

---

## Configuration Base de Données

### Migrations
```bash
# Créer une migration
cd backend
alembic revision --autogenerate -m "Description de la migration"

# Appliquer les migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Voir l'état
alembic current
```

### Sauvegardes
```bash
# Sauvegarde complète
pg_dump -h host -U user -d dbname > backup_$(date +%Y%m%d).sql

# Restauration
psql -h host -U user -d dbname < backup_20260613.sql
```

---

## Configuration Redis

### Persistence
```bash
# Dans redis.conf
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfilename "appendonly.aof"
```

### Memory
```bash
maxmemory 256mb
maxmemory-policy allkeys-lru
```

---

## Configuration Email

### SMTP
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe-app
SMTP_FROM=noreply@votre-domaine.com
```

---

## Configuration Stockage Fichiers

### Stockage Local
```env
STORAGE_TYPE=local
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760  # 10MB
```

### Stockage S3/MinIO
```env
STORAGE_TYPE=s3
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=guinee_academy-uploads
S3_REGION=eu-west-1
```

---

## Monitoring & Observabilité

### Sentry
- Configurer `SENTRY_DSN`
- Les données sensibles (Authorization, X-Tenant-ID, Cookie) sont automatiquement supprimées avant envoi
- `send_default_pii=False` par défaut (RGPD)

### Prometheus Metrics
- Endpoint: `GET /metrics`
- Métriques disponibles: requêtes par endpoint, latence, erreurs, taux de succès auth

### Health Check
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "version": "1.0.0"}
```

---

## Dépannage

### Problèmes Courants

| Symptôme | Cause | Solution |
|----------|-------|----------|
| 400 Bad Request sur toutes les routes | `DATABASE_URL` mal formatée | Vérifier le format `postgresql://user:pass@host:5432/db` |
| Tokens invalidés au redémarrage | `SECRET_KEY` auto-générée en mode DEBUG | Définir un `SECRET_KEY` fixe |
| CORS bloqué | `CORS_ORIGINS` non configuré | Ajouter le domaine du frontend |
| 429 Too Many Requests | Rate limiting déclenché | Vérifier le trafic ou ajuster les limites |
| Erreur 500 sur login | Redis indisponible | Vérifier `REDIS_URL` et la connectivité |
| Données d'un autre tenant | RLS non configuré | Exécuter les scripts RLS (PostgreSQL uniquement) |

### Logs
```bash
# Backend logs
docker compose logs -f backend --tail=100

# PostgreSQL logs
docker compose logs -f postgres --tail=100

# Redis logs
docker compose logs -f redis --tail=100
```
