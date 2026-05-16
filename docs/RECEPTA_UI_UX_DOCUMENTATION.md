# RECEPTA by OPTILAB — Documentation UI/UX Complète
## Référence de conception pour refonte graphique

> **Usage de ce document :** Cette documentation décrit l'intégralité de l'application RECEPTA —
> toutes ses pages, ses modes, ses flux, ses données, ses animations souhaitées et ses contraintes
> d'usage terrain. Elle est destinée à guider une refonte complète de l'interface graphique.
>
> **Date de rédaction :** Mai 2026  
> **Version app :** V3 PRO

---a

## 1. IDENTITÉ DU PRODUIT

### 1.1 Nom et positionnement
- **Nom commercial :** RECEPTA
- **Sous-marque :** by OPTILAB (suite logicielle propriétaire)
- **Tagline proposée :** *"La réception topographique, digitalisée."*
- **Type :** Application web SaaS multi-tenant, usage professionnel BTP

### 1.2 Logo RECEPTA (CSS — pas d'image)
Le logo est une grille 2×2 de points colorés :
```
● (cyan #00ffff)    ● (ambre #fbbf24)
● (cyan #00ffff)    ● (cyan #00ffff)
```
Accompagné du texte "**RECEPTA**" en cyan #00ffff, et "by OPTILAB" en sous-titre discret.
**Règle absolue :** Ne jamais utiliser de fichier image pour le logo.

### 1.3 Palette de couleurs de marque
| Couleur | Hex | Usage principal |
|---------|-----|-----------------|
| Cyan RECEPTA | `#00ffff` | Couleur principale, accents, logo |
| Ambre | `#fbbf24` | Secondaire, alertes, mode ET |
| Navy profond | `#07101c` | Fond général (dark mode) |
| Navy moyen | `#0d1b2e` | Cartes, surfaces |
| Navy clair | `#1e3a5f` | Bordures, separateurs |
| Blanc | `#ffffff` | Texte principal sur fond sombre |
| Slate | `#94a3b8` | Texte secondaire |
| Vert conformité | `#10b981` | Validé, OK |
| Rouge non-conformité | `#ef4444` | Non validé, erreur |
| Violet PRO | `#8b5cf6` | Mode PARTENARIAT |

### 1.4 Typographie recommandée
- **Principale :** Inter (sans-serif moderne, lisibilité maximale)
- **Mono :** Space Mono ou JetBrains Mono (valeurs PK, mesures, codes)
- **Tailles :** minimum 14px en lecture normale, 16px sur terrain (accessibilité)

---

## 2. CONTEXTE D'USAGE — CONTRAINTES TERRAIN CRITIQUES

### 2.1 Environnement d'utilisation
L'application sera utilisée **en conditions extrêmes de chantier** :
- Plein soleil (contraste élevé obligatoire)
- Pluie et humidité (écran mouillé — cibles tactiles larges)
- Gants de chantier (cibles min. 44×44px, idéalement 56px)
- Lumière artificielle la nuit (dark mode impératif)
- Poussière, vibrations (pas de gestes complexes multi-doigts)
- Connexion internet limitée ou inexistante (loading states clairs)
- Tablette (10-12", tenue à une main possible) + Smartphone (6"+)

### 2.2 Implications design
- **Dark mode par défaut** — fond sombre, texte clair (jamais de fond blanc pur)
- **Contrastes WCAG AAA** minimum pour toutes les informations critiques
- **Boutons = cibles larges** — min 52px de hauteur, padding horizontal généreux
- **Formulaires = champs grands** — inputs min 48px de hauteur
- **Pas de survol/hover comme seul indicateur** — tout doit être lisible sans interaction
- **Feedback immédiat** — chaque action doit donner un retour visuel < 100ms
- **Mode hors-ligne partiel** — afficher clairement quand l'app tente de charger
- **Zoom natif** — ne pas désactiver le zoom navigateur (accessibility)
- **Un pouce = navigation principale** — zone safe area en bas de l'écran

---

## 3. MODES DE L'APPLICATION

L'application a **deux modes de plan** qui définissent le niveau de collaboration :

### 3.1 Mode AUTONOME (anciennement SOLO)
- **Pour qui :** Un bureau de contrôle travaillant seul, sans entreprise de travaux connectée
- **Couleur de marque :** Bleu `#3b82f6`
- **Badge :** `AUTONOME` (bleu)
- **Fonctionnalités incluses :**
  - Gestion de projet simple (1 MDC uniquement)
  - Réception topographique directe (sans demande préalable)
  - Génération de fiches PDF
  - Archivage R2 + email
  - Cartographie du tracé
  - Rapport de réceptions
- **Non inclus :** Workflow de demande ET→MDC, simulation ET, équipe travaux

### 3.2 Mode PARTENARIAT (anciennement PRO)
- **Pour qui :** Bureau de contrôle + entreprise de travaux sur un même projet
- **Couleur de marque :** Violet `#8b5cf6`
- **Badge :** `PARTENARIAT` (violet)
- **Fonctionnalités supplémentaires par rapport à AUTONOME :**
  - Entreprise de travaux connectée avec ses propres comptes
  - Workflow de **Demande de réception** (ET soumet → MDC traite)
  - Simulation terrain pour l'ET (brouillon non officiel)
  - Carte des réceptions avec verdicts géolocalisés
  - Rapport de période filtré
  - Logos des deux entités sur les fiches

### 3.3 Rôles utilisateurs
| Rôle | Abréviation | Description | Accès |
|------|-------------|-------------|-------|
| Administrateur | ADMIN | Gère tous les projets, utilisateurs, entreprises | Panel admin complet |
| Contrôleur | MDC | Mission de Contrôle — valide les réceptions | Interface réception + carte + rapport |
| Entreprise de Travaux | ET | Soumet des demandes, simule les réceptions | Demandes + simulation |
| Observateur | OBS | Lecture seule | Visualisation uniquement |

---

## 4. ARCHITECTURE GLOBALE DES PAGES

```
/ (landing)
  └─ /login
       ├─ /admin/                          (ADMIN)
       │    ├─ /admin/projets/<id>
       │    └─ /admin/projets/<id>/visualisation
       │
       └─ /pro/projets/                    (MDC / ET / OBS)
            ├─ /pro/projets/<id>/simulation          (ET)
            ├─ /pro/projets/<id>/reception-mdc       (MDC)
            ├─ /pro/projets/<id>/carte               (MDC)
            ├─ /pro/projets/<id>/rapport             (MDC)
            ├─ /pro/projets/<id>/visualisation       (MDC)
            ├─ /pro/demandes/                        (ET + MDC)
            │    ├─ /pro/demandes/nouvelle           (ET)
            │    ├─ /pro/demandes/<id>               (ET + MDC)
            │    └─ /pro/demandes/historique/        (ET + MDC)
            └─ /reception (SOLO mode)                (MDC AUTONOME)
```

---

## 5. PAGE 1 — LANDING (Page d'accueil publique)

### 5.1 Contexte
URL : `/`  
Accès : Public (non connecté)  
Objectif : Première impression du produit, conversion vers `/login`

### 5.2 Layout actuel
- Fond : `#07101c` (navy très profond)
- Navigation fixe en haut
- Grille 2 colonnes : Brand (gauche) | Animation typographique (droite)
- Responsive : 1 colonne sur mobile (animation en premier)

