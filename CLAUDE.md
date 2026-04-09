# CLAUDE.md — RECEPTA by OPTILAB : Système de Réception Topographique BTP

> Fichier de référence projet. Toute personne (ou IA) travaillant sur ce code doit lire ce fichier en premier.
> **Dernière mise à jour : 2026-04-09** — V2 PRO planifiée + réorganisation racine + fixes email/PDF + logo RECEPTA CSS partout

---

## 1. DESCRIPTION DU PROJET

### Identité visuelle
- **RECEPTA** — nom commercial de l'outil (affiché en grand, en cyan `#00ffff`)
- **OPTILAB** — suite logicielle propriétaire (affiché en sous-titre "by OPTILAB")
- **Logo RECEPTA** : grille 2×2 de points colorés (CSS uniquement, pas de fichier image) :
  - Point 1 (haut gauche) : `#00ffff` (cyan)
  - Point 2 (haut droite) : `#fbbf24` (jaune)
  - Points 3 & 4 (bas) : `#00ffff` (cyan)
- **Page de connexion** : logo CSS dots + "RECEPTA" en `#00ffff` + badge "by OPTILAB"
- **Écran d'accueil** : spirale animée SVG (cyan/jaune) + théodolite SVG au centre
- **Ne jamais utiliser les fichiers `optilab_*.png`** pour représenter RECEPTA — utiliser le logo CSS

---

**RECEPTA** (anciennement PTT BTP / OPTILAB) est une application web Flask (Python) **SaaS multi-tenant** à usage professionnel pour les ingénieurs et techniciens du BTP.

Elle permet de :
- Créer et éditer des **profils en travers types** de routes (géométrie, couches de chaussée, éléments annexes)
- Gérer des **points kilométriques (PK)** et recalculer des coordonnées relatives
- Enregistrer des **mesures de réception topographique** terrain et les comparer aux côtes théoriques
- **Visualiser les résultats** avec code couleur (conforme/non conforme/interpolé) dans une vue dédiée
- Générer des **fiches de réception officielles** en PDF (signatures manuscrites, observations, légende)
- **Envoyer les fiches par email** aux parties prenantes (contrôleur + entreprise) via Resend
- **Archiver les fiches** sur Cloudflare R2 et les consulter dans un historique

**Public cible** : Contrôleurs topographiques, équipes chantier BTP, chefs de projet routiers.

**Modèle** : SaaS — chaque entreprise cliente a son propre compte, ses utilisateurs, et son fichier Excel modèle stocké dans le cloud.

---

## 2. STACK TECHNIQUE

| Composant | Technologie | Notes |
|-----------|-------------|-------|
| Backend | Python / Flask >= 2.3 | Application Factory pattern |
| ORM / BDD | Flask-SQLAlchemy + PostgreSQL | Hébergé sur Supabase |
| Authentification | Flask-Login | Rôles : `admin` / `client` |
| Lecture Excel | pandas >= 2.0 + openpyxl >= 3.1 | Fichiers stockés sur R2 |
| Génération PDF | **xhtml2pdf** (moteur principal sur Render) | WeasyPrint non disponible sur Render (pas de GTK) |
| Stockage cloud | **Cloudflare R2** via boto3 | Fichiers Excel clients + fiches archivées |
| Email | **Resend** (API) | Fiches de réception en pièce jointe |
| Frontend | HTML5 + CSS3 + Vanilla JS + Tailwind (pages admin/historique) | Aucun framework JS |
| Stockage inter-pages | sessionStorage navigateur | Données de session utilisateur |
| Hébergement prod | **Render** (Linux) | Via gunicorn + wsgi.py |
| Hébergement local | Waitress (Windows) | Via waitress-serve |

---

## 3. STRUCTURE DES FICHIERS

