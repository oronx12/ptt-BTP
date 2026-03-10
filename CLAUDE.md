# CLAUDE.md — PTT BTP : Profils Topographiques Travers BTP

> Fichier de référence projet. Toute personne (ou IA) travaillant sur ce code doit lire ce fichier en premier.

---

## 1. DESCRIPTION DU PROJET

**PTT BTP** est une application web Flask (Python) à usage professionnel pour les ingénieurs et techniciens du BTP.
Elle permet de :
- Créer et éditer des **profils en travers types** de routes (géométrie, couches de chaussée, éléments annexes)
- Gérer des **points kilométriques (PK)** et recalculer des coordonnées relatives
- Enregistrer des **mesures de réception topographique** terrain et les comparer aux côtes théoriques
- **Visualiser les résultats** avec code couleur (conforme/non conforme/interpolé) dans une vue dédiée
- Générer des **fiches de réception officielles** en PDF (avec signatures manuscrites, observations, légende)

**Public cible** : Contrôleurs topographiques, équipes chantier BTP, chefs de projet routiers.

---

## 2. STACK TECHNIQUE

| Composant | Technologie | Version min |
|-----------|------------|-------------|
| Backend | Python / Flask | Flask >= 2.0 |
| Lecture Excel | pandas + openpyxl | pandas >= 1.3, openpyxl >= 3.0 |
| Génération PDF | WeasyPrint (optionnel) | >= 60.0 |
| Frontend | HTML5 + CSS3 + Vanilla JS | Aucun framework JS |
| Stockage inter-pages | sessionStorage navigateur | — |
| Données | JSON, CSV, XLSX | — |

**Pas de base de données backend.** Toutes les données vivent dans le navigateur (sessionStorage) pendant la session.

---

## 3. STRUCTURE DES FICHIERS

```
02_2026_Setup_app_01/
├── setup.bat                       # ← DÉMARRAGE : double-clic pour installer + lancer
├── run.py                          # Point d'entrée développement  (python run.py)
├── wsgi.py                         # Point d'entrée production      (gunicorn/waitress wsgi:app)
├── requirements.txt                # Dépendances production
├── requirements-dev.txt            # Dépendances développement (+ pytest)
├── .env.example                    # Modèle de variables d'environnement
├── .gitignore
├── CLAUDE.md                       # ← CE FICHIER
│
├── app/                            # Package Flask principal
│   ├── __init__.py                 # Application Factory — create_app()
│   ├── config.py                   # DevelopmentConfig / ProductionConfig / TestingConfig
│   │
│   ├── blueprints/
│   │   ├── pages.py                # Routes HTML (/, /editeur, /reception, /points-kilometriques)
│   │   └── api.py                  # Routes API (/api/excel/*, /api/*-pdf, /api/download)
│   │
│   ├── services/
│   │   ├── excel_service.py        # Lecture et parsing du fichier Excel modèle
│   │   └── pdf_service.py          # Génération PDF (WeasyPrint + fallback HTML)
│   │
│   ├── templates/
│   │   ├── home.html               # Page d'accueil + choix du pipeline
│   │   ├── index.html              # Phase 1 : Éditeur de profil (canvas)
│   │   ├── points_kilometriques.html  # Phase 2 : Gestion des PK
│   │   ├── reception_topographique.html  # Phase 3 : Réception + visualisation + PDF
│   │   └── pdf/
│   │       └── fiche_reception.html   # Template PDF/impression Jinja2
│   │
│   └── static/
│       └── style.css               # Design system CSS global
│
├── core/
│   └── profile_utils.py            # Logique géométrique pure Python (sans Flask)
│
├── data/
│   ├── Projet_Routier_Topographie.xlsx  # Fichier Excel modèle (onglets: Cote_Gauche / Cote_Droit)
│   └── tmp/                        # Fichiers générés temporaires (PDF, exports)
│
├── archive/                        # Anciennes versions — NE PAS MODIFIER
│   ├── index_old.html
│   └── reception_topographique_old.html
│
├── tests/
│   ├── __init__.py
│   └── test_profile_utils.py       # Tests unitaires logique géométrique
│
└── venv/                           # Environnement virtuel Python (non commité)
```

### Fichiers archivés
`archive/index_old.html` et `archive/reception_topographique_old.html` sont des versions précédentes.
**Ne pas les modifier, ne pas les utiliser en production.**

---

## 4. DÉMARRAGE DU PROJET