### 5.3 Contenu de la navigation
- Logo RECEPTA (dots CSS 2×2 + texte cyan)
- Texte "by OPTILAB" en petit
- Bouton "Connexion" → `/login` (pill, fond cyan, texte dark, hover glow)

### 5.4 Colonne Brand (gauche)
- Eyebrow : "Réception topographique BTP" (texte cyan-dim, uppercase)
- Titre géant : "RECEP**TA**" (les deux dernières lettres en cyan `#00ffff`)
- Séparateur ligne + "by OPTILAB"
- Tagline : 1-2 phrases décrivant la valeur (digitalisation de la réception)
- CTA principal : "Accéder à la plateforme" (grand bouton cyan avec box-shadow glow)
- Pills de features : 3-4 badges inline ("PDF officiel", "Archivage cloud", "Multi-projets", "Terrain mobile")

### 5.5 Colonne Animation (droite) — ANIMATION CLÉS
L'animation est une **animation typographique de style Hofmann/circle-grid** :
- 20 cercles arrangés en grille qui forment des lettres
- Chaque cercle : `clip-path: shape(...)` (Chrome 126+ / Firefox 135+)
- Les lettres cyclent automatiquement toutes les 700ms
- Cycle : `H → o → f → A → N → M → n → R` (lettres variées, certaines référencent RECEPTA)
- Couleur : `var(--cyan)` = `#00ffff`
- Taille : environ 45vw (très grande, dominante)

**Animation souhaitée sur la landing :**

1. **Animation d'entrée (load)** :
   - Fond qui s'allume progressivement (fade-in de 0.4s)
   - Navigation qui glisse du haut (slide-down 0.3s, délai 0.1s)
   - Titre RECEPTA qui apparaît lettre par lettre (stagger 0.05s par lettre)
   - Animation Hofmann qui démarre après 0.6s (pas immédiatement)
   - CTA qui pulse doucement 1s après l'entrée (attention-grab)

2. **Animation ambiante (loop)** :
   - Cycle de lettres Hofmann (existant, 700ms)
   - Fond : légère animation de particules ou gradient animé très subtil
   - Logo dots : micro-animation de "respiration" (scale 1.0→1.05→1.0, 3s loop)

3. **Animation souhaitée pour les features pills** :
   - Apparition en "cascade" de bas en haut (stagger 0.1s)
   - Hover : légère élévation + glow cyan

4. **Scroll (si la page est longue)** :
   - Sections qui apparaissent au scroll (Intersection Observer, fade+translateY)
   - Parallax subtil sur le fond