```
02_2026_Setup_app_01/
├── setup.bat                       # DÉMARRAGE Windows : double-clic pour installer + lancer
├── run.py                          # Point d'entrée développement  (python run.py)
├── wsgi.py                         # Point d'entrée production      (gunicorn wsgi:app)
├── requirements.txt                # Dépendances production
├── .env.example                    # Modèle de variables d'environnement
├── .python-version                 # Pin Python 3.11 (pour Render)
├── .gitignore
├── CLAUDE.md                       # CE FICHIER
│
├── app/                            # Package Flask principal
│   ├── __init__.py                 # Application Factory — create_app() + init extensions
│   ├── config.py                   # DevelopmentConfig / ProductionConfig / TestingConfig
│   ├── models.py                   # Modèles SQLAlchemy : Client, User, FicheReception
│   │
│   ├── blueprints/
│   │   ├── pages.py                # Routes HTML (/, /editeur, /reception, /points-kilometriques, /historique)
│   │   ├── api.py                  # Routes API (/api/excel/*, /api/*-pdf, /api/send-email, /api/download)
│   │   ├── auth.py                 # Authentification : /login, /logout
│   │   └── admin.py                # Panel admin : /admin/* (CRUD clients/users, upload Excel, sélecteur fichier test)
│   │
│   ├── services/
│   │   ├── excel_service.py        # Lecture et parsing du fichier Excel (local ou R2)
│   │   ├── pdf_service.py          # Génération PDF (xhtml2pdf + fallback HTML)
│   │   └── r2_service.py           # Cloudflare R2 : upload/download/presigned URLs
│   │
│   ├── templates/
│   │   ├── auth/
│   │   │   └── login.html          # Page de connexion
│   │   ├── admin/
│   │   │   ├── dashboard.html      # Dashboard admin (liste clients + users + sélecteur Excel test)
│   │   │   ├── client_form.html    # Formulaire création client
│   │   │   └── user_form.html      # Formulaire création utilisateur
│   │   ├── home.html               # Page d'accueil + lien "Phase Conception" (discret)
│   │   ├── index.html              # Phase Conception : Éditeur de profil (canvas)
│   │   ├── points_kilometriques.html  # Phase Conception : Gestion des PK
│   │   ├── reception_topographique.html  # Réception + visualisation + PDF + email (~5000 lignes)
│   │   ├── historique.html         # Historique des fiches archivées (R2)
│   │   └── pdf/
│   │       └── fiche_reception.html   # Template PDF/impression Jinja2
│   │
│   └── static/
│       ├── style.css               # Design system CSS global
│       └── img/                    # Images statiques
│
├── core/
│   └── profile_utils.py            # Logique géométrique pure Python (sans Flask)
│
├── data/
│   ├── Projet_Routier_Topographie.xlsx  # Fichier Excel modèle local (fallback dev)
│   ├── clients/                    # Fichiers Excel par client (fallback local R2)
│   ├── modeles_recepta/            # 4 modèles Excel assainissement générés (P1→P4)
│   ├── sources/                    # Fichiers Excel sources clients (référence)
│   └── tmp/                        # Fichiers générés temporaires (PDF, exports)
│
├── docs/                           # Documentation (DOCUMENTATION_PROJET.md, RECEPTA_V2_CONCEPTION.md)
├── scripts/                        # Scripts utilitaires (gen_modeles_v3.py, create_admin.py, r2_manager.py)
├── logo/                           # Assets logo OPTILAB
├── archive/                        # Anciennes versions — NE PAS MODIFIER
├── tests/
│   ├── __init__.py
│   └── test_profile_utils.py
└── venv/                           # Environnement virtuel Python (non commité)
```

---

## 4. VARIABLES D'ENVIRONNEMENT REQUISES

Créer un fichier `.env` à la racine (voir `.env.example`).

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `SECRET_KEY` | Prod obligatoire | Clé secrète Flask (sessions) |
| `DATABASE_URL` | Oui | URL PostgreSQL Supabase (`postgresql://...`) |
| `R2_ENDPOINT` | Oui | URL endpoint Cloudflare R2 |
| `R2_BUCKET` | Oui | Nom du bucket R2 |
| `R2_ACCESS_KEY_ID` | Oui | Clé d'accès R2 |
| `R2_SECRET_ACCESS_KEY` | Oui | Secret R2 |
| `RESEND_API_KEY` | Pour emails | Clé API Resend |
| `MAIL_FROM` | Non | Expéditeur email (défaut : `OPTILAB <noreply@ptt-btp.fr>`) |
| `FLASK_ENV` | Non | `development` / `production` (défaut : development) |