### Méthode simple (Windows)
Double-cliquer sur **`setup.bat`** — il fait tout automatiquement :
1. Vérifie Python
2. Crée le venv si absent
3. Installe les dépendances
4. Lance le serveur → http://localhost:5000

### Méthode manuelle
```bash
# Créer le venv (première fois)
python -m venv venv

# Activer (Windows)
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer en développement
python run.py
# → http://localhost:5000

# Lancer en production (Windows)
waitress-serve --port=5000 wsgi:app
```

WeasyPrint (PDF natif) nécessite GTK sur Windows — si non disponible, le fallback HTML est utilisé automatiquement.

---

## 5. ARCHITECTURE BACKEND

### 5.1 Routes de pages (Blueprint `pages`) — `app/blueprints/pages.py`

| Route | Template rendu | Rôle |
|-------|---------------|------|
| `/` | `home.html` | Accueil — choix du pipeline de travail |
| `/editeur` | `index.html` | Phase 1 — Éditeur de profil en travers |
| `/points-kilometriques` | `points_kilometriques.html` | Phase 2 — Gestion PK |
| `/reception` | `reception_topographique.html` | Phase 3 — Réception topographique |

### 5.2 API endpoints (Blueprint `api`) — `app/blueprints/api.py`

#### `GET /api/excel/sheets`
Retourne la liste des onglets du fichier `Projet_Routier_Topographie.xlsx`.
```json
{ "sheets": ["Cote_Gauche", "Cote_Droit"] }
```

#### `GET /api/excel/data/<sheet_name>`
Retourne les données d'un onglet Excel nettoyées (NaN, Inf remplacés par null).
- Détecte automatiquement la colonne PK (cherche `'PK'` ou `'KILOMETRIQUE'` dans le nom de colonne)
- Détecte automatiquement les colonnes de côtes via `pd.api.types.is_numeric_dtype()` (toutes colonnes numériques non-PK)
```json
{
  "pk_column": "PK",
  "pks": ["0+000", "0+025", ...],
  "cote_columns": ["G_Roulement", "G_Base", "D_Roulement", ...],
  "all_columns": [...],
  "data": [{ "PK": "0+000", "G_Roulement": 102.34, ... }, ...]
}
```

#### `GET /api/download/<filename>`
Téléchargement d'un fichier depuis `data/tmp/`.
Protégé contre le path traversal (whitelist regex `^[\w\-. ]+$`).

#### `POST /api/generate-pdf`
Génère la fiche de réception PDF (ou HTML si WeasyPrint absent).

**Corps JSON attendu :**
```json
{
  "projet": "Nom du projet",
  "date": "2026-02-28",
  "operateur": "Nom opérateur",
  "section": "Section X",
  "meteo": "Ensoleillé",
  "tolerance": 2,
  "mode": "assainissement",
  "controleur_nom": "...",
  "controleur_fonction": "...",
  "controleur_date": "...",
  "entreprise_nom": "...",
  "entreprise_societe": "...",
  "entreprise_date": "...",
  "signature_controleur": "data:image/png;base64,...",
  "signature_entreprise": "data:image/png;base64,...",
  "observations_generales": "Texte libre d'observations...",
  "stations": [
    {
      "numero": 1,
      "nom": "Station de nivellement n°1",
      "cote_repere": 3,
      "lar": 3,
      "cote_bleue": 6.000,
      "pente": null,
      "rows": [
        {
          "pk": "0+000",
          "element_label": "Roulement (Gauche)",
          "cote_label": "0.000",
          "lav": "2",
          "cote_mesuree": "4.000",
          "cote_theorique": "4.000",
          "ecart": "-0.002",
          "ecart_status": "ok",
          "observation": "Côte conforme",
          "is_interpolated": false
        }
      ]
    }
  ]
}
```
**Réponse :** PDF binaire (`application/pdf`) ou HTML (`text/html` si fallback).

#### `POST /api/preview-pdf`
Identique à `generate-pdf` mais retourne toujours du HTML (pour impression navigateur via `window.print()`).
Accepte les mêmes champs JSON, incluant `signature_controleur` et `signature_entreprise`.

---

## 6. LOGIQUE MÉTIER — core/profile_utils.py

Ce module est le **moteur de calcul géométrique**. Il est indépendant de Flask et peut être utilisé en standalone.

