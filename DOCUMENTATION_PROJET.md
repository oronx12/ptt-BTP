# Documentation Complète — Projet PTT BTP SaaS
> Rédigée le 11 mars 2026 — Explications techniques accessibles

---

## TABLE DES MATIÈRES

1. [Vue d'ensemble — Le grand tableau](#1-vue-densemble)
2. [Ton application avant (local)](#2-ton-application-avant)
3. [Ce qu'on a construit : une application SaaS](#3-ce-quon-a-construit)
4. [Les outils externes — À quoi sert chacun ?](#4-les-outils-externes)
   - GitHub
   - Render
   - Supabase / PostgreSQL
   - Cloudflare R2
5. [Les concepts techniques expliqués simplement](#5-les-concepts-techniques)
   - Git & Commit
   - Branch / main
   - Push / Pull
   - Deploy
   - Variable d'environnement
   - Base de données & ORM
   - Blueprint Flask
   - Presigned URL
6. [Le flux complet : de ton PC à l'utilisateur final](#6-le-flux-complet)
7. [Résumé de toutes les étapes réalisées](#7-résumé-des-étapes)
8. [Schéma de l'architecture](#8-schéma-architecture)
9. [Tableau récapitulatif des outils](#9-tableau-récapitulatif)
10. [Glossaire rapide](#10-glossaire)

---

## 1. Vue d'ensemble

Avant, ton application PTT BTP tournait **uniquement sur ton PC**.
Maintenant, elle est disponible **sur Internet pour n'importe qui**, avec des comptes utilisateurs, des données stockées dans le cloud, et des fichiers sauvegardés automatiquement.

```
AVANT                          APRÈS
──────────────────────         ─────────────────────────────────────────
Ton PC uniquement        →     Accessible depuis n'importe où
Pas de connexion         →     Login / mot de passe par utilisateur
Fichiers sur ton disque  →     Fichiers dans le cloud (Cloudflare R2)
Pas de sauvegarde        →     Historique des fiches dans une base de données
Un seul utilisateur      →     Multi-utilisateurs avec rôles (admin/client)
```

---

## 2. Ton application avant (local)

L'application de départ était une **application Flask Python** qui tournait sur `http://localhost:5000`.

**Ce qu'elle faisait :**
- Lire un fichier Excel pour récupérer les côtes théoriques
- Permettre la saisie des mesures terrain
- Générer une fiche PDF de réception topographique
- Gérer les profils en travers (éditeur canvas)
- Gérer les points kilométriques

**Ses limites :**
- Utilisable seulement sur ton PC
- Aucune gestion d'utilisateurs
- Fichiers Excel stockés localement
- Aucun historique sauvegardé

---

## 3. Ce qu'on a construit : une application SaaS

**SaaS = Software as a Service** = un logiciel accessible via Internet, comme Gmail ou Notion.

On a transformé ton app locale en SaaS en ajoutant :

| Fonctionnalité ajoutée | Outil utilisé |
|------------------------|--------------|
| Hébergement web (accessible 24h/24) | **Render** |
| Gestion du code source | **GitHub** |
| Comptes utilisateurs + login | **Flask-Login + PostgreSQL** |
| Base de données en ligne | **Supabase (PostgreSQL)** |
| Stockage des fichiers Excel et PDF | **Cloudflare R2** |
| Architecture multi-clients | **Blueprints Flask** |

---

## 4. Les outils externes

---

### GITHUB — Le "coffre-fort" de ton code

**Adresse :** github.com/oronx12/ptt-BTP

**En une phrase :** GitHub garde une copie de tout ton code, avec l'historique de tous les changements.

**Analogie :** Imagine que tu travailles sur un document Word. GitHub, c'est comme si chaque fois que tu sauvegardes, il gardait **toutes les versions précédentes** et les labels ("version du 10 mars", "correction du bug X"). Tu peux revenir en arrière à tout moment.

**Dans notre projet, GitHub sert à :**
1. Stocker tout le code source de l'application
2. Déclencher automatiquement le redéploiement sur Render à chaque modification
3. Garder l'historique de chaque modification (commits)
4. Permettre la collaboration si d'autres développeurs rejoignent le projet

**Commandes utilisées :**
```bash
git add fichier.py          # Marquer un fichier comme "à sauvegarder"
git commit -m "message"     # Créer un point de sauvegarde avec un message
git push                    # Envoyer les sauvegardes vers GitHub
git log                     # Voir l'historique des sauvegardes
```

---

### RENDER — L'hébergeur web (le "serveur")

**Adresse :** render.com → ton app : https://ptt-btp.onrender.com

**En une phrase :** Render est un ordinateur dans le cloud qui fait tourner ton application en permanence.

**Analogie :** Ton PC fait tourner l'app sur `localhost:5000`, mais il est éteint la nuit. Render, c'est un PC qui ne s'éteint jamais (ou presque), connecté à Internet, que tout le monde peut atteindre.

**Dans notre projet, Render sert à :**
1. Faire tourner ton app Flask 24h/24
2. Exécuter `gunicorn wsgi:app` (le serveur de production)
3. Fournir une URL publique (`https://ptt-btp.onrender.com`)
4. Se redeployer automatiquement à chaque push sur GitHub
5. Stocker les variables d'environnement (mots de passe, clés API) de façon sécurisée

**Fichiers de configuration Render dans ton projet :**
```
Procfile     → dit à Render comment lancer l'app
              contenu : web: gunicorn wsgi:app --workers 2 --timeout 120

render.yaml  → configuration générale du service Render

.python-version → force Python 3.11 (Render utiliserait Python 3.14 sinon)
                  contenu : 3.11.9
```

**Note importante sur le plan gratuit :**
Render Free Tier "dort" après 15 minutes d'inactivité. La première visite après une longue pause peut prendre 50 secondes. C'est normal.

---

### SUPABASE / POSTGRESQL — La base de données

**Adresse :** supabase.com → projet connecté à ton app

**En une phrase :** Supabase héberge ta base de données PostgreSQL dans le cloud.

#### Qu'est-ce qu'une base de données ?

C'est comme un ensemble de **tableaux Excel ultra-puissants** stockés en ligne.

Exemple — la table `users` ressemble à :
```
id | nom          | email              | mot_de_passe | is_admin | client_id
1  | Jean Dupont  | jean@example.com   | (crypté)     | true     | NULL
2  | Marie Martin | marie@chantier.fr  | (crypté)     | false    | 1
```

#### Qu'est-ce que PostgreSQL ?

PostgreSQL (souvent abrégé "Postgres") est le **logiciel** qui gère les tables.
Supabase est l'**hébergeur** qui fait tourner PostgreSQL dans le cloud.

**C'est comme :** Excel est le logiciel, Google Sheets est l'hébergeur.

#### Tables créées dans notre projet :

```
users              → comptes utilisateurs (nom, email, mot de passe, rôle)
clients            → sociétés clientes (nom, projet, clé R2 du fichier Excel)
fiches_reception   → historique des fiches générées (projet, section, opérateur, lien R2)
```

**Connexion à Supabase depuis Render :**
```
Variable d'environnement DATABASE_URL =
postgresql://postgres.xxx:mot_de_passe@aws-1-eu-central-1.pooler.supabase.com:5432/postgres
```

**Pourquoi "Session Pooler" ?**
Le plan gratuit Supabase limite le nombre de connexions simultanées. Le "Session Pooler" (port 5432) est un intermédiaire qui optimise ces connexions.

---

### CLOUDFLARE R2 — Le stockage de fichiers

**En une phrase :** R2 est un espace de stockage en ligne pour tes fichiers (Excel, PDF/HTML des fiches).

**Analogie :** C'est comme Google Drive ou Dropbox, mais accessible via une API pour les développeurs.

**Dans notre projet, R2 stocke :**
```
data/clients/1/modele.xlsx          → fichier Excel du client 1
data/clients/2/modele.xlsx          → fichier Excel du client 2
fiches/1/20260310_143022.html       → fiche de réception archivée (client 1)
fiches/2/20260311_091500.html       → fiche de réception archivée (client 2)
```

**Comment on accède aux fichiers R2 ?**
Via des **URLs signées** (presigned URLs) : des liens temporaires (valables 1h) générés automatiquement qui permettent d'accéder à un fichier sans le rendre public.

**Pourquoi R2 et pas stocker sur Render ?**
Les fichiers sur Render sont **effacés à chaque redéploiement**. R2 garde les fichiers de façon permanente.

**Variables R2 dans Render :**
```
R2_ENDPOINT         = https://xxx.r2.cloudflarestorage.com
R2_BUCKET           = ptt-btp-models
R2_ACCESS_KEY_ID    = clé publique
R2_SECRET_ACCESS_KEY= clé privée
```

---

## 5. Les concepts techniques

---

### GIT & COMMIT

**Git** est un système de contrôle de version. Il tourne sur ton PC (en local).

**Un commit** = un point de sauvegarde dans l'historique du code.

**Analogie :** Imagine que tu joues à un jeu vidéo. Un commit, c'est comme **sauvegarder la partie**. Tu peux revenir à n'importe quelle sauvegarde précédente.

```bash
# Étapes pour créer un commit :

# 1. Dire à Git quels fichiers inclure dans la sauvegarde
git add app/config.py

# 2. Créer la sauvegarde avec un message descriptif
git commit -m "Fix: correction du bug de connexion"

# 3. Envoyer la sauvegarde vers GitHub
git push
```

**Chaque commit a :**
- Un **hash** : identifiant unique de 7 caractères (ex: `0df6542`)
- Un **message** : description humaine de ce qui a changé
- Une **date et heure**
- Le **contenu exact** de chaque fichier modifié

**Commits de ce projet :**
```
ada141f  chore: trigger redeploy
9a5826f  UI: modernisation réception, résultats, et fiche PDF
0df6542  Fix: strip whitespace/newline from DATABASE_URL env var
dd87bad  Feat: archivage fiches R2 + historique + UI Tailwind modernisée
9c06922  Fix: DATABASE_URL parsing + Python 3.11 via .python-version
0ce06a8  Fix: pin Python 3.11 for Render compatibility
dca8cf0  Initial commit — PTT BTP SaaS
```

---

### BRANCH / MAIN

Une **branch** (branche) est une version parallèle du code.

La branche **main** (ou master) est la branche principale — celle qui va en production.

**Analogie :** Imagine un arbre. Le tronc = main. Les branches = des versions alternatives où tu testes des choses. Dans ce projet, on travaille directement sur `main` (pour simplifier).

---

### PUSH / PULL

- **`git push`** = envoyer tes commits locaux vers GitHub (du PC vers le cloud)
- **`git pull`** = récupérer les commits de GitHub vers ton PC (du cloud vers le PC)

**Analogie :** `push` = uploader, `pull` = télécharger.

**Dans notre workflow :**
```
[Ton PC]  →  git push  →  [GitHub]  →  Auto-deploy  →  [Render]
```
Chaque push sur GitHub déclenche automatiquement un redéploiement sur Render.

---

### DEPLOY (Déploiement)

**Déployer** = mettre une version du code en production (sur le serveur accessible aux utilisateurs).

**Les étapes d'un deploy sur Render :**
1. Render détecte un nouveau commit sur GitHub
2. Render télécharge le nouveau code
3. Render installe les dépendances (`pip install -r requirements.txt`)
4. Render lance l'application (`gunicorn wsgi:app`)
5. Si tout marche → **"Deploy live"**
6. Si erreur → **"Deploy failed"** (voir les logs)

**Statuts dans l'onglet Events de Render :**
```
Deploy started   → Render a commencé le déploiement
Deploy live      → ✅ L'app est en ligne avec la nouvelle version
Deploy failed    → ❌ Une erreur a stoppé le déploiement (voir logs)
```

---

### VARIABLE D'ENVIRONNEMENT

Une **variable d'environnement** est une valeur de configuration stockée en dehors du code.

**Pourquoi ne pas mettre les mots de passe dans le code ?**
- Le code est sur GitHub → visible par tous
- Les mots de passe ne doivent JAMAIS être dans le code source

**Analogie :** Dans ton code tu écris `mot_de_passe = os.environ.get("DB_PASSWORD")`.
La vraie valeur est stockée dans Render, dans un coffre-fort séparé.

**Variables d'environnement de ce projet :**
```
DATABASE_URL         → connexion à Supabase/PostgreSQL
SECRET_KEY           → clé secrète Flask (sécurise les sessions)
FLASK_ENV            → "production" (désactive le mode debug)
R2_ENDPOINT          → URL du bucket Cloudflare R2
R2_BUCKET            → nom du bucket R2
R2_ACCESS_KEY_ID     → clé publique R2
R2_SECRET_ACCESS_KEY → clé privée R2
```

**Dans le code (`app/config.py`) :**
```python
_db_url = os.environ.get("DATABASE_URL", "").strip()
```
`os.environ.get("NOM")` lit la variable depuis l'environnement. En local, elles viennent du fichier `.env`. En production (Render), elles sont configurées dans le tableau de bord.

---

### BASE DE DONNÉES & ORM

**ORM = Object Relational Mapper**

Au lieu d'écrire du SQL brut comme :
```sql
SELECT * FROM users WHERE email = 'jean@example.com';
```

On écrit du Python grâce à **SQLAlchemy** (l'ORM utilisé) :
```python
user = User.query.filter_by(email='jean@example.com').first()
```

C'est la même chose mais en Python. SQLAlchemy traduit le Python en SQL automatiquement.

**Flask-SQLAlchemy** = intégration de SQLAlchemy dans Flask.
**Flask-Login** = gestion des sessions utilisateurs (qui est connecté ?).

**`db.create_all()`** : crée automatiquement toutes les tables dans PostgreSQL si elles n'existent pas encore. C'est appelé au démarrage de l'app.

---

### BLUEPRINT FLASK

Un **Blueprint** est une façon d'organiser les routes Flask en modules séparés.

**Sans Blueprint (monolithe) :**
```python
# app.py — tout dans un seul fichier de 3000 lignes 😰
@app.route("/")
@app.route("/login")
@app.route("/admin")
@app.route("/api/excel")
# ... tout mélangé
```

**Avec Blueprints (modulaire) :**
```
app/blueprints/
├── pages.py    → routes HTML (/, /reception, /historique)
├── api.py      → routes API (/api/excel, /api/generate-pdf, /api/fiches)
├── auth.py     → routes auth (/login, /logout)
└── admin.py    → routes admin (/admin, /admin/nouveau-client)
```

Chaque blueprint est un "mini-Flask" indépendant. Plus lisible, plus maintenable.

---

### PRESIGNED URL (URL Signée)

Une URL signée est un lien temporaire qui donne accès à un fichier privé dans R2.

**Pourquoi pas juste rendre les fichiers publics ?**
Les fiches de réception contiennent des données professionnelles confidentielles.

**Comment ça marche :**
```
1. Utilisateur clique "Consulter" sur une fiche
2. Flask appelle R2 : "génère un lien temporaire pour ce fichier"
3. R2 retourne une URL valable 1 heure
4. Flask envoie cette URL au navigateur
5. Le navigateur ouvre le fichier directement depuis R2
6. Après 1 heure, le lien expire automatiquement
```

**Dans le code (`r2_service.py`) :**
```python
def generate_presigned_url(r2_key: str, expires_in: int = 3600) -> str:
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': r2_key},
        ExpiresIn=expires_in  # 3600 secondes = 1 heure
    )
    return url
```

---

## 6. Le flux complet

### Quand un développeur modifie le code :

```
[VS Code sur ton PC]
        │
        │  git add + git commit
        ▼
[Git local — ton PC]
        │
        │  git push
        ▼
[GitHub — cloud]
        │
        │  webhook automatique (GitHub notifie Render)
        ▼
[Render — serveur]
        │  1. Télécharge le nouveau code
        │  2. pip install -r requirements.txt
        │  3. gunicorn wsgi:app
        ▼
[App en ligne — https://ptt-btp.onrender.com]
```

---

### Quand un utilisateur se connecte et génère une fiche :

```
[Navigateur utilisateur]
        │  POST /login (email + password)
        ▼
[Flask sur Render]
        │  Vérifie email/password dans PostgreSQL (Supabase)
        │  Crée une session sécurisée
        ▼
[Page réception topographique]
        │  GET /api/excel/data/Cote_Gauche
        ▼
[Flask → R2]
        │  Télécharge le fichier Excel du client depuis R2
        │  Lit et retourne les données JSON
        ▼
[Utilisateur saisit les mesures]
        │  POST /api/generate-pdf (données JSON)
        ▼
[Flask]
        │  Génère le HTML de la fiche
        │  Archive dans R2 (fiches/client_id/timestamp.html)
        │  Enregistre métadonnées dans PostgreSQL
        │  Retourne le PDF ou HTML
        ▼
[Historique (/historique)]
        │  GET /api/fiches → liste depuis PostgreSQL
        │  Clic "Consulter" → GET /api/fiches/42/url
        │  Génère URL signée R2 (1h)
        ▼
[Fichier affiché depuis R2 directement]
```

---

## 7. Résumé de toutes les étapes réalisées

### ÉTAPE 1 — Architecture Flask Application Factory
- Restructuration en `create_app()` avec Application Factory
- Création des 4 Blueprints : `pages`, `api`, `auth`, `admin`
- Ajout de `Flask-SQLAlchemy`, `Flask-Login`, `psycopg2` dans `requirements.txt`

### ÉTAPE 2 — Modèles de données (PostgreSQL)
Création des modèles dans `app/models.py` :
- `User` : id, nom, email, password_hash, is_admin, actif, client_id
- `Client` : id, nom, projet_label, excel_key (clé R2), actif
- `FicheReception` : id, client_id, user_id, r2_key, projet, section, date_reception, operateur, created_at

### ÉTAPE 3 — Authentification
- Route `/login` (POST) : vérifie email/password, crée session
- Route `/logout` : détruit la session
- `@login_required` sur toutes les pages protégées
- Mots de passe hashés avec `werkzeug.security` (jamais stockés en clair)

### ÉTAPE 4 — Dashboard Admin
- Route `/admin` : liste clients et utilisateurs
- Route `/admin/nouveau-client` : créer un client
- Route `/admin/nouvel-utilisateur` : créer un utilisateur
- Route `/admin/upload-excel/<id>` : uploader un Excel vers R2
- Route `/admin/toggle-client/<id>` : activer/désactiver un client

### ÉTAPE 5 — Intégration Cloudflare R2
- Création de `app/services/r2_service.py`
- `upload_excel()` : upload fichier Excel vers R2
- `download_excel()` : télécharge Excel depuis R2 (retourne bytes)
- `upload_fiche()` : archive HTML de fiche vers R2
- `generate_presigned_url()` : génère lien temporaire 1h

### ÉTAPE 6 — Archivage des fiches
- Ajout modèle `FicheReception` dans `models.py`
- Fonction `_archive_fiche()` dans `api.py`
- Routes `/api/fiches` et `/api/fiches/<id>/url`
- Page `/historique` avec tableau de toutes les fiches

### ÉTAPE 7 — Déploiement Render
- Création `Procfile` : `web: gunicorn wsgi:app --workers 2 --timeout 120`
- Création `.python-version` : `3.11.9`
- Fix `DATABASE_URL` : `postgres://` → `postgresql://` + `.strip()`
- Configuration des variables d'environnement dans Render
- Push GitHub → Auto-deploy sur Render

### ÉTAPE 8 — Modernisation UI
- Header Tailwind CSS cohérent sur toutes les pages
- Dashboard admin modernisé (stats cards, layout grid)
- Page login redesignée (gradient, animations)
- Page historique avec recherche et tableau
- Section résultats réception : KPI cards, badges circulaires
- Fiche PDF : header gradient, barre de progression, layout professionnel

### BUGS CORRIGÉS EN COURS DE ROUTE

| Bug | Cause | Fix |
|-----|-------|-----|
| `ModuleNotFoundError: boto3` | boto3 non installé | `pip install boto3` + ajout requirements.txt |
| Clé R2 incorrecte | Chemin `clients/1/modele.xlsx` vs `data/clients/1/modele.xlsx` | Mise à jour chemin dans admin.py et base de données |
| `git push` auth failed | Pas de TTY en terminal WSL | Push manuel en PowerShell |
| `Could not parse SQLAlchemy URL` | DATABASE_URL vide ou absent | Ajout dans Render + `.strip()` + fallback `or None` |
| `database "postgres\n" does not exist` | Retour à la ligne `\n` dans DATABASE_URL | `.strip()` dans `config.py` |
| Render utilise Python 3.14 | `runtime.txt` ignoré par Render | `.python-version` avec `3.11.9` |
| Deploy failed après `dd87bad` | Combinaison des problèmes DATABASE_URL | Fix `.strip()` → commit `0df6542` |

---

## 8. Schéma architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TON PC (développement)                    │
│                                                                   │
│  ┌─────────────┐    git push    ┌──────────────────────────────┐ │
│  │  VS Code    │ ─────────────► │  GitHub (oronx12/ptt-BTP)    │ │
│  │  Python     │                │  Stockage code + historique   │ │
│  └─────────────┘                └──────────────┬───────────────┘ │
└─────────────────────────────────────────────────│───────────────┘
                                                   │ webhook auto-deploy
                                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                     RENDER (serveur de production)               │
│                                                                   │
│  gunicorn wsgi:app                                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  Application Flask PTT BTP                   │ │
│  │                                                              │ │
│  │  Blueprint auth    → /login, /logout                        │ │
│  │  Blueprint pages   → /, /reception, /historique             │ │
│  │  Blueprint api     → /api/excel, /api/generate-pdf          │ │
│  │  Blueprint admin   → /admin, /admin/nouveau-client          │ │
│  └──────────────┬──────────────────┬────────────────────────────┘ │
│                 │                  │                              │
│         SQLAlchemy ORM        boto3 (S3)                        │
└─────────────────│──────────────────│────────────────────────────┘
                  │                  │
        ┌─────────▼────────┐  ┌──────▼────────────────────┐
        │   SUPABASE       │  │   CLOUDFLARE R2            │
        │   PostgreSQL     │  │   Stockage fichiers        │
        │                  │  │                            │
        │   Table users    │  │  data/clients/1/modele.xlsx│
        │   Table clients  │  │  fiches/1/20260310_xxx.html│
        │   Table fiches   │  │                            │
        └──────────────────┘  └────────────────────────────┘
```

---

## 9. Tableau récapitulatif des outils

| Outil | Rôle | Où ? | Gratuit ? |
|-------|------|------|-----------|
| **Git** | Versionner le code localement | Ton PC | ✅ Oui |
| **GitHub** | Héberger le code + déclencher les deploys | github.com | ✅ Oui (plan free) |
| **Render** | Faire tourner l'app en production | render.com | ✅ Oui (avec limitations) |
| **Supabase** | Base de données PostgreSQL en ligne | supabase.com | ✅ Oui (plan free) |
| **Cloudflare R2** | Stockage fichiers (Excel, HTML fiches) | cloudflare.com | ✅ Oui (10 GB free) |
| **Flask** | Framework web Python | Dans ton code | ✅ Open source |
| **SQLAlchemy** | ORM Python ↔ PostgreSQL | Dans ton code | ✅ Open source |
| **Flask-Login** | Gestion des sessions utilisateurs | Dans ton code | ✅ Open source |
| **Gunicorn** | Serveur WSGI de production | Render | ✅ Open source |
| **Tailwind CSS** | Framework CSS via CDN | Navigateur | ✅ Open source |
| **boto3** | SDK Python pour accéder à R2 | Dans ton code | ✅ Open source |

---

## 10. Glossaire

| Terme | Définition simple |
|-------|------------------|
| **Local** | Sur ton PC, accessible seulement depuis ton ordinateur |
| **Production** | L'environnement en ligne, accessible à tous les utilisateurs |
| **Git** | Logiciel de suivi des versions de ton code (installé sur ton PC) |
| **GitHub** | Site web qui héberge ton code Git dans le cloud |
| **Commit** | Un point de sauvegarde dans l'historique Git, avec un message |
| **Push** | Envoyer tes commits locaux vers GitHub |
| **Deploy** | Mettre une nouvelle version du code en production |
| **Render** | Hébergeur cloud qui fait tourner ton app Flask |
| **PostgreSQL** | Logiciel de base de données relationnelle (comme Excel mais puissant) |
| **Supabase** | Hébergeur cloud pour PostgreSQL |
| **ORM** | Couche logicielle qui traduit Python ↔ SQL (SQLAlchemy) |
| **Blueprint** | Module Flask pour organiser les routes par thème |
| **WSGI** | Interface standard entre Python et les serveurs web |
| **Gunicorn** | Serveur WSGI utilisé en production (remplace `flask run`) |
| **Variable d'environnement** | Valeur de configuration stockée hors du code (mots de passe, clés) |
| **R2** | Service de stockage de fichiers de Cloudflare (comme S3 d'Amazon) |
| **Presigned URL** | Lien temporaire (1h) pour accéder à un fichier privé dans R2 |
| **SaaS** | Software as a Service — logiciel accessible via Internet avec abonnement |
| **Hash** | Empreinte numérique irréversible d'un mot de passe (sécurité) |
| **Session** | Mémoire temporaire côté serveur qui identifie un utilisateur connecté |
| **webhook** | Signal automatique envoyé par GitHub à Render quand tu pousses du code |
| **CDN** | Réseau de distribution de contenu (ex: Tailwind CSS chargé depuis Internet) |
| **`.env`** | Fichier local (non commité) qui contient les variables d'environnement |
| **`requirements.txt`** | Liste de toutes les bibliothèques Python nécessaires au projet |

---

*Document généré automatiquement — PTT BTP SaaS — Mars 2026*