---

## 5. DÉMARRAGE DU PROJET

### Méthode simple (Windows)
Double-cliquer sur **`setup.bat`** — il fait tout automatiquement.

### Méthode manuelle
```bash
# Créer et activer le venv
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac

# Installer les dépendances
pip install -r requirements.txt

# Créer le fichier .env (copier .env.example et remplir les valeurs)
cp .env.example .env

# Lancer en développement
python run.py
# → http://localhost:5000

# Lancer en production (Windows)
waitress-serve --port=5000 wsgi:app
```

> Ne jamais utiliser `run.py` (debug=True) en production. Toujours passer par `wsgi.py`.

---

## 6. ARCHITECTURE BACKEND

### 6.1 Modèles BDD — `app/models.py`

```
Client          → entreprise cliente
  ├── nom           : str(120)
  ├── excel_key     : str(255) — clé R2 du fichier Excel modèle
  ├── projet_label  : str(200) — nom affiché dans l'app
  └── actif         : bool

User            → technicien / admin
  ├── email         : str unique
  ├── password_hash : str (Werkzeug)
  ├── nom           : str
  ├── role          : 'admin' | 'client'
  ├── client_id     → FK Client (NULL si admin)
  └── last_login    : datetime

FicheReception  → archive d'une fiche générée
  ├── r2_key        : chemin dans R2
  ├── projet, section, date_reception, operateur
  ├── client_id     → FK Client
  └── user_id       → FK User
```

### 6.2 Blueprints

| Blueprint | Préfixe | Fichier | Accès |
|-----------|---------|---------|-------|
| `pages` | `/` | `blueprints/pages.py` | `@login_required` sur toutes les pages |
| `api` | `/api/` | `blueprints/api.py` | `@login_required` sur tous les endpoints |
| `auth` | `/login`, `/logout` | `blueprints/auth.py` | Public |
| `admin` | `/admin/` | `blueprints/admin.py` | `@admin_required` (role='admin') |

### 6.3 Routes de pages (Blueprint `pages`)

| Route | Template | Rôle |
|-------|----------|------|
| `/` | `home.html` | Accueil — choix du pipeline |
| `/editeur` | `index.html` | Phase 1 — Éditeur de profil en travers |
| `/points-kilometriques` | `points_kilometriques.html` | Phase 2 — Gestion PK |
| `/reception` | `reception_topographique.html` | Phase 3 — Réception topographique |
| `/historique` | `historique.html` | Historique des fiches archivées |

### 6.4 API endpoints (Blueprint `api`)

#### `GET /api/excel/sheets`
Retourne les onglets du fichier Excel du client connecté (depuis R2 ou fallback local).
```json
{ "sheets": ["Cote_Gauche", "Cote_Droit"] }
```

#### `GET /api/excel/data/<sheet_name>`
Données d'un onglet nettoyées (NaN/Inf → null).
- Colonne PK : cherche `'PK'` ou `'KILOMETRIQUE'` dans le nom
- Colonnes côtes : toutes colonnes numériques non-PK (`pd.api.types.is_numeric_dtype()`)

#### `POST /api/generate-pdf`
Génère la fiche de réception en PDF (xhtml2pdf) ou HTML (fallback).
Archivage automatique sur R2 + enregistrement dans `FicheReception`.

#### `POST /api/preview-pdf`
Identique à `generate-pdf` mais retourne toujours du HTML (pour `window.print()`).

#### `POST /api/send-fiche-email`
Envoie la fiche par email via Resend aux signataires.
Corps : mêmes données que `generate-pdf` + liste de destinataires.

#### `GET /api/download/<filename>`
Téléchargement depuis `data/tmp/`. Protégé contre path traversal (whitelist regex `^[\w\-. ]+$`).