### 6.1 Fonction principale : `Z_surf(x, params)`
Calcule la cote Z de la surface en un point x du demi-profil.

**Formule piecewise :**
```
Si x ≤ x_ch :  Z = Z0 - s × x
Si x > x_ch :  Z = (Z0 - s × x_ch) - s_acc × (x - x_ch)
```

### 6.2 Fonction principale : `recalc_layers(params, layers, objects=None)`
Recalcule les polygones de chaque couche de chaussée (4 coins P1 à P4).

### 6.3 Fonction haut niveau : `update_profile_from_file(path, new_Z0, new_X0)`
Charge un profil JSON, met à jour Z0/X0, recalcule et exporte CSV/XLSX/JSON.

---

## 7. FLUX DE TRAVAIL (DATA FLOW)

### Pipeline Excel multi-onglets (principal)
```
[Chargement automatique au démarrage]
  → Promise.all([GET /api/excel/data/Cote_Gauche, GET /api/excel/data/Cote_Droit])
  → allSheetsData = { Cote_Gauche: {...}, Cote_Droit: {...} }
  → commonPKs = intersection des PK des deux onglets
        ↓
[Sélection des éléments à réceptionner]
  → renderColumnSelectionUI() : grille 2 colonnes (Gauche | Droite)
  → Chaque checkbox porte data-sheet="Cote_Gauche|Cote_Droit" et data-label="Roulement (Gauche)"
  → makeElementLabel("G_Roulement", "Cote_Gauche") → "Roulement (Gauche)"
        ↓
[Génération de la fiche de saisie]
  → generateReceptionSheet() : tableau avec colonnes PK | ÉLÉMENT | Distance | LAV | Mesurée | Théorique | Écart+ | Écart-
  → Côte théorique lue depuis allSheetsData[sheetName].data[pkIndex]
  → Interpolation linéaire possible entre deux PK connus (classe row-interpolated)
        ↓
[Saisie des mesures terrain]
  → Input LAV par ligne → calcul écart = coteMesuree - coteTheorique
  → Statut par classe CSS sur <tr> : ecart-ok | ecart-positif | ecart-negatif
  → Auto-texte observation-cell : "Côte conforme" / "Côte non conforme"
        ↓
[Visualisation des résultats — bouton "Visualiser les résultats"]
  → collectReceptionDataForPDF() : lit inputs et classes CSS, construit objet JSON
    - is_interpolated : row.classList.contains('row-interpolated')
    - ecart_status : 'ok' si row.classList.contains('ecart-ok'), sinon 'error'
    - ecart : valeur directe de ecartNeg (déjà signée) ou '+' + ecartPos
    - Infos signataires lues directement depuis les <input> (pas les spans display-*)
  → renderResultatsSection(data) : stats + tableaux colorés + légende
  → Textarea "observations-generales" : texte libre
        ↓
[Export PDF]
  → POST /api/generate-pdf avec data + observations_generales
  → fiche_reception_pdf.html rendu côté serveur
  → PDF téléchargé (WeasyPrint) ou fenêtre d'impression (fallback)
```

### Pipeline Manuel (3 phases)
```
[Phase 1 - Éditeur] → sessionStorage['editorPoints']
[Phase 2 - PK]      → sessionStorage['pkData']
[Phase 3 - Réception] → même saisie que ci-dessus, sans import Excel
```

---

## 8. FRONTEND — PAGES ET JAVASCRIPT

### 8.1 reception_topographique.html — Réception (Phase 3)
**Module principal (~4033 lignes)**

**Variables globales clés :**
```javascript
let allSheetsData = {};       // { Cote_Gauche: {pks, data, cote_columns}, Cote_Droit: {...} }
let commonPKs = [];           // PK communs aux deux onglets
let globalSelectedPoints = []; // Points sélectionnés avec {pk, sheetName, label, coteTheorique}
```

**Fonctions clés :**
- `loadAllSheetsData()` — charge tous les onglets en parallèle via `Promise.all()`
- `renderColumnSelectionUI()` — grille Gauche/Droite avec checkboxes
- `makeElementLabel(colName, sheetName)` — transforme `G_Roulement` → `"Roulement (Gauche)"`
- `generateReceptionSheet()` — construit le tableau de saisie
- `generateRowHTML(stNum, pk, dist, coteTheo, isInterp, elementLabel)` — génère une ligne `<tr>`
- `collectReceptionDataForPDF()` — collecte toutes les données pour l'export (lit les inputs directs)
- `renderResultatsSection(data)` — affiche la vue résultats avec code couleur
- `getSignatureBase64(type)` — retourne l'image canvas en base64