5. **Animation du bouton CTA** :
   - Glow pulsant (box-shadow cyan qui s'étend et se rétrécit, 2s loop)
   - Hover : scale 1.02 + glow plus intense
   - Click : scale 0.97 (feedback tactile)

**Note technique :** Les animations doivent être désactivables avec `prefers-reduced-motion: reduce`

### 5.6 Pied de page landing
- "© 2026 OPTILAB — RECEPTA" | version | mentions légales

---

## 6. PAGE 2 — CONNEXION

### 6.1 Contexte
URL : `/login`  
Accès : Public  
Objectif : Authentifier l'utilisateur

### 6.2 Layout
- Fond : `#07101c` avec légère texture/grain ou gradient animé
- Card centré (max-width 420px, verticalement centré)
- Au-dessus de la card : logo RECEPTA (dots + texte)
- En-dessous : "by OPTILAB" en très petit

### 6.3 Card de connexion
**Header de la card :**
- Logo RECEPTA CSS (dots 2×2)
- "RECEPTA" en cyan
- "Connexion à votre espace" (subtitle, slate-400)

**Corps du formulaire :**
- Champ Email :
  - Label flottant ou label au-dessus
  - Icône email (outline, slate-400)
  - Fond : `#0d1b2e`
  - Bordure : `#1e3a5f` au repos, `#00ffff` au focus
  - Type : email, autocomplete="email"
- Champ Mot de passe :
  - Icône cadenas
  - Toggle visibilité (oeil)
  - Type : password
- Bouton "Se connecter" :
  - Full width
  - Fond : `#00ffff`
  - Texte : `#07101c` (foncé sur fond clair)
  - Hauteur : min 52px
  - État loading : spinner + "Connexion…" (désactive le bouton)

**Gestion des erreurs :**
- Message d'erreur inline (sous le formulaire, fond rouge sombre, icône ✗)
- Pas de rechargement de page (feedback immédiat)

**Animations souhaitées :**
- Card : apparition avec légère animation (fade + scale de 0.97 → 1.0)
- Focus sur input : bordure qui s'anime (transition smooth)
- Bouton submit : feedback visuel immédiat au clic
- Erreur : apparition avec shake horizontal (animation de 0.3s)
- Succès : transition vers la page suivante (fade-out de la card)

---

## 7. PAGE 3 — TABLEAU DE BORD PRO (Liste des projets)

### 7.1 Contexte
URL : `/pro/projets/`  
Accès : MDC, ET, OBS (tout utilisateur affilié à un projet)  
Objectif : Vue d'ensemble des projets de l'utilisateur + accès rapide aux actions

### 7.2 Structure globale
- Header sticky (48-56px) : logo + nom utilisateur + badge rôle + logout
- Corps scrollable
- Pas de sidebar (navigation contextuelle par projet)

### 7.3 Header
- Gauche : Logo RECEPTA dots + "RECEPTA"
- Centre (optionnel) : nom du projet actif si 1 seul projet
- Droite : Avatar utilisateur (initiales ou photo) + badge rôle (MDC/ET/OBS) + logout

### 7.4 Contenu — Vue MDC
Si l'utilisateur est MDC :

**Barre de stats (bandeau horizontal, sticky sous header)** :
- Nb de projets gérés
- Nb de demandes en attente (badge rouge si > 0)
- Nb de réceptions ce mois

**Liste des projets MDC** :
- Section title : "Vos projets — Mission de Contrôle"
- Grid adaptatif : 1 col mobile, 2 cols tablet, 3 cols desktop
- Chaque carte projet :
  - **Header coloré** (bleu AUTONOME / violet PARTENARIAT)
  - Avatar lettre du projet (grande, 56px)
  - Nom du projet (bold, white)
  - Intitulé (slate-300, truncated)
  - PK range (cyan mono)
  - Badges : mode (AUTONOME/PARTENARIAT), statut (Actif/Inactif)
  - Section équipe : noms MDC + ET si PARTENARIAT
  - Indicateurs : nb de réceptions, nb en attente, % conformité moyen
  - **Actions (bottom bar)** :
    - Btn "Réceptionner" (cyan, icon: clipboard-check) → page réception
    - Btn "Carte" (emerald si GPS dispo, slate sinon)
    - Btn "Rapport" (blue)
    - Btn "..." (more) → dropdown : Visualiser, Historique

**Demandes en attente** (section dédiée, si PARTENARIAT) :
- Section title : "Demandes à traiter" + badge rouge
- Mini-liste des demandes urgentes (3 max, lien "Voir tout →")

### 7.5 Contenu — Vue ET
Si l'utilisateur est ET :

**Liste des projets ET** :
- Section title : "Vos projets — Entreprise de Travaux"
- Même grid que MDC
- Actions différentes :
  - Btn "Simulation" (amber) → simulation page
  - Btn "Demande" (violet) → créer une demande
  - Btn "Mes demandes" (slate)

**Mes demandes récentes** (section dédiée) :
- 3 dernières demandes avec statut coloré
- Lien "Voir tout →"

### 7.6 Animations souhaitées
- Cartes projet : apparition en cascade (stagger 0.08s), slide-up + fade-in
- Hover sur carte : légère élévation (box-shadow + translateY(-2px))
- Badge "en attente" : pulse si nb > 0 (animation attention)
- Compteurs de stats : animation de comptage (number roll) à l'entrée
- Transition entre pages : fade-out → fade-in (pas de refresh brutal)

---

## 8. PAGE 4 — DASHBOARD ADMINISTRATEUR

### 8.1 Contexte
URL : `/admin/`  
Accès : Rôle ADMIN uniquement  
Objectif : Gérer l'ensemble des projets, entreprises et opérateurs de la plateforme

### 8.2 Structure
- Header sticky : Logo RECEPTA + "Administration" badge rouge + nom admin + lien "PRO" + logout
- Barre de stats (3 chiffres : nb projets / nb opérateurs / nb entreprises)
- Navigation par onglets : **Projets** | **Opérateurs** | **Entreprises**

### 8.3 Onglet Projets

**En-tête de section :**
- Titre "Tous les projets"
- Bouton "⊕ Nouveau projet" (cyan) — ouvre un formulaire inline collapsible

**Formulaire création projet (inline, collapsible) :**
Champs :
- Nom du projet* (text)
- Intitulé complet (text, plus long)
- Description (textarea, 2 lignes)
- PK début (text, format "0+000")
- PK fin (text, format "X+000")
- Tolérance par défaut (cm) (number, default 0.2)
- Mode (radio 2 choix) : AUTONOME (bleu) | PARTENARIAT (violet)
- Bouton "Créer le projet"

**Grille des projets (1→2→3 colonnes selon écran) :**
Chaque carte projet affiche :
- **Accentuation gauche** : bande colorée (bleu/violet selon mode)
- **Avatar** : grande lettre du projet (colorée)
- **Nom + intitulé** (tronqués)
- **Badge mode** : AUTONOME (bleu) / PARTENARIAT (violet) + Actif/Inactif
- **Bureau de Contrôle** : nom de l'entreprise MDC ou "Non associé" (gris)
- **Entreprise de Travaux** : (si PARTENARIAT) nom ou "Non associé"
- **Chips équipe** : nombre de contrôleurs + nombre équipe travaux
- **Indicateur Excel** : ✓ vert si fichier Excel associé, ⚠ ambre sinon
- **Indicateur GPS** : ● vert si tracé GPS disponible, ● gris sinon
- **Barre d'actions (5 boutons)** :
  - "Équipe" → page détail projet
  - "Visualiser" → visualisation Excel
  - "Carte" → carte du tracé (coloré si GPS dispo)
  - ⚙ (gear) → panneau de configuration inline
- **Panneau ⚙ (collapsible) :**
  - Section 1 : Upload fichier Excel (drag & drop ou file input)
  - Section 2 : Config rapide (nom, PK début/fin, intitulé, tolérance)
  - Section 3 : Bouton toggle mode AUTONOME ↔ PARTENARIAT
  - Section 4 : Bouton activer/désactiver le projet

### 8.4 Onglet Opérateurs

**En-tête :**
- Titre "Opérateurs"
- Bouton "⊕ Nouvel opérateur" → formulaire création user

**Tableau des opérateurs :**
Chaque ligne :
- Avatar initiales + Nom (bold)
- Email (slate)
- Chips projets (colorés par rôle : bleu=MDC, orange=ET, violet=OBS)
- Badge actif/inactif
- Bouton "Entreprises" → expand panneau associations
- Bouton "Modifier"
- **Panneau associations (collapsible) :**
  - Chips existantes (nom entreprise + rôle + bouton ×)
  - Formulaire ajout : select entreprise + select rôle + "Associer"

### 8.5 Onglet Entreprises

**En-tête :**
- Titre "Entreprises"
- Bouton "⊕ Nouvelle entreprise"

**Tableau des entreprises :**
Chaque ligne :
- Logo entreprise (si uploadé) ou avatar lettres
- Nom + label projet
- Chips projets associés (colorés MDC/ET)
- Badge actif/inactif
- Bouton "Opérateurs" → expand
- Bouton "Modifier"
- **Panneau opérateurs (collapsible) :**
  - Liste des opérateurs affiliés (avec rôle + bouton retrait)
  - Formulaire "Associer un opérateur existant" (select + rôle)
  - Formulaire "Créer et associer un nouvel opérateur" (nom, email, mdp)

### 8.6 Animations souhaitées
- Onglets : transition slide horizontale entre les tabs
- Panneaux collapse : transition smooth height (max-height animation)
- Cartes projet : hover avec légère élévation
- Badge "Actif" ↔ "Inactif" : transition de couleur au toggle
- Flash messages (success/danger) : slide depuis le haut, auto-disparaît après 4s

---

## 9. PAGE 5 — DÉTAIL PROJET (Admin)

### 9.1 Contexte
URL : `/admin/projets/<id>`  
Accès : ADMIN  
Objectif : Gérer en profondeur un projet (équipe, clients, logos, configuration)

### 9.2 Structure
- Header sticky avec breadcrumb : Admin → Nom du projet
- Bouton "Visualiser" (lien rapide)
- Bannière d'identité du projet
- 4 onglets : **Général** | **Bureau de Contrôle** | **Équipe Travaux** | **Paramètres**

### 9.3 Bannière identité
- Avatar grand (60px) + Nom du projet (h1 white)
- Badges : mode, actif/inactif
- Infos rapides : PK range, tolérance, statut Excel, nb membres
- Bouton "Réceptionner" si Excel associé

### 9.4 Onglet Général
Formulaire d'édition :
- Nom* (text)
- Intitulé complet (text)
- Description (textarea)
- PK début / PK fin (row de 2)
- Tolérance par défaut en cm (number)
- Bouton "Enregistrer les modifications"

Section Mode :
- Explication du mode actuel
- Bouton toggle AUTONOME ↔ PARTENARIAT

### 9.5 Onglet Bureau de Contrôle (MDC)
**Entreprise mandataire :**
- Si associée : carte entreprise (logo + nom + nb opérateurs + badge MDC) + bouton "Retirer"
- Si non : dropdown select + bouton "Associer"

**Logo Bureau de Contrôle :**
- Preview du logo (si uploadé)
- Zone upload (drag & drop, formats PNG/JPG/GIF/WEBP, max 2MB)
- Bouton "Télécharger le logo MDC"

**Opérateurs MDC :**
- Liste des membres rôle "controleur" (avatar + nom + email + badge rôle + bouton ×)
- Formulaire ajout :
  - Select opérateur (tous les users disponibles)
  - Select entreprise (optionnel, pour afficher sur la fiche)
  - Bouton "Ajouter"

### 9.6 Onglet Équipe Travaux (ET)
- Si mode AUTONOME : banner amber "Ce projet est en mode AUTONOME — activez PARTENARIAT pour gérer une équipe Travaux" + bouton toggle
- Si mode PARTENARIAT : même structure que MDC mais pour l'entreprise ET + opérateurs rôle "travaux"

### 9.7 Onglet Paramètres
**Excel :**
- Statut actuel (✓ associé / ⚠ manquant)
- Zone upload (drag & drop)
- Note : "L'upload auto-remplit PK début/fin et tolérance si les champs sont vides"

**Coordonnées GPS :**
- Nb de points si défini
- Lien "Ouvrir la carte"

**Zone Danger (rouge sombre) :**
- Bouton "Désactiver le projet" (amber)
- Bouton "Supprimer définitivement" (rouge, requiert confirmation par texte)

### 9.8 Animations souhaitées
- Transitions entre onglets : fade (0.15s)
- Formulaires save : bouton → spinner → checkmark vert (sans rechargement)
- Upload logo : preview immédiate avant envoi (FileReader JS)
- Zone danger : animation shake si confirm échoue

---

## 10. PAGE 6 — VISUALISATION PROJET (Admin + PRO MDC)

### 10.1 Contexte
URL : `/admin/projets/<id>/visualisation` et `/pro/projets/<id>/visualisation`  
Accès : ADMIN + MDC  
Objectif : Analyser le modèle Excel du projet (profil, sections, éléments, carte)

### 10.2 Structure
- Header sticky avec breadcrumb
- Carte d'identité (logos MDC/ET + nom + badges + paramètres GEN)
- Bannière stats (4 KPIs : nb PK, longueur totale, sections AXE, éléments mesurables)
- **Mini-carte Leaflet** (tracé du projet si PK_Coordonnées dans Excel)
- Grille 2 colonnes (si profil long disponible) :
  - Colonne gauche : Profil en long (Chart.js, ligne cyan)
  - Colonne droite : Profil en travers type (SVG généré)
- Section Sections (onglets AXE / ASG-Gauche / ASD-Droit)
- Section Éléments mesurables (grille colorée par groupe)

### 10.3 Mini-carte Leaflet
- Hauteur : 300px
- Fond de carte : OpenStreetMap (plan), possibilité satellite
- Tracé Lambert93 → WGS84 via proj4.js
- Polyline cyan (#00ffff) pour l'axe du projet
- Marqueur vert : point de départ (PK début)
- Marqueur rouge : point d'arrivée (PK fin)
- Marqueurs bleus : PK intermédiaires (optionnel, si nb PK < 50)
- Bouton "Ouvrir la carte complète →" (lien vers `/pro/projets/<id>/carte`)
- Message d'état sous la carte : "X points PK chargés depuis l'Excel"
- Si pas de données : carte cachée

### 10.4 SVG Profil en travers type
Généré par `visualization_service.py` → `generate_section_svg()` :
- Vue en coupe transversale de la route
- Couches de chaussée empilées (BB en haut, FF en bas) avec leurs couleurs :
  - BB : `#2c2c2c` (bitume)
  - GB4/GB : `#4a4a4a` (grave bitume)
  - GNT : `#8a8a8a` (grave non traitée)
  - FF : `#5b4ca8` (fond de forme)
  - SOL : `#8b6914` (sol naturel)
- Canaux d'assainissement (gauche : bleu `#1a6fb5`, droit : violet `#7c3aed`)
- Points TER en amber `#f59e0b`
- Annotations largeurs et dévers
- Légende des épaisseurs en cm

### 10.5 Animations souhaitées
- Chart.js profil en long : animation de dessin de la ligne (drawTime)
- SVG profil en travers : fade-in des couches en cascade (stagger 0.1s par couche)
- Mini-carte : fade-in de la polyline après chargement
- KPIs : animation de comptage des chiffres à l'entrée

---

## 11. PAGE 7 — CARTE DU PROJET (PRO MDC)

### 11.1 Contexte
URL : `/pro/projets/<id>/carte`  
Accès : MDC + ADMIN  
Objectif : Cartographie interactive du tracé avec visualisation des réceptions

### 11.2 Structure
- Plein écran (100vh, sans scroll)
- Header 48px sticky (logo + nom projet + logout)
- Carte Leaflet occupant tout l'espace restant
- Panneau flottant à droite (collapsible)

### 11.3 Carte Leaflet
**Fond de carte (3 choix) :** Plan (OSM) | Satellite (ESRI) | Topo (OpenTopoMap)

**Couches cartographiques :**
- **Structure (toujours visible) :**
  - Axe du projet : polyline cyan, weight 3
  - Emprise chaussée : polygon semi-transparent bleu
  - Points PK : cercles numérotés (cyan, radius 5, popup au clic)
- **Côté Gauche :** éléments offsettés à gauche (polylines parallèles, bleu)
- **Côté Droit :** éléments offsettés à droite (polylines parallèles, violet)
- **Axe :** éléments centraux (polyline cyan)
- **Réceptions clôturées :**
  - Validée : segment vert `#10b981`
  - Non validée : segment rouge `#ef4444`
  - À reprendre : segment ambre `#f59e0b`

**Interactions carte :**
- Clic sur un segment de réception → popup avec : N° demande, PK range, date, verdict, lien "Détail"
- Clic sur PK → popup avec cote Z NGF
- Géolocalisation "Me localiser" (point bleu pulsant)
- Sélecteur fond de carte dans le panneau

### 11.4 Panneau flottant
- Toggle collapse/expand (bouton ▾)
- Section : Fond de carte
- Section : Couches (avec switch on/off + indicateur couleur + oeil)
- Section : Légende réceptions (Validée/Non validée/À reprendre)
- Compteur réceptions sur la carte
- Section : "Me localiser" (GPS)
- Lien : "Rapport des réceptions" → page rapport

### 11.5 Animations souhaitées
- Chargement : overlay avec loader RECEPTA (4 points qui pulsent)
- Couches : fade-in progressif des polylines au chargement
- Réceptions : les segments apparaissent avec un effet de dessin (animation CSS path)
- Popup : slide-up au clic
- Géolocalisation : pulse ring (cercles concentriques qui s'étendent)
- Toggle panneau : slide smooth

---

## 12. PAGE 8 — LISTE DES DEMANDES (PRO ET + MDC)

### 12.1 Contexte
URL : `/pro/demandes/`  
Accès : ET (ses demandes) + MDC (inbox) + ADMIN  
Objectif : Vue d'ensemble des demandes de réception

### 12.2 Structure
- Header avec "Demandes de réception" + actions rapides
- Pour MDC : Section "À traiter" en haut (urgences)
- Pour ET : Section "Mes demandes" + bouton "Nouvelle demande"

### 12.3 Cards demande
Chaque card :
- **Numéro** (cyan, monospace, ex: DR-2026-001) + **Badge statut** (coloré)
- Nom du projet (bold)
- Tronçon : PK début → PK fin (monospace ambre)
- Mode : ASS / TER (petit badge)
- Demandeur + date soumission
- Date souhaitée (si définie)
- Flèche → vers le détail

**Badges statut :**
| Statut | Couleur fond | Couleur texte | Icône |
|--------|-------------|---------------|-------|
| En attente | `#78350f` (ambre sombre) | `#fcd34d` | ⏳ |
| Accusée | `#1e3a5f` (bleu) | `#7dd3fc` | 📨 |
| Acceptée | `#064e3b` (vert) | `#6ee7b7` | ✓ |
| Refusée | `#7f1d1d` (rouge) | `#fca5a5` | ✗ |
| Clôturée | `#1e1b4b` (violet sombre) | `#c4b5fd` | ⬛ |

### 12.4 Animations souhaitées
- Cards : stagger d'apparition (0.05s par card)
- Hover : border-color transition + légère élévation
- Badge statut "En attente" : subtle pulse si MDC
- Nouvelles demandes depuis la dernière visite : highlight animé (border flash)

---

## 13. PAGE 9 — CRÉATION D'UNE DEMANDE (ET)

### 13.1 Contexte
URL : `/pro/demandes/nouvelle`  
Accès : ET uniquement  
Objectif : Soumettre une demande de réception à la MDC

### 13.2 Structure (4 sections)
Wizard ou page unique avec sections distinctes visuellement.

### Section 1 : Projet
- Dropdown "Sélectionner un projet" (un seul projet dans la majorité des cas)
- Card de preview du projet une fois sélectionné (nom, PK, tolérance)

### Section 2 : Paramètres
- Mode toggle (Assainissement ↔ Terrassement) — grand toggle tactile
- Tolérance (number spinner avec +/- buttons, min 0.5, default 2.0)
- Météo (input texte, placeholder "Ex: Ensoleillé, 18°C")

### Section 3 : Sélection des éléments (2 colonnes)
**Colonne gauche : Points kilométriques**
- Sélecteur de plage rapide : "PK début" + "PK fin" + bouton "Appliquer"
- Liste de checkboxes scrollable (chaque PK = checkbox)
- "Tout cocher" / "Tout décocher"
- Indicateur : "X PK sélectionnés"

**Colonne droite : Éléments à mesurer**
- Groupé par côté (Gauche en bleu, Droit en vert)
- Checkboxes des colonnes de côtes
- "Tout cocher" / "Tout décocher" par côté
- Indicateur : "X éléments sélectionnés"

**Ligne d'état (entre les 2 colonnes) :**
- Loading spinner pendant le chargement Excel
- Message d'erreur si chargement échoue

### Section 4 : Planification (fond sombre ambre)
- Date souhaitée (date picker grande cible tactile)
- Heure souhaitée (time picker)
- Observations (textarea, 3 lignes)

### Actions
- Bouton "Annuler" (ghost)
- Bouton "Envoyer la demande à la MDC" (orange/ambre, icon send, full-width mobile)

### 13.3 Animations souhaitées
- Section 3 : apparition progressive après sélection projet
- Checkboxes : animation de coche (checkmark draw)
- Compteur PK/éléments : animation de comptage en temps réel
- Bouton submit : état loading (spinner) → état succès (checkmark + redirect)
- Validation erreur : champs en erreur avec shake + border rouge

---

## 14. PAGE 10 — DÉTAIL D'UNE DEMANDE

### 14.1 Contexte
URL : `/pro/demandes/<id>`  
Accès : ET (lecture + verdict) + MDC (actions) + ADMIN  
Objectif : Voir le détail d'une demande + effectuer les actions MDC

### 14.2 Structure
**Card 1 : En-tête demande**
- N° demande (grand, cyan, mono)
- Projet + PK range
- Statut badge (grand)
- Soumetteur + date
- Détails : météo, tolérance, observations, date souhaitée

**Card 2 : Timeline**
Frise chronologique verticale :
```
● Soumise (violet)          — date/heure
● Accusée (bleu)            — date/heure (si présent)
● Acceptée (vert)           — date/heure (si présent)
  [ou]
● Refusée (rouge)           — date/heure + motif
● Clôturée + Verdict (couleur) — date/heure + label verdict
```
Points de timeline avec ligne de connexion, animation de fill progressif

**Card 3 : Actions MDC** (visible uniquement MDC)
*Selon statut :*
- en_attente : [Accuser réception] [Refuser] (avec form motif caché)
- accusee : [Accepter] [Refuser]
- acceptee : [Bouton LANCER LA RÉCEPTION (grand, cyan)] + 3 boutons verdict

**Card 4 : Éléments sélectionnés**
- Tableau des éléments (sheet + colonne) que l'ET a sélectionnés
- Groupés par côté (Gauche/Droit)

### 14.3 Animations souhaitées
- Timeline : apparition des étapes de haut en bas, ligne de connexion qui se "remplit" en vert
- Bouton "Lancer la réception" : pulse cyan pour attirer l'attention
- Actions MDC : confirm dialog avec animation de slide-up (modal/sheet)
- Verdict : après clic, le badge de statut se transforme avec animation

---

## 15. PAGE 11 — SIMULATION (ET — Brouillon)

### 15.1 Contexte
URL : `/pro/projets/<id>/simulation`  
Accès : ET + MDC  
Objectif : Tester des mesures de manière informelle, sans créer de fiche officielle

### 15.2 Structure
**Header :**
- Badge "BROUILLON" (ambre, bien visible)
- Bouton impression/PDF
- Bouton réinitialiser

**Barre de contrôles sticky :**
- Sélecteur d'onglet Excel (dropdown)
- PK début / PK fin (dual dropdown)
- Tolérance (spinner)
- Bouton "Générer le tableau" (violet)

**Barre de bilan (apparaît après génération) :**
- Total points | Conformes | Non-conformes | % conformité
- Barre de progression colorée

**Zone principale :**
- Avant génération : message d'instruction
- Après génération : tableau de simulation (voir détail ci-dessous)

### 15.3 Tableau de simulation
Fond dark (`#0f172a`), police monospace :
| PK | Élément | Côte théorique | Mesure terrain | Écart | Statut |
|----|---------|--------------|-----------| ------|----|
| 1+000 | Roulement G | 162.340 | `[input]` | — | — |

**Comportement des inputs :**
- Fond : `#1e293b`
- Texte : blanc
- Focus : border cyan
- Après saisie : calcul automatique écart + coloration de la ligne
  - Conforme : fond vert clair `#f0fdf4` + "✓ OK"
  - Non-conforme : fond rouge clair `#fef2f2` + "▲ +X.Xmm" ou "▼ -X.Xmm"
  - Vide : neutre
- Bilan mis à jour en temps réel

**Bannière simulation (imprimable) :**
```
⚠ SIMULATION — BROUILLON NON OFFICIEL ⚠
Ce tableau est un outil de préparation interne.
Pour une réception officielle, créez une demande.
```

### 15.4 Animations souhaitées
- Tableau : fade-in des lignes en cascade après génération
- Input value → calcul → coloration : transition smooth de la ligne (0.2s)
- Barre de bilan : transition de la barre de progression (width change, smooth)
- Badge "BROUILLON" : subtle pulse ambre en permanence

---

## 16. PAGE 12 — RÉCEPTION TOPOGRAPHIQUE (Cœur de l'application)

### 16.1 Contexte
URL : `/reception` (SOLO) ou `/pro/projets/<id>/reception-mdc` (PRO) ou `/reception?pro=1&demande_id=X`  
Accès : MDC + ADMIN  
Objectif : Saisir les mesures terrain et comparer aux côtes théoriques

**C'est la page la plus importante de l'application. Elle est utilisée directement sur le terrain, tablette à la main.**

### 16.2 Wizard en étapes
La page est organisée en **4 étapes** :

```
Étape 1 : Infos générales
Étape 2 : Sélection des éléments
Étape 3 : Saisie des mesures
Étape 4 : Signatures + Export
```

Navigation : stepper horizontal sticky en haut (pas de sidebar).

### 16.3 ÉTAPE 1 — Informations générales

**Formulaire d'en-tête de fiche :**
- Nom du projet* (text)
- Date du contrôle* (date picker, défaut = aujourd'hui)
- Nom de l'opérateur* (text)
- Section / Tronçon (text, ex: "PK 1+000 à PK 3+500")
- Météo (text)
- Tolérance (number, cm, default 0.2)
- Mode : **Assainissement ↔ Terrassement** (grand toggle tactile)

**Mode toggle :**
- Fond dark, 2 options côte à côte
- Assainissement : icône tuyau + "ASS"
- Terrassement : icône excavateur + "TER"
- L'actif a un fond coloré, l'inactif est ghost

**Bouton "Étape suivante →"** (full-width sur mobile)

### 16.4 ÉTAPE 2 — Sélection des éléments

**Chargement Excel :**
- Spinner "Chargement des données Excel…"
- Barre de progression si lent
- Message d'erreur si échec

**Interface de sélection :**

**Colonne gauche : Points kilométriques**
- Tous les PK communs aux onglets de l'Excel
- Sélecteur de plage (PK début → PK fin + "Appliquer")
- Liste scrollable avec checkboxes
- Boutons "Tout" / "Aucun"
- **Section PK hors-plan** (si onglet IMPREVUS dans Excel) :
  - Séparateur ambre "⚠ PK hors-plan (IMPREVUS)"
  - PK listés en italic ambre, checkbox cochables

**Colonne droite : Côtes à mesurer**
- Groupé par onglet (Cote_Gauche, Cote_Droit, etc.)
- En-têtes colorés (bleu Gauche, vert Droit)
- Checkboxes des colonnes
- Tout/Aucun par groupe
- **Section hors-plan** (si IMPREVUS) : colonnes en fond ambre clair

**Panneau SVG (collapsible) :**
- Titre "Schéma profil en travers"
- SVG du profil en travers avec couches et épaisseurs
- Apparaît uniquement si projet PRO avec Excel V3

**Options de génération PDF :**
- Checkbox : "Séparer Gauche et Droite sur pages séparées"
- Checkbox : "Ignorer la distinction Gauche/Droit"

**Bouton "Générer la fiche →"** (grand, cyan)

### 16.5 ÉTAPE 3 — Saisie des mesures

**Header de la station :**
- N° station + nom
- Paramètres de la station :
  - Côte de repère (input)
  - LAV — Lecture Arrière Visée (input)
  - Côte bleue calculée = Cote_repere + LAV (affichée automatiquement)
  - (Terrassement uniquement) Pente (%)

**Tableau de saisie :**

*Mode Assainissement (9 colonnes) :*
| PK | Élément | Côte LAV | Mesurée | Théorique | Écart+ | Écart- | Valida. | Obs. |
|----|---------|----|---|---|---|---|---|---|

*Mode Terrassement (11 colonnes) :*
| PK | Élément | Dist.Axe | Pente | Côte LAV | Mesurée | Théorique | Écart+ | Écart- | Valida. | Obs. |
|----|---------|----|---|---|---|---|---|---|---|---|

**Saisie mesurée :**
- Grand input tactile (min 44px hauteur)
- Keypad numérique suggéré (inputmode="decimal")
- Focus automatique sur le prochain champ après validation

**Statuts des lignes (couleur de fond de la ligne entière) :**
- `ecart-ok` : fond vert clair `#f0fdf4`, border-left vert
- `ecart-positif` : fond rouge `#fef2f2`, border-left rouge + badge "▲ +Xmm"
- `ecart-negatif` : fond rouge `#fef2f2`, border-left rouge + badge "▼ -Xmm"
- `row-interpolated` : fond gris `#f8fafc`, border-left slate + badge "INT"
- `row-imprevu` : fond ambre `#fffbeb`, border-left ambre + badge "HP"

**Colonne Observations :**
- Bouton caméra 📷 → capture photo (optionnelle)
- Textarea mini pour note libre

**Colonne Validation :**
- Bouton cyclable : — → ✓ → ⚠ → —
- Couleurs : neutre → vert → ambre

**Actions sur les lignes :**
- Bouton interpolation "+" entre deux lignes (discret, apparaît au hover)
- Bouton suppression de la ligne (×, discret)

**Actions sur la station :**
- Bouton "+ Nouvelle station" → duplique le tableau pour un nouveau PK
- Bouton "Visualiser les résultats" → affiche la section résultats

**Section résultats (après "Visualiser") :**

Header gradient vert emerald :
- Logos MDC/ET (si PRO, chargés depuis R2)
- "Résultats de réception" + sous-titre
- Badges : mode (ASS/TER) + % de conformité

**4 KPI Cards :**
- Points mesurés (fond bleu)
- Taux de conformité % (fond coloré selon %)
- Points conformes (fond vert)
- Hors tolérance (fond rouge si > 0, vert si 0)

**Tableaux de résultats par station :**
- Header : "Station X" + badge % conformité
- Tableau récapitulatif (plus compact)
- Colorisation identique au tableau de saisie

### 16.6 ÉTAPE 4 — Signatures + Export

**Section signataires :**

**Bloc Contrôleur MDC :**
- Nom* (input)
- Grade/Fonction (input)
- Date (date picker, défaut aujourd'hui)
- Zone signature (canvas tactile) — dessin avec le doigt ou stylet
- Bouton "Effacer la signature"

**Bloc Entreprise de Travaux :**
- Même structure que MDC

**Statut de réception global :**
- 3 boutons radio larges (tactiles) :
  - ✓ **Validée** (emerald, fond vert sombre)
  - ✗ **Non validée** (rouge, fond rouge sombre)
  - ↩ **À reprendre** (ambre, fond ambre sombre)

**Options d'export :**
- Section "Observations générales" (textarea)
- Bouton principal : "Générer le PDF" (cyan, très grand, icône PDF)
- Bouton secondaire : "Prévisualiser" (ghost)
- Bouton tertiaire : "Envoyer par email" (outline)

**Email modal (si "Envoyer par email" cliqué) :**
- Destinataires (multi-input)
- Message personnalisé (textarea)
- Bouton "Envoyer"

### 16.7 Animations souhaitées
- Stepper : indicateur d'étape qui se "remplit" à chaque avancée
- Tableau de saisie : ligne qui change de couleur en transition smooth (0.3s) après saisie
- KPI Cards : chiffres qui se comptent à la génération des résultats
- Signature canvas : guide subtil ("Signez ici") qui disparaît au premier touch
- Bouton PDF : animation de génération (spinner → progress → checkmark + download)
- Tables résultats : stagger d'apparition des lignes

---

## 17. PAGE 13 — RAPPORT DE PÉRIODE (PRO MDC)

### 17.1 Contexte
URL : `/pro/projets/<id>/rapport?date_debut=...&date_fin=...`  
Accès : MDC + ADMIN  
Objectif : Rapport agrégé de toutes les réceptions d'une période, imprimable

### 17.2 Structure
**Barre de filtre (sticky, masquée à l'impression) :**
- Label "Du" + date picker
- Label "Au" + date picker
- Bouton "Filtrer"
- Badge période active (si filtre actif)
- Bouton "Tout afficher" (si filtre actif)

**Barre d'impression (sticky, masquée à l'impression) :**
- Logo RECEPTA + "Rapport de réceptions"
- Lien "← Carte"
- Bouton "Imprimer / Exporter PDF"

**En-tête du rapport :**
- Nom du projet (h1)
- Sous-titre : période filtrée ou "Toutes sections clôturées"
- PK range
- Date de génération + nom de l'utilisateur

**4 KPIs :**
- Total réceptions (bleu)
- Validées (vert)
- Non validées (rouge)
- À reprendre (ambre)

**Barre de taux :**
- Barre colorée (verte + ambre + rouge proportionnelles)
- Légende avec pourcentages

**Tableau détail :**
Colonnes : N° | Tronçon (PK) | Mode | Demandé par | Clôturée le | Verdict | Tolérance

**Pied de page :**
"Rapport généré par RECEPTA by OPTILAB — [date]"

### 17.3 Animations souhaitées
- Barre de taux : animation d'extension au chargement (width transition depuis 0)
- KPIs : comptage animé
- Tableau : lignes qui apparaissent en cascade

---

## 18. PAGE 14 — HISTORIQUE DES RÉCEPTIONS (PRO)

### 18.1 Contexte
URL : `/pro/demandes/historique/`  
Accès : ET + MDC + ADMIN  
Objectif : Archiver et retrouver toutes les réceptions clôturées

### 18.2 Structure
- Header + stats (total, validées, non-validées, à reprendre)
- Barre de recherche (temps réel, no-submit)
- Tableau principal

**Tableau :**
Colonnes : N° + Mode | Projet | Tronçon | Demandeur | Clôturée le | Verdict | Actions

**Actions par ligne :**
- "Détail" → demande_detail
- "Fiche PDF" (si fiche archivée) → URL présignée R2
- "Revoir" (MDC uniquement) → ouvre la réception en mode consultation

**État vide :**
- Icon + "Aucune réception clôturée" + lien vers demandes

**Recherche :**
- Filtre en temps réel sur : numéro, projet, PK, demandeur

---

## 19. FICHE PDF — DOCUMENT OFFICIEL

### 19.1 Contexte
Générée par : `POST /api/generate-pdf` ou `POST /api/preview-pdf`  
Template : `app/templates/pdf/fiche_reception.html` (Jinja2 + xhtml2pdf)  
Format : PDF téléchargeable + archivé sur Cloudflare R2

### 19.2 Structure de la fiche
**En-tête (Header) :**
- Logo MDC (max 52px) à gauche
- Titre centré : INTITULÉ DU PROJET (majuscules)
- Sous-titre : "Fiche de Réception Topographique"
- Logo ET (max 52px) à droite
- Ligne : Date | Mode (ASS/TER) | Section

**Bloc Informations générales (2 colonnes) :**
- Colonne 1 : Projet, Date, Opérateur, Section, Météo
- Colonne 2 : KPIs (total, conformité %, conformes, hors tolérance)

**Barre de conformité :**
- Barre colorée (vert/orange/rouge selon %)
- Label : "X% de points conformes"

**Verdict global (coloré) :**
- "VALIDÉE" (fond vert) / "NON VALIDÉE" (fond rouge) / "À REPRENDRE" (fond ambre)

**Pour chaque station :**
- En-tête : N° station + badge conformité
- Paramètres : côte repère, LAV, côte bleue
- Tableau des mesures (compact, 7-8 colonnes selon mode)
  - Lignes colorées selon statut (row-ok / row-error / row-interp / row-imprevu)
  - Badge "INT" pour interpolés, badge "HP" pour hors-plan
- Observations de la station (si présentes)

**Observations générales :**
- Tableaux d'observations avec image et texte

**Signatures :**
- Colonne Contrôleur (nom, grade, date, image signature)
- Colonne Entreprise (nom, société, date, image signature)

**Légende :**
- Conforme (vert) / Non conforme (rouge) / Interpolé (gris) / Hors-plan HP (ambre)

**Pied de page :**
- RECEPTA by OPTILAB | N° de page | Date

---

## 20. COMPOSANTS UI TRANSVERSAUX

### 20.1 Header application (toutes les pages connectées)
```
[Logo RECEPTA] [Nom page ou breadcrumb]     [User avatar + nom] [logout]
```
- Hauteur : 48-56px
- Fond : `#1e293b` (slate-800)
- Sticky (reste visible au scroll)
- Sur mobile : breadcrumb remplacé par nom de page seul

### 20.2 Navigation mobile (Bottom bar)
Pour les pages PRO sur mobile/tablette, une bottom navigation de 4 icons :
- Projets (maison)
- Demandes (liste + badge)
- Historique (horloge)
- Profil (personne)

### 20.3 Flash messages
- Apparaissent en haut de page (sous le header)
- Types : success (vert), danger (rouge), info (bleu), warning (ambre)
- Auto-disparition après 4s
- Animation : slide-down depuis le header + fade-out automatique
- Icônes : ✓ / ✗ / ℹ / ⚠

### 20.4 Modals / Sheets
- Sur desktop : modal centré avec backdrop
- Sur mobile : bottom sheet (slide-up depuis le bas)
- Backdrop : fond semi-transparent sombre
- Animation : fade-in + slide-up (0.25s)
- Fermeture : clic backdrop ou swipe-down (mobile)

### 20.5 Loading states
- Spinners : 4 points RECEPTA (cyan/ambre) qui pulsent en séquence
- Squelettes : placeholder animé (shimmer) pour les tableaux en cours de chargement
- Progress bars : pour les uploads et génération PDF
- Toast "Chargement…" pour les actions courtes

### 20.6 Empty states
- Illustration SVG simple (non surchargée)
- Titre "Aucun X pour le moment"
- Description courte
- CTA si applicable ("Créer un X")

### 20.7 Tooltips
- Apparaissent au hover (desktop) et au long-press (tactile, 500ms)
- Fond : `#1e293b`
- Texte : white
- Border-radius : 6px
- Animation : fade-in 0.1s

---

## 21. RÉCAPITULATIF ANIMATIONS PAR PAGE

| Page | Animations d'entrée | Animations ambiantes | Animations interactions |
|------|--------------------|--------------------|------------------------|
| Landing | Fade + stagger lettres RECEPTA | Cycle Hofmann, dots pulse | Hover pills glow, CTA pulse |
| Login | Card scale-in | — | Input border glow focus, error shake |
| Pro - Liste projets | Cards stagger slide-up | Badge en attente pulse | Hover élévation carte |
| Admin - Dashboard | Tabs slide | — | Panel collapse smooth |
| Détail projet | Fade entre tabs | — | Upload preview, save → checkmark |
| Visualisation | Chart drawTime, SVG couches stagger | — | Popups Leaflet |
| Carte Leaflet | Loader RECEPTA, polyline draw | Pulse géolocalisation | Popup slide-up |
| Liste demandes | Cards stagger | En attente pulse | Hover border-color |
| Création demande | Sections révélées progressivement | — | Submit loading → checkmark |
| Détail demande | Timeline fill progressif | Bouton lancer pulse | Verdict confetti (si validée) |
| Simulation | Tableau fade-in | Badge brouillon pulse | Ligne coloration smooth |
| **Réception** | Stepper fill | — | Ligne coloration, PDF loading |
| Rapport | KPIs comptage, barre extension | — | Filtre date feedback |
| Historique | Table stagger | — | Recherche highlight |

---

## 22. CONSIDÉRATIONS ACCESSIBILITÉ TERRAIN

### 22.1 Taille des cibles tactiles
- Boutons d'action principaux : min 56px de hauteur
- Inputs de saisie terrain : min 52px de hauteur
- Checkboxes : custom (min 24×24px)
- Éléments de navigation : min 48px

### 22.2 Contraste
- Texte normal : ratio ≥ 7:1 (WCAG AAA)
- Texte grand (>18px) : ratio ≥ 4.5:1
- Informations critiques (conformité, verdict) : ratio maximum possible

### 22.3 Gestes tactiles
- Swipe pour navigation (avec fallback bouton)
- Long-press pour options supplémentaires
- Double-tap pour zoom acceptable
- Pas de gestes complexes multi-doigts

### 22.4 Mode plein soleil
- Background sombre obligatoire (jamais de fond blanc en usage terrain)
- Texte blanc ou très clair
- Contrastes renforcés pour les valeurs de mesure
- Police légèrement plus grande qu'habituellement (16px minimum pour les données)

### 22.5 Feedback haptique
- Si API Vibration disponible : légère vibration (50ms) à chaque mesure validée
- Vibration plus longue (200ms) si mesure non conforme

---

## 23. DÉTAIL DES MODES DE RÉCEPTION

### 23.1 Mode Assainissement (ASS)
**Usage :** Vérification des côtes altimètriques pour réseaux d'assainissement, eaux pluviales, bordures, trottoirs, radiers.

**Colonnes du tableau de saisie (9 colonnes) :**
1. **PK** — Point kilométrique (ex: 1+250)
2. **Élément** — Nom de l'élément mesuré (ex: G_Roulement, D_Fond_Fouille)
3. **Côte LAV** — Côte bleue calculée (Cote_repère + LAV) — auto
4. **Mesurée** — Côte mesurée sur le terrain (INPUT utilisateur)
5. **Théorique** — Côte théorique depuis l'Excel
6. **Écart +** — Excédent positif (si mesure > théorique)
7. **Écart -** — Déficit négatif (si mesure < théorique)
8. **Validation** — Cyclable : — / ✓ / ⚠
9. **Observations** — Notes texte + photo

**Calcul automatique :**
```
écart = mesure - théorique
si |écart| ≤ tolérance → conforme (ecart-ok)
si écart > 0 → excédent positif (ecart-positif, rouge)
si écart < 0 → déficit (ecart-negatif, rouge)
```

### 23.2 Mode Terrassement (TER)
**Usage :** Vérification des profils en travers pour terrassements, remblais, déblais, dressement des talus.

**Colonnes supplémentaires (11 colonnes) :**
1. **PK**
2. **Élément**
3. **Distance axe** — Distance de l'élément par rapport à l'axe (m) (INPUT)
4. **Pente** — Pente du profil (%) — héritée de la station ou saisie
5. **Côte LAV**
6. **Mesurée** (INPUT)
7. **Théorique** — calculé depuis : Cote_axe + (distance × pente / 100)
8. **Écart +**
9. **Écart -**
10. **Validation**
11. **Observations**

**Spécificités terrassement :**
- Champ "Pente" par station (global pour toute la station)
- Possibilité de sous-points (multiple distances par élément)
- Côte théorique recalculée dynamiquement à chaque changement de pente

---

## 24. INFRASTRUCTURE TECHNIQUE (pour info designer)

| Composant | Technologie |
|-----------|-------------|
| Backend | Python Flask |
| Base de données | PostgreSQL (Supabase) |
| Stockage fichiers | Cloudflare R2 |
| Email | Resend API |
| PDF | xhtml2pdf (Python) |
| Excel | pandas + openpyxl |
| Cartes | Leaflet.js + proj4.js |
| Graphiques | Chart.js |
| Authentification | Flask-Login (sessions) |
| Hébergement | Render (Linux) |
| Frontend | HTML + CSS + Vanilla JS |

**Contraintes techniques importantes pour le design :**
- Pas de framework CSS lourd (pas de React, Vue, Angular)
- Tailwind CDN utilisable (pages admin/pro)
- CSS custom pour les pages critiques (réception, PDF)
- Vanilla JavaScript uniquement
- Les SVG inline sont générés côté serveur (Python)
- Le PDF est généré via HTML/CSS → xhtml2pdf (CSS limité, pas de flexbox/grid en PDF)

---

## 25. FLUX UTILISATEUR PRINCIPAUX

### 25.1 Flux MDC — Réception AUTONOME
```
Login → /pro/projets/ → [Sélectionner projet] → [Réceptionner]
→ /reception (Étape 1: infos) → (Étape 2: sélection éléments)
→ (Étape 3: saisie mesures terrain) → (Étape 4: signatures + export)
→ PDF généré + archivé R2 + email envoyé
```

### 25.2 Flux MDC — Traitement demande PARTENARIAT
```
Login → /pro/demandes/ → [Voir demande en attente]
→ [Accuser réception] → [Accepter]
→ [Commencer la réception] → /reception (pré-rempli depuis la demande)
→ (saisie mesures) → (signatures) → [Verdict: Validée/Non validée/À reprendre]
→ PDF généré + demande clôturée + visible sur la carte
```

### 25.3 Flux ET — Soumission demande PARTENARIAT
```
Login → /pro/projets/ → [Sélectionner projet] → [Nouvelle demande]
→ /pro/demandes/nouvelle → [Sélectionner PK + éléments] → [Planifier] → [Soumettre]
→ Attente traitement MDC...
→ Notification (email) → [Voir verdict sur /pro/demandes/<id>]
```

### 25.4 Flux ADMIN — Configuration projet
```
/admin/ → [Créer projet] → [Upload Excel] → [Logos MDC/ET]
→ [Associer entreprises MDC + ET] → [Ajouter opérateurs]
→ Projet prêt pour utilisation
```

---

## 26. NOTES POUR LA REFONTE GRAPHIQUE

### 26.1 Priorités absolues
1. **La page de réception (Page 12) est le cœur de l'application** — elle doit être parfaite sur tablette/smartphone en plein soleil
2. **Les tableaux de saisie** doivent avoir des inputs très larges et du contraste maximal
3. **Les statuts de conformité** (vert/rouge) doivent être immédiatement lisibles à 1 mètre de distance
4. **La navigation entre les étapes** doit être évidente et accessible à une main

### 26.2 Ce qu'il faut absolument conserver
- Dark mode (fond sombre) — impératif pour le terrain
- Couleur cyan `#00ffff` pour RECEPTA (identité de marque)
- Logo CSS 2×2 dots (pas d'image)
- Distinction visuelle claire AUTONOME (bleu) vs PARTENARIAT (violet)
- Distinction MDC (bleu) vs ET (ambre/orange) dans tous les composants partagés

### 26.3 Opportunités d'amélioration UX
- Ajouter un mode "Nuit" encore plus sombre (chantier en extérieur la nuit)
- Ajouter un mode "Haute Visibilité" (contrastes extrêmes, touches encore plus grandes)
- Animations d'erreur plus claires (mesure hors tolérance = feedback haptic + visuel fort)
- Progress indicator pendant la génération PDF (étapes numérotées)
- Raccourcis clavier pour la saisie rapide en mode bureau (Tab, Enter, flèches)
- Auto-save du formulaire de réception (localStorage toutes les 30s)
- Mode hors-ligne détecté avec banner de notification

### 26.4 Animations — Philosophie générale
- **Utiles, pas décoratives** : chaque animation doit communiquer un état ou guider l'attention
- **Rapides** : max 300ms pour les transitions UI, 600ms pour les entrées de page
- **Non bloquantes** : jamais d'animation qui empêche l'interaction
- **Désactivables** : `prefers-reduced-motion` toujours respecté
- **Terrain** : sur tablette avec écran de protège-lunette, les animations trop subtiles ne servent à rien — privilégier les feedbacks nets et contrastés

---

*Document généré par RECEPTA OPTILAB — Mai 2026*  
*Pour usage interne — Refonte UI/UX*