### 6.5 Routes admin (Blueprint `admin`)

| Route | Méthode | Action |
|-------|---------|--------|
| `/admin/` | GET | Dashboard (liste clients + users) |
| `/admin/clients/nouveau` | GET/POST | Créer un client |
| `/admin/clients/<id>/excel` | POST | Uploader l'Excel modèle → R2 |
| `/admin/clients/<id>/toggle` | POST | Activer/désactiver un client |
| `/admin/utilisateurs/nouveau` | GET/POST | Créer un utilisateur |

---

## 7. SERVICE CLOUDFLARE R2 — `app/services/r2_service.py`

| Fonction | Rôle |
|----------|------|
| `upload_excel(bytes, key)` | Upload fichier Excel client |
| `upload_fiche(bytes, key)` | Archive fiche de réception (HTML) |
| `download_excel(key)` | Télécharge Excel depuis R2 → bytes |
| `generate_presigned_url(key, 3600)` | URL signée temporaire (1h) |

Clé R2 des Excel clients : `data/clients/{client_id}/modele.xlsx`
Clé R2 des fiches : `fiches/{client_id}/{timestamp}_{projet}.html`

---

## 8. GÉNÉRATION PDF — `app/services/pdf_service.py`

- **Moteur principal** : `xhtml2pdf` (pur Python, fonctionne sur Render sans GTK)
- **Fallback** : HTML brut retourné si xhtml2pdf échoue
- **WeasyPrint** : retiré de la prod (nécessite GTK, incompatible Render)
- **Template** : `app/templates/pdf/fiche_reception.html` (Jinja2)

---

## 9. FLUX DE TRAVAIL (DATA FLOW)

### Pipeline Excel multi-onglets (principal)
```
[Chargement automatique]
  → GET /api/excel/sheets → liste des onglets
  → Promise.all([GET /api/excel/data/Cote_Gauche, GET /api/excel/data/Cote_Droit])
  → allSheetsData = { Cote_Gauche: {...}, Cote_Droit: {...} }
  → commonPKs = intersection des PK des deux onglets
        ↓
[Sélection des éléments]
  → renderColumnSelectionUI() : grille 2 colonnes (Gauche | Droite)
  → makeElementLabel("G_Roulement", "Cote_Gauche") → "Roulement (Gauche)"
        ↓
[Saisie des mesures terrain]
  → Tableau avec colonnes PK | ÉLÉMENT | Distance | LAV | Mesurée | Théorique | Écart+ | Écart-
  → Statut CSS sur <tr> : ecart-ok | ecart-positif | ecart-negatif | row-interpolated
        ↓
[Visualisation]
  → collectReceptionDataForPDF() → objet JSON complet
  → renderResultatsSection(data) : stats + tableaux colorés + légende
        ↓
[Export]
  → POST /api/generate-pdf → PDF téléchargé + archivé R2
  → POST /api/send-fiche-email → email Resend aux signataires
```

---

## 10. FRONTEND — PAGES ET JAVASCRIPT

### 10.1 reception_topographique.html (~4000+ lignes)

**Variables globales clés :**
```javascript
let allSheetsData = {};        // { Cote_Gauche: {pks, data, cote_columns}, ... }
let commonPKs = [];            // PK communs aux deux onglets
let globalSelectedPoints = []; // { pk, sheetName, label, coteTheorique }
```

**Fonctions clés :**
- `loadAllSheetsData()` — charge tous les onglets via `Promise.all()`
- `renderColumnSelectionUI()` — grille Gauche/Droite avec checkboxes
- `makeElementLabel(colName, sheetName)` — `G_Roulement` → `"Roulement (Gauche)"`
- `generateReceptionSheet()` — construit le tableau de saisie
- `collectReceptionDataForPDF()` — collecte données pour export (lit les `<input>` directs)
- `renderResultatsSection(data)` — vue résultats avec code couleur
- `getSignatureBase64(type)` — canvas → base64