**Modes :**
- `assainissement` : 9 colonnes (sans colonne pente/dist axe)
- `terrassement` : 11 colonnes (avec dist axe et pente)

**Colspan des lignes d'interpolation :** `terrassement ? 12 : 10`

**Statut des lignes (classes CSS sur `<tr>`) :**
- `ecart-ok` → conforme (|écart| ≤ tolérance)
- `ecart-positif` → non conforme, côté positif
- `ecart-negatif` → non conforme, côté négatif
- `row-interpolated` → point interpolé (ne compte pas dans le bilan)

### 8.2 app/templates/pdf/fiche_reception.html — Template PDF (refonte fév. 2026)

**Variables Jinja2 disponibles :**
```
projet, date, operateur, section, meteo, tolerance, mode
controleur_nom, controleur_fonction, controleur_date
entreprise_nom, entreprise_societe, entreprise_date
signature_controleur, signature_entreprise (base64 PNG)
observations_generales (texte libre)
stations[] avec rows[] incluant : pk, element_label, cote_label, lav,
  cote_mesuree, cote_theorique, ecart, ecart_status, observation, is_interpolated
total_points, points_conformes, points_non_conformes, conformes_percent
```

**Colonnes du tableau PDF :** PK | Élément | Dist.(m) | LAV | Côte mesurée | Côte théorique | Écart | Statut | Observation

**Classes CSS de ligne :**
```css
tr.row-ok          { background: #f8fffe; border-left: 3px solid #4ade80; }
tr.row-warning     { background: #fffdf0; border-left: 3px solid #facc15; }
tr.row-error       { background: #fff8f8; border-left: 3px solid #f87171; }
tr.row-interpolated{ background: #f8fafc; border-left: 3px solid #cbd5e1; }
```

**Colonne STATUT** : symboles ✓ / ⚠ / ✗ / ◦ selon `ecart_status` et `is_interpolated`

**Bilan statistique** : cartes dynamiques (vert/orange/rouge) selon `conformes_percent`

---

## 9. DESIGN SYSTEM — static/style.css

### Palette de couleurs
```css
--primary: #1e3a5f        /* Bleu foncé principal */
--primary-dark: #0f2744   /* Bleu très foncé */
--accent: #3b82f6         /* Bleu clair interactif */
--success: #059669        /* Vert */
--warning: #d97706        /* Orange */
--error: #dc2626          /* Rouge */
```

