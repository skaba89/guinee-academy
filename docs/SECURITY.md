# Security Documentation — Guinée Academy

## Table of Contents
1. [Architecture de Sécurité](#architecture-de-sécurité)
2. [Authentification](#authentification)
3. [Autorisation (RBAC)](#autorisation-rbac)
4. [Isolation Multi-Tenant](#isolation-multi-tenant)
5. [Gestion des Tokens JWT](#gestion-des-tokens-jwt)
6. [Protection contre les attaques courantes](#protection-contre-les-attaques-courantes)
7. [Variables d'Environnement](#variables-denvironnement)
8. [Risques Connus](#risques-connus)
9. [Checklist Déploiement Sécurisé](#checklist-déploiement-sécurisé)

---

## Architecture de Sécurité

### Stack Sécurité
| Composant | Technologie | Rôle |
|-----------|-------------|------|
| Authentification | JWT (HS256) + OAuth2 | Identification des utilisateurs |
| Autorisation | RBAC (11 rôles) | Contrôle d'accès par permissions |
| Isolation Tenant | RLS PostgreSQL + middleware | Séparation des données par établissement |
| Cache/Blacklist | Redis | Invalidation de tokens, rate limiting |
| Rate Limiting | slowapi | Protection contre les abus |
| Headers Sécurité | Middleware FastAPI | X-Content-Type-Options, X-Frame-Options, etc. |
| Monitoring | Sentry + Prometheus | Détection d'incidents |

### Flux de Requête Authentifiée
```
Client → HTTPS → Nginx/CDN → Rate Limiter → Tenant Middleware →
Auth Middleware (JWT validation + blacklist check) →
require_permission → Endpoint Handler → DB (RLS filtered)
```

---

## Authentification

### Login Flow
1. L'utilisateur soumet `username` + `password` à `POST /api/v1/auth/login/`
2. Le serveur vérifie les identifiants avec **timing-safe comparison** (hash dummy si utilisateur inexistant)
3. Un JWT est émis avec les claims: `sub`, `exp`, `iss`, `aud`, `roles`, `tenant_id`, `tv` (token version)
4. Le token est retourné au client

### Token JWT Structure
```json
{
  "sub": "user-uuid",
  "exp": 1718000000,
  "iss": "guinee-academy",
  "aud": "guinee-academy-api",
  "roles": ["TENANT_ADMIN"],
  "tenant_id": "tenant-uuid",
  "tv": 5
}
```

### Token Version (tv)
- **Objectif**: Invalider tous les tokens lors d'un logout-all
- **Mécanisme**: Redis stocke `ga:user_token_version:{user_id}` → incrémenté à chaque logout-all
- **Validation**: `validate_token_version()` compare le `tv` du token avec la version Redis

### Token Blacklist
- **Objectif**: Invalider un token spécifique lors du logout
- **Mécanisme**: Redis stocke `token_blacklist:{jti}` → TTL = temps restant du token
- **Fail-open**: Si Redis est indisponible, la blacklist n'est pas vérifiée (pour éviter de bloquer tous les utilisateurs)

---

## Autorisation (RBAC)

### Matrice des Rôles
| Rôle | Permissions clés | Restrictions |
|------|-----------------|--------------|
| SUPER_ADMIN | `*` (toutes) | Accès global, pas limité à un tenant |
| TENANT_ADMIN | users, students, grades, finance, settings | Pas de rgpd:delete, tenants:write |
| DIRECTOR | users, students, grades, analytics, audit | Pas de finance:write |
| DEPARTMENT_HEAD | grades, attendance, subjects, schedule | Pas de users:write |
| TEACHER | students:read, grades:read/write, attendance | Lecture seule la plupart |
| STUDENT | me:read, grades:read, attendance:read | Très limité |
| PARENT | me:read, students:read, grades:read | Lecture seule |
| ACCOUNTANT | finance:read/write, payments, inventory | Pas de grades ou students:write |
| SECRETARY | students:read/write, admissions, certificates | Pas de finance:write |
| STAFF | students, attendance, admissions, inventory | Pas de grades:write |
| ALUMNI | students:read, grades:read, schedule:read | Lecture seule |

### Décorateur `require_permission`
```python
from app.core.security import require_permission

@router.get("/users/", dependencies=[Depends(require_permission("users:read"))])
async def list_users(...):
    ...
```

### Gating par Plan (`require_plan`)
```python
from app.core.security import require_plan

@router.post("/ai/chat/", dependencies=[Depends(require_plan("pro"))])
async def ai_chat(...):
    ...
```

**⚠️ Fail-Open**: Si la DB est indisponible, `require_plan` autorise l'accès. Voir [Risques Connus](#risques-connus).

---

## Isolation Multi-Tenant

### Principe
Chaque établissement (tenant) a ses propres données. Les requêtes sont filtrées par `tenant_id` à deux niveaux:

1. **Application Layer**: Chaque endpoint filtre par `current_user["tenant_id"]`
2. **Database Layer (PostgreSQL)**: Row-Level Security (RLS) via `app.current_tenant_id`

### SUPER_ADMIN Cross-Tenant Access
Les SUPER_ADMIN n'ont pas de `tenant_id` fixe. Pour accéder aux données d'un établissement spécifique:
1. Le frontend envoie un header `X-Tenant-ID` avec l'UUID du tenant
2. `get_current_user()` valide le format UUID et vérifie l'existence du tenant en DB
3. Le `tenant_id` résolu est injecté dans le contexte de la requête

### Reset RLS par Requête
```python
# Dans get_current_user() — empêche les fuites du pool de connexions
db.execute(text("SELECT set_config('app.current_tenant_id', NULL::text, false)"))
```

---

## Gestion des Tokens JWT

### Création
```python
from app.core.security import create_access_token

token = create_access_token(
    data={"sub": str(user.id), "roles": roles, "tenant_id": tenant_id, "tv": token_version},
    expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
)
```

### Validation
```python
from app.core.security import verify_token

payload = verify_token(token)  # Vérifie signature, expiry, iss, aud
```

### Invalidation (Logout)
```python
# Logout simple — blackliste le token actuel
await blacklist_token(jti, remaining_ttl)

# Logout-all — invalide tous les tokens
await increment_token_version(user_id)
```

---

## Protection contre les Attaques Courantes

| Attaque | Protection | Statut |
|---------|-----------|--------|
| **Brute Force** | Rate limiting (5/min sur login) | ✅ Actif |
| **Timing Attack** | Hash dummy sur utilisateur inexistant | ✅ Actif |
| **XSS** | CSP headers, React auto-escaping | ✅ Actif |
| **CSRF** | JWT Bearer token (pas de cookie) | ✅ Actif |
| **SQL Injection** | SQLAlchemy ORM, paramètres liés | ✅ Actif |
| **IDOR** | Filtrage tenant_id + permission checks | ⚠️ Partiel |
| **Race Condition** | SELECT FOR UPDATE recommandé | ⚠️ Non implémenté |
| **Token Reuse** | Blacklist Redis + token version | ✅ Actif |
| **User Enumeration** | Timing-safe login | ✅ Actif |
| **Clickjacking** | X-Frame-Options: DENY | ✅ Actif |
| **MIME Sniffing** | X-Content-Type-Options: nosniff | ✅ Actif |
| **MITM** | HSTS (en production) | ✅ Actif |

---

## Variables d'Environnement

### Critiques (Production)
| Variable | Description | Valeur requise |
|----------|-------------|----------------|
| `SECRET_KEY` | Clé de signature JWT | Min. 32 caractères, aléatoire |
| `DATABASE_URL` | URL PostgreSQL | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | URL Redis | `redis://host:6379/0` |
| `DEBUG` | Mode debug | `False` en production |
| `ENVIRONMENT` | Environnement | `production` |

### Sécurité (Recommandées)
| Variable | Description | Défaut |
|----------|-------------|--------|
| `SENTRY_DSN` | Sentry pour monitoring | None |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie JWT | 30 |
| `CORS_ORIGINS` | Origines autorisées | None (toutes en dev) |

### ⚠️ Alertes
- **SECRET_KEY vide en production**: L'application refuse de démarrer (`os._exit(1)`)
- **DEBUG=True en production**: Clé auto-générée à chaque redémarrage → tous les tokens invalidés

---

## Risques Connus

### ✅ Critiques — Corrigés (Phase 6)

1. **IDOR sur homework submit**: ✅ CORRIGÉ — Vérification `student_id == authenticated_user.student_id`
   - Fichier: `backend/app/api/v1/endpoints/academic/homework.py`

2. **IDOR sur parents risk-scores**: ✅ CORRIGÉ — `require_permission("parents:read")` + filtre `tenant_id`
   - Fichier: `backend/app/api/v1/endpoints/operational/parents.py`

3. **Fuite tenant dans student dashboard**: ✅ CORRIGÉ — Filtre `tenant_id` ajouté à la requête enrollment
   - Fichier: `backend/app/api/v1/endpoints/academic/students.py`

4. **Fail-open require_plan**: ✅ CORRIGÉ — Fail-closed : 503 si DB indisponible
   - Fichier: `backend/app/core/security.py`

5. **95+ endpoints sans require_permission**: ✅ CORRIGÉ — Tous les endpoints ont `require_permission`
   - Fichiers: hr.py, infrastructure.py, parents.py, library.py, inventory.py, alumni.py, communication.py, school_life.py, surveys.py, clubs.py, incidents.py, departments.py, admissions.py, billing.py, tenants.py

### ✅ Corrigés (Phase 6 — Audit Complet)

6. **Conditions de course (Library)**: CORRIGÉ — Emprunts utilisent un `UPDATE ... WHERE available_copies > 0` atomique
7. **Conditions de course (Inventory)**: CORRIGÉ — `adjust_stock` utilise un `UPDATE ... WHERE stock_quantity >= :qty` atomique
8. **Conditions de course (create_order)**: CORRIGÉ — Le décrément de stock vérifie la disponibilité avant de décrémenter
9. **IDOR homework submit**: CORRIGÉ — Vérification que `student_id` correspond au profil étudiant authentifié
10. **IDOR parents risk-scores**: CORRIGÉ — `require_permission("parents:read")` + filtre `tenant_id` sur toutes les requêtes `parent_students`
11. **Fuite tenant student dashboard**: CORRIGÉ — La requête enrollment filtre maintenant par `tenant_id`
12. **Fail-open require_plan**: CORRIGÉ — Fail-closed : retourne 503 si la DB est indisponible au lieu d'autoriser l'accès
13. **Broken lambda tenants.py**: CORRIGÉ — `Depends(lambda: require_permission(...))` → `Depends(require_permission(...))`
14. **95+ endpoints sans permission**: CORRIGÉ — Ajout de `require_permission` à tous les endpoints dans: alumni (13), communication (17), school_life (21), surveys (7), clubs (7), incidents (5), departments (13), admissions (1), billing (4), tenants (7), parents (14), library (4), inventory (4), students dashboard (1)
15. **Permissions manquantes dans ROLE_PERMISSIONS**: CORRIGÉ — Ajout de permissions (parents, library, school_life, communications, surveys, clubs, incidents, departments, alumni, billing, homework, assessments, mfa) à tous les rôles appropriés

### 🟡 Majeurs (Restants)

16. **Rate limiting insuffisant**: Certains endpoints critiques non limités
    - Recommandation: Étendre le rate limiting à tous les endpoints d'écriture

17. **f-string SQL**: 55+ requêtes SQL utilisent des f-strings pour des clauses dynamiques
    - Recommandation: Utiliser des whitelists pour les noms de colonnes/tableaux dynamiques

18. **Validation Pydantic manquante**: Certains endpoints acceptent `dict` brut au lieu de modèles Pydantic
    - Recommandation: Créer des schémas Pydantic pour `surveys.py`, `communication.py` forums, `rgpd.py` consent

---

## Checklist Déploiement Sécurisé

### Avant Déploiement
- [ ] `SECRET_KEY` est défini (min. 32 caractères, pas de valeur par défaut)
- [ ] `DEBUG=False` dans l'environnement de production
- [ ] `DATABASE_URL` utilise PostgreSQL (pas SQLite)
- [ ] `REDIS_URL` est configuré et accessible
- [ ] CORS origins sont restreints au domaine de production
- [ ] HTTPS est configuré sur le reverse proxy
- [ ] HSTS est activé (Strict-Transport-Security)
- [ ] Les migrations Alembic sont à jour (`alembic upgrade head`)
- [ ] Le super-admin par défaut a changé son mot de passe

### Configuration Réseau
- [ ] L'API backend n'est pas exposée directement (passer par Nginx/CDN)
- [ ] Redis n'est pas accessible depuis Internet
- [ ] PostgreSQL n'est pas accessible depuis Internet
- [ ] Le port d'administration est filtré

### Monitoring
- [ ] Sentry est configuré avec `SENTRY_DSN`
- [ ] Les alertes sur les erreurs 401/403 sont activées
- [ ] Le rate limiting est monitoré (alerte si seuil approché)
- [ ] Les logs d'audit sont collectés et analysés

### Post-Déploiement
- [ ] Vérifier que les headers de sécurité sont présents (`curl -I https://domain/api/v1/health`)
- [ ] Vérifier que le rate limiting fonctionne (tentatives rapides → 429)
- [ ] Vérifier l'isolation tenant (créer 2 tenants, vérifier l'isolation des données)
- [ ] Tester le logout (vérifier que le token est blacklisté)
- [ ] Tester le logout-all (vérifier que tous les tokens sont invalidés)