**Modes :**
- `assainissement` : 9 colonnes (sans pente/dist axe)
- `terrassement` : 11 colonnes (avec dist axe et pente)

**Statut des lignes (classes CSS sur `<tr>`) :**
- `ecart-ok` → conforme (|écart| ≤ tolérance)
- `ecart-positif` → non conforme, excédent positif
- `ecart-negatif` → non conforme, déficit
- `row-interpolated` → point interpolé (exclu du bilan)

### 10.2 Template PDF — `app/templates/pdf/fiche_reception.html`

**Variables Jinja2 :**
```
projet, date, operateur, section, meteo, tolerance, mode
controleur_nom, controleur_fonction, controleur_date
entreprise_nom, entreprise_societe, entreprise_date
signature_controleur, signature_entreprise (base64 PNG)
observations_generales
stations[] → rows[] : pk, element_label, cote_label, lav,
             cote_mesuree, cote_theorique, ecart, ecart_status,
             observation, is_interpolated
total_points, points_conformes, points_non_conformes, conformes_percent
```

**Classes CSS des lignes PDF :**
```css
tr.row-ok          { background: #f8fffe; border-left: 3px solid #4ade80; }
tr.row-error       { background: #fff8f8; border-left: 3px solid #f87171; }
tr.row-interpolated{ background: #f8fafc; border-left: 3px solid #cbd5e1; }
```

---

## 11. CONVENTIONS ET RÈGLES DE CODE

### Python (backend)
- **Langue des commentaires** : Français
- **Blueprints** : routes dans leurs fichiers respectifs (`pages.py`, `api.py`, `auth.py`, `admin.py`)
- **Logique métier** : dans `services/` et `core/profile_utils.py`
- **Gestion d'erreur** : `{"error": str(e)}, 500` sur toutes les routes API
- **NaN/Inf** : `df.where(pd.notnull(df), None)` avant sérialisation JSON
- **Auth** : `@login_required` sur toutes les routes pages/api, `@admin_required` sur `/admin/`

### JavaScript (frontend)
- **Vanilla JS uniquement** — pas de jQuery, pas de frameworks
- **Communication inter-pages** : uniquement via `sessionStorage`
- **Signatures** : lire `document.getElementById('controleur-nom').value` (inputs directs), jamais les spans `display-*`
- **Statut conformité** : lire `row.classList.contains('ecart-positif')` sur le `<tr>`
- **Signe écart négatif** : `ecartNeg` contient déjà le `-`, ne pas re-préfixer

### HTML/CSS
- **Tailwind CDN** : utilisé sur les pages admin et historique uniquement
- **CSS custom** (`style.css`) : toutes les autres pages
- **CSS inline** dans les templates : uniquement pour overrides spécifiques à la page

---

## 12. BUGS CORRIGÉS

| Bug | Cause | Fix |
|-----|-------|-----|
| Écart affiché `--23.249` | `ecartNeg` avait déjà le `-`, code ajoutait un `-` | `ecart = ecartNeg` sans préfixe |
| Bilan toujours 100% conforme | Cherchait classes `ecart-error`/`ecart-warning` inexistantes | Lire `ecart-positif`/`ecart-negatif` sur `<tr>` |
| Infos signataires absentes du PDF | Lisait les spans `display-*` non mis à jour | Lire directement les `<input>` |
| `preview_pdf` sans signatures | Route n'extrayait pas les signatures | Ajout dans la route |
| Colonnes côtes non détectées | Cherchait `'COTE'` dans le nom | `pd.api.types.is_numeric_dtype()` |
| `DATABASE_URL` avec `postgres://` | SQLAlchemy 2.x exige `postgresql://` | `str.replace()` au démarrage |
| PDF non généré sur Render | WeasyPrint nécessite GTK absent sur Render | Remplacement par xhtml2pdf |
| Email envoie HTML au lieu de PDF | Pièce jointe non obligatoire + mauvais format | `make_pdf_bytes_any` obligatoire + base64 |
| Pièce jointe corrompue (Resend) | `list(pdf_bytes)` → entiers, Resend attend base64 | `base64.b64encode(pdf_bytes).decode()` |
| Deploy Render crash au démarrage | `db.create_all()` plante si Supabase DNS timeout | Enveloppé dans `try/except` dans `__init__.py` |
| Admin voit toujours l'ancien Excel | Admin sans client tombe sur `MODEL_EXCEL` figé | Sélecteur fichier test en session dans `/admin/` |
| Logo image manquant sur Render | `optilab_logo.png` non trouvé | Logo CSS 2×2 points (cyan/jaune) dans tous les headers |

