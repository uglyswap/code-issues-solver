# Rapport d'audit et corrections - code-issues-solver

Audit exhaustif (sécurité, correctness, concurrence, données, UX/accessibilité, DevOps) puis corrections.
Méthode : audit multi-agents par sous-système + sweeps transversales, vérification adversariale de chaque finding contre le code réel, puis corrections appliquées et vérifiées (compilation, import réel de l'app, smoke test SQLite end-to-end, type-check UI, validation docker-compose).

Total : 187 findings bruts -> 176 confirmés (9 critical, 55 high, 61 medium, 49 low). Les corrections ci-dessous couvrent l'intégralité des bloquants et des problèmes sécurité/correctness contenus. Les éléments purement architecturaux sont listés en fin de document (décision requise).

## 1. Bloquants : l'application ne démarrait pas

| Problème | Fichier | Correction |
|---|---|---|
| Erreur de syntaxe (bloc SSRF mal inséré, variable `provider` inexistante) | `backend/app/routers/providers.py` | Fonction `list_provider_models` restructurée, validation SSRF hors du `try` ; `test_provider` durci aussi |
| `crud.get_user` inexistant -> 500 sur TOUT endpoint authentifié | `backend/app/dependencies.py:32` | Remplacé par `crud.get_user_by_id` + parsing `sub` robuste |
| 14 fichiers corrompus par un placeholder `$(cat /opt/data/...)` (déploiement raté) | voir §2 | Restaurés depuis la dernière version git saine |
| Workers : `get_db()` ne committait JAMAIS -> toutes les écritures (tickets, statuts, logs) perdues au rollback de fermeture | `workers/app/tasks.py` | `get_db` converti en contextmanager commit-on-exit |
| Engine async réutilisé entre `asyncio.run()` (event loops distincts) -> "Future attached to a different loop" | `workers/app/tasks.py`, `workers/app/session_worker.py` | `poolclass=NullPool` |
| Session continue tuée à 10 min par le TimeLimit Dramatiq par défaut | `workers/app/session_worker.py` | `time_limit=7 jours` sur l'acteur |
| Service `workers` absent de docker-compose (cœur du produit jamais lancé) | `docker-compose.yml` | Service `workers` ajouté |

## 2. Fichiers corrompus restaurés (contenu réel perdu)

`nginx.conf`, `scripts/reset_password.py`, `scripts/migrate_dashboard_fields.py`, et tout le cœur UI : `ui/src/types/index.ts`, `App.tsx`, `services/api.ts`, `components/Layout.tsx`, `pages/AgentsPage.tsx`, `DashboardPage.tsx`, `ExecutionsPage.tsx`, `ProvidersPage.tsx`, `SessionPage.tsx`, `SessionsPage.tsx`, `TicketDetailPage.tsx`.

Restaurés depuis la version git saine la plus récente. Note : de rares ajouts UI postérieurs à la corruption (ex : bouton "model list" du commit `e2a9564`) ne sont pas récupérables depuis git ; le backend correspondant existe (endpoint `/providers/{id}/models`).

## 3. Sécurité

- **Mismatch schéma `SuccessfulPatch`** (`AttributeError` garanti, base de connaissances jamais alimentée) : schéma `SuccessfulPatchCreate` réaligné sur le modèle + appelant `tasks.py` corrigé.
- **Lazy-load async** `recent_exec.tickets` (`MissingGreenlet`) : requête explicite. `backend/app/routers/webhooks.py`.
- **IDOR inter-projet sur les secrets** : `update`/`delete` vérifient désormais l'appartenance au `project_id`. `backend/app/routers/secrets.py`.
- **Admin par défaut `admin/admin1234` loggé en clair** : mot de passe via `ADMIN_PASSWORD` (env) ou généré aléatoirement, jamais codé en dur. `backend/app/seed.py`.
- **Token GitHub en clair dans l'URL de clone + stderr -> logs DB/prompt LLM** : token masqué dans toutes les sorties, `GIT_TERMINAL_PROMPT=0`, clone `--depth 1`. `workers/app/tasks.py`.
- **SSRF webhook de déploiement** (POST vers URL contrôlée) : `validate_url_no_ssrf` avant POST. `tasks.py` + `session_worker.py`.
- **SSRF providers** (`test`/`models`) : validation ajoutée. `backend/app/routers/providers.py`.
- **Exfiltration d'identifiants test-app via redirection** : `follow_redirects=False` sur le POST de login. `backend/app/routers/projects.py`.
- **CORS** : `allow_credentials=False` (auth Bearer, pas de cookies) + parsing `CORS_ORIGINS` depuis env (liste JSON ou CSV). `main.py`, `config.py`.
- **JWT** : claim `exp` désormais exigé à la vérification. `backend/app/security.py`.
- **WebSocket sessions** : re-validation utilisateur (existe + actif) et existence de session avant abonnement ; itération broadcast sur copie (anti-mutation concurrente). `backend/app/routers/sessions.py`.
- **Prompt injection / SSTI** : données non fiables encadrées + `SandboxedEnvironment` Jinja. `agents/app/base_agent.py`.
- **github_client** : `path`/`ref` désormais url-encodés (anti path traversal/injection). `integrations/app/github_client.py`.
- **GITHUB_WEBHOOK_SECRET** désormais injecté (requis) + `ENVIRONMENT=production` dans compose (active le garde-fou des secrets faibles). `docker-compose.yml`.
- **Headers de sécurité nginx** (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy). `nginx.conf`, `nginx.ui.conf`.

## 4. Correctness / concurrence / robustesse

- Tickets bloqués en statut transitoire sur exception : statut `failed` posé. `tasks.py`.
- Race `send()`/`commit()` : commit avant chaque `.send()` inter-acteurs. `tasks.py`.
- `retry_ticket` : garde `max_retries` (anti-boucle). `tickets.py`.
- `update_ticket` : `status` contraint à une liste blanche. `tickets.py`.
- Dashboard : `total_tickets` respecte le filtre `project_id`. `dashboard.py`.
- Fuite client httpx LLM : `agent.client.close()` après usage. `tasks.py` (+ `aclose()` sur `BaseAgent`).
- LLM client : parsing défensif (RuntimeError explicite), retry/backoff 429/5xx. `integrations/app/llm_client.py`.
- github_client : retry + respect rate limit, fichiers >1MB via `download_url`. `integrations/app/github_client.py`.
- `run_json` robuste (extraction JSON multi-stratégie). `base_agent.py`.
- Playwright : `goto` avec timeout, `stop()` défensif par ressource, `start()` nettoyé sur échec, args conteneur (`--no-sandbox`, `--disable-dev-shm-usage`), listeners bornés (anti-fuite mémoire). `browser/app/driver.py`.
- Crawler : erreurs remontées au lieu d'être avalées, screenshots horodatés à la microseconde. `browser/app/crawler.py`.
- `DateTime(timezone=True)` partout + FK `ondelete` (Agent.provider_id, AuditLog) cohérents. `backend/app/models.py`.
- `context_enrichment` : `except` nu -> `except SyntaxError`.

## 5. UI / UX / Accessibilité

- Accessibilité (WCAG) : `<label htmlFor>`/`id` sur tous les formulaires (Login, Projects, Secrets, filtres Tickets), `aria-label`+`aria-hidden` sur les boutons icône, `role="alert"`/`aria-live`, `autoComplete`, `:focus-visible` global, `role="log"` sur les logs live.
- UX : confirmation avant suppression (Projects/Secrets) + `onError`, états empty/error/404 gérés, boutons submit `disabled` pendant mutation (anti double-soumission), reset des logs SSE au changement d'exécution.
- Sécurité front : `queryClient.clear()` au logout/401 (anti-fuite de cache entre comptes), validation mot de passe à l'inscription.

## 6. DevOps

- docker-compose : `REDIS_URL` dupliquée/corrompue supprimée, service `workers` ajouté, healthcheck backend réel (`/health`), secrets requis.
- Dockerfiles : healthcheck `/health` corrigé, `playwright install --with-deps` + cache lisible non-root, `npm install` (pas de lockfile requis).
- CI : `needs` inter-workflow invalide -> `workflow_run`, SSH durci (`ssh-keyscan` au lieu de `StrictHostKeyChecking=no`, secrets), env de test pour e2e, `safety scan`.
- `auto-repair.yml` : signature HMAC `X-Hub-Signature-256` calculée (l'appel passait sinon en 401).
- `.dockerignore` créé, `.gitignore` renforcé, deps dev/prod séparées (`requirements-dev.txt`).

## 7. Recommandations NON appliquées (décision/arbitrage requis)

Ces points sont structurels : ils changent l'architecture ou risquent de casser des données existantes. Documentés volontairement plutôt que corrigés unilatéralement.

1. **Isolation multi-tenant / IDOR généralisé** (BACK-02/SEC-12) : aucune ressource (`Project`, `Secret`, `Ticket`, ...) n'a de `owner_id`. Tout utilisateur authentifié accède à tout, et `/register` est public. Si l'app doit être multi-utilisateurs : ajouter `owner_id` + migration + filtrage partout. Si elle est mono-tenant (admin) : restreindre `/register` et introduire un rôle admin. **Décision produit nécessaire.**
2. **Migration Alembic obsolète** (DATA-01) : `2024_06_20_init.py` ne contient ni `sessions`, ni `bug_patterns`, ni `successful_patches`, ni les colonnes dashboard de `tickets`. Masqué au runtime par `Base.metadata.create_all` (anti-pattern). Recommandation : régénérer une migration complète et retirer `create_all` du lifespan.
3. **Dérivation de clé Fernet par simple SHA-256** (BACK-13) : pas de sel ni KDF lent, pas de versionnage de clé (rotation impossible). Changer le KDF casserait le déchiffrement des secrets existants -> nécessite une stratégie de migration des données.
4. **Application de patch "cosmétique"** : `create_pull_request` commite le diff dans `patches/fix-N.patch` au lieu d'appliquer réellement le patch aux fichiers (comportement marqué "simplified" dans le code).
5. **WebSocket temps réel cross-process** : `session_worker` (process Dramatiq) appelle `manager.broadcast`, mais `manager` est en mémoire du process API -> les logs temps réel n'atteignent pas les clients WS. Nécessite un pub/sub Redis.
6. **Sessions DB longues dans les workers** (CONC-03/12) : une exécution/session tient une connexion pendant tout le crawl Playwright. Avec `NullPool` c'est fonctionnel mais monopolise une connexion ; à découpler par phases pour la montée en charge.
7. **Couverture de tests** : CI exige `--cov-fail-under=80` mais la suite est minimale et requiert Postgres/Redis. À étoffer (notamment tests d'autorisation).

## 8. Vérifications effectuées

- `python -m compileall` : OK sur tout le code Python.
- Import réel de `backend.app.main` (66 routes) + `create_all` (12 tables) sur SQLite : OK.
- Smoke test end-to-end : `get_user_by_id`, JWT `exp` requis, création `SuccessfulPatch` (fix de schéma), chiffrement/déchiffrement secret, `dashboard.total_tickets` filtré : OK.
- Import des workers/intégrations/agents/browser : OK.
- UI `npm run type-check` : 0 erreur.
- `docker compose config -q` : OK.