### Composants CSS notables
- `.site-header` — header sticky, gradient bleu foncé
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger` — boutons avec hover effects
- `.card`, `.section-card` — cartes avec shadow et border-radius
- Breakpoints : 1200px, 1000px, 768px, 480px

---

## 10. CONVENTIONS ET RÈGLES DE CODE

### Python (backend)
- **Langue des commentaires** : Français
- **Structure** : Toutes les routes dans `app.py`, logique métier dans `profile_utils.py`
- **Gestion d'erreur** : Chaque route API retourne `{"error": str(e)}, 500` en cas d'exception
- **NaN/Inf** : Toujours nettoyer avec `df.where(pd.notnull(df), None)` avant sérialisation JSON
- **Colonnes côtes** : détectées par `pd.api.types.is_numeric_dtype()`, pas par nom de colonne

### JavaScript (frontend)
- **Vanilla JS uniquement** — pas de jQuery, pas de frameworks
- **Communication inter-pages** : uniquement via `sessionStorage`
- **Lecture des champs signature** : toujours depuis `document.getElementById('controleur-nom').value` (inputs directs), jamais depuis les spans `display-*` qui ne sont mis à jour qu'au "Générer la fiche"
- **Statut de conformité** : lire `row.classList.contains('ecart-positif')` / `ecart-negatif` sur le `<tr>`, pas des classes de cellule
- **Signe de l'écart négatif** : `ecartNeg` contient déjà le signe `-`, ne pas préfixer d'un `-` supplémentaire

### HTML/CSS
- **Templates Jinja2** pour les pages servies par Flask
- **CSS inline** dans les templates : uniquement pour overrides spécifiques à la page

---

## 11. BUGS CORRIGÉS (fév. 2026)

| Bug | Cause | Fix |
|-----|-------|-----|
| Écart affiché `--23.249` | `ecartNeg` contenait déjà `-23.249`, code ajoutait un `-` supplémentaire | `ecart = ecartNeg` sans préfixe |
| Bilan toujours 100% conforme | `collectReceptionDataForPDF` cherchait classes `ecart-error`/`ecart-warning` inexistantes | Lire `ecart-positif`/`ecart-negatif` sur le `<tr>` |
| Infos signataires absentes du PDF | Code lisait les spans `display-*` non mis à jour | Lire directement les `<input>` |
| `preview_pdf` sans signatures | Route n'extrayait pas `signature_controleur`/`signature_entreprise` | Ajout dans `app.py` route `preview_pdf` |
| Colonnes côtes non détectées | Logique cherchait `'COTE'` dans le nom → échec avec `G_Roulement` etc. | `pd.api.types.is_numeric_dtype()` |

---

## 12. PROBLÈMES CONNUS ET DETTE TECHNIQUE

### Sécurité
- [ ] **`/download/<filename>`** : risque de path traversal — implémenter une whitelist
- [ ] **Aucune authentification** : toutes les pages sont publiques
- [ ] **Pas de validation côté serveur** des données PDF (XSS potentiel)

### Architecture / Data
- [ ] **sessionStorage** : données perdues au refresh — envisager localStorage ou API sauvegarde
- [ ] **Export Excel simulé** : le frontend génère un CSV avec extension `.xlsx`

### PDF
- [ ] **WeasyPrint optionnel** : fallback HTML n'a pas le même rendu
- [ ] **Images base64 volumineuses** : signatures peuvent dépasser 16MB (limite Flask)

### Performance
- [ ] **Pas de cache** : l'Excel est relu à chaque appel API
- [ ] **Tableaux** : pas de virtualisation — 10 000+ points provoquerait un lag

---

## 13. AMÉLIORATIONS RECOMMANDÉES (PAR PRIORITÉ)

### Priorité 1 — Sécurité
1. Sécuriser `/download/<filename>` avec un répertoire temporaire contrôlé
2. Ajouter validation des entrées dans les endpoints POST
3. `app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024`

### Priorité 2 — Robustesse
4. Remplacer sessionStorage par localStorage avec sérialisation JSON robuste
5. Ajouter route `POST /api/save-session` / `GET /api/load-session` (SQLite ou fichier)

### Priorité 3 — Fonctionnalités
6. Vrai export Excel via `openpyxl` (route `/api/export-excel`)
7. Ajout d'un niveau "avertissement" (warning) distinct de "erreur" dans le calcul d'écart
8. Permettre des observations libres par ligne (actuellement auto-texte uniquement)

### Priorité 4 — Performance
9. Cache serveur pour les données Excel (`functools.lru_cache` ou Flask-Caching)
10. Virtualisation des tableaux longs (> 500 lignes)

---

## 14. RÉSUMÉ RAPIDE POUR DÉBOGAGE

| Problème | Cause probable | Solution |
|----------|---------------|----------|
| "Fichier Projet_Routier_Topographie.xlsx introuvable" | Fichier absent du répertoire racine | Placer le fichier Excel à côté de app.py |
| "Colonne PK introuvable" | Nom de colonne sans 'PK' ou 'KILOMETRIQUE' | Renommer la colonne dans l'Excel |
| PDF sans noms/fonctions signataires | Champs remplis après "Générer la fiche" | Déjà corrigé — lecture directe des inputs |
| Écart avec double `--` | Bug corrigé fév. 2026 | Voir section 11 |
| Bilan faux (100% conforme) | Bug corrigé fév. 2026 | Voir section 11 |
| PDF non généré | WeasyPrint absent | Installer GTK + WeasyPrint ou utiliser le fallback HTML |
| Données perdues entre pages | sessionStorage non alimenté | Vérifier que la phase précédente a bien exporté |
| Canvas vide | Points non chargés | Vérifier `sessionStorage['editorPoints']` dans la console |

---

## 15. LANCEMENT EN PRODUCTION

```bash
# Avec Waitress (Windows — recommandé, inclus dans requirements.txt)
waitress-serve --port=5000 wsgi:app

# Avec Gunicorn (Linux/Mac)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

> Ne jamais utiliser `run.py` (debug=True) en production. Toujours passer par `wsgi.py`.

---

*Dernière mise à jour : 2026-02-28 — Refonte réception + visualisation résultats + corrections bugs*