---

## 13. PROBLÈMES CONNUS ET DETTE TECHNIQUE

### PDF
- [ ] **xhtml2pdf** : rendu moins fidèle que WeasyPrint pour les mises en page complexes
- [ ] **Signatures base64** : peuvent être volumineuses (>1MB par signature)

### Architecture / Data
- [ ] **sessionStorage** : données perdues au refresh — envisager localStorage
- [ ] **Export Excel simulé** : le frontend génère un CSV avec extension `.xlsx`
- [ ] **Pas de cache Excel** : fichier R2 relu à chaque appel API

### Sécurité
- [ ] **Pas de validation stricte** des données PDF côté serveur (XSS potentiel)

---

## 14. AMÉLIORATIONS RECOMMANDÉES

### Priorité 1 — Robustesse
1. Cache serveur pour les données Excel (`functools.lru_cache` ou Redis)
2. Vraie validation et sanitization des inputs POST

### Priorité 2 — Fonctionnalités
3. Vrai export Excel via `openpyxl` (route `/api/export-excel`)
4. Niveau "avertissement" distinct de "erreur" dans le calcul d'écart
5. Observations libres par ligne (actuellement auto-texte uniquement)
6. Mot de passe oubli / reset par email

### Priorité 3 — Performance
7. Virtualisation des tableaux longs (> 500 lignes)
8. Pagination de l'historique des fiches

---

## 15. DÉBOGAGE RAPIDE

| Problème | Cause probable | Solution |
|----------|---------------|----------|
| Redirection vers `/login` sur toutes les pages | Normal — `@login_required` actif | Se connecter |
| "Fichier Excel introuvable" | Pas d'`excel_key` pour ce client | Admin → uploader l'Excel |
| "Colonne PK introuvable" | Nom de colonne sans 'PK' ou 'KILOMETRIQUE' | Renommer dans l'Excel |
| Écart avec double `--` | Bug corrigé | Voir section 12 |
| Bilan faux (100% conforme) | Bug corrigé | Voir section 12 |
| PDF non généré | xhtml2pdf erreur | Vérifier les logs Render |
| Données perdues entre pages | sessionStorage non alimenté | Vérifier la phase précédente |
| Email non envoyé | `RESEND_API_KEY` absent ou invalide | Vérifier les variables d'env Render |
| Erreur R2 | Credentials R2 invalides ou bucket inexistant | Vérifier `R2_*` dans les env vars |

---

## 16. DÉPLOIEMENT RENDER

```bash
# Build command (Render)
pip install -r requirements.txt

# Start command (Render)
gunicorn wsgi:app

# Variables d'env à configurer dans le dashboard Render :
# SECRET_KEY, DATABASE_URL, R2_ENDPOINT, R2_BUCKET,
# R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, RESEND_API_KEY, MAIL_FROM
```

Python version : **3.11** (fichier `.python-version` à la racine).

---

## 17. CHANGELOG RÉCENT (2026-04-07)

### Identité visuelle — renommage RECEPTA
- Outil renommé **RECEPTA** (OPTILAB reste la suite)
- Logo RECEPTA = grille CSS 2×2 points (`#00ffff`, `#fbbf24`, `#00ffff`, `#00ffff`) — pas d'image
- Page connexion (`auth/login.html`) : logo RECEPTA CSS centré dans l'en-tête de la card
- Page accueil (`home.html`) : header "RECEPTA by OPTILAB" avec logo CSS

### Écran d'accueil — spirale + théodolite
- Spirale agrandie : `.svg-frame` 300px → 380px, SVGs 344px → 420px
- **Théodolite SVG** ajouté au centre de la spirale (`id="topo-instrument"`) :
  - Trépied (3 pieds + embouts)
  - Corps instrument + lunette horizontale
  - Objectif et oculaire
  - Niveau à bulle (ellipse + bulle intérieure)
  - Réticule de visée (croix)
  - Arc de cercle gradué (symbolique)
  - Tout en `stroke="#00FFFF"` pour cohérence avec l'animation

### Réception topographique — UX
- Couleurs côté gauche (rouge) / côté droit (bleu) sur les lignes du tableau
- Colonne VALIDATION (bouton cyclable : — / ✓ / ⚠) avant OBSERVATIONS
- Options PDF : séparer par côté / ignorer la distinction gauche-droit
- Filtre nouveau point : exclut les points déjà validés dans la station précédente
- Observations par ligne : titre + commentaire + photo (caméra ou fichier)
- Suppression du champ "Fonction du contrôleur" (étape 5 signatures)

### Interpolation — corrections
- Bouton interpolation "entre deux PK" : discreet (petit "+" entre lignes)
- **Option choix libre PK1/PK2 corrigée** :
  - Pré-sélection automatique au premier appel
  - Message d'erreur inline si PK1 ≥ PK2
  - Lecture fraîche du DOM au clic "Confirmer" (évite les closures obsolètes)
- `regenerateAllStations` corrigé : ne détruit plus les séparateurs `.interp-sep-row` ni les boutons "+"

---

## 18. CHANGELOG 2026-04-09

### Réorganisation de la racine
- `docs/` : DOCUMENTATION_PROJET.md, RECEPTA_V2_CONCEPTION.md, INST.txt, pooler.example
- `scripts/` : gen_*.py, create_admin.py, r2_manager.py
- `data/sources/` : fichiers Excel sources clients
- `data/modeles_recepta/` : 4 modèles Excel assainissement (P1→P4, 1km à 5km)

### Logo RECEPTA CSS sur toutes les pages
- Tous les headers remplacent `optilab_logo.png` par le logo CSS grille 2×2 (cyan/jaune)
- Pages concernées : `reception_topographique.html`, `historique.html`, `admin/dashboard.html`, `index.html`, `points_kilometriques.html`

### Navigation simplifiée
- Bouton `← Phase 2 : Points km` supprimé de la barre du bas de la réception
- "Mode manuel (avancé)" renommé **"Phase Conception"** dans le footer de `home.html`

### Fixes email et PDF
- Pièce jointe PDF encodée en **base64** (format attendu par SDK Resend)
- `/generate-pdf` utilise désormais `make_pdf_bytes_any` (xhtml2pdf sur Render)
- `@login_required` ajouté sur `/generate-pdf` et `/preview-pdf` (manquait)

### Admin — sélecteur fichier Excel de test
- Nouvelle carte orange dans `/admin/` : dropdown de tous les `.xlsx` locaux
- Le choix est mémorisé en session Flask → `_get_excel_source()` le sert
- Permet à l'admin de tester n'importe quel modèle sans passer par R2

### Robustesse déploiement
- `db.create_all()` enveloppé dans `try/except` → Render ne plante plus si Supabase DNS timeout

### V2 PRO — planification
- Deux produits décidés : **RECEPTA SOLO** (29-49€/mois) et **RECEPTA PRO** (149-299€/mois/projet)
- Un seul codebase, une seule URL, différenciation par champ `plan` sur le modèle `Client`
- Architecture V2 complète documentée dans `docs/RECEPTA_V2_CONCEPTION.md`
- Prochaine étape V2 : ajouter `plan` sur `Client`, créer `blueprints/pro/`, implémenter `Projet` + `Portion` + `MembreProjet`

---

*Dernière mise à jour : 2026-04-09 — Fixes email/PDF + logo CSS + réorganisation racine + V2 PRO planifiée*
