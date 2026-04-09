# RECEPTA V2 — Système de Réception Collaborative MDC / Entreprise

> Document de conception — Version 2 (non implémentée)
> Rédigé le 2026-04-09

---

## 1. Vision

RECEPTA V1 est un outil de réception topographique mono-utilisateur : la Mission de Contrôle (MDC) saisit tout elle-même. RECEPTA V2 introduit une **collaboration formelle** entre deux acteurs distincts du chantier :

- **L'Entreprise** — exécute les travaux, demande les réceptions
- **La Mission de Contrôle (MDC)** — valide, accepte ou refuse les réceptions

Chaque projet dispose de ses propres membres, avec des droits et des vues strictement séparés selon le rôle.

---

## 2. Acteurs et rôles

| Rôle | Qui | Ce qu'il peut faire |
|------|-----|---------------------|
| `admin` | OPTILAB (toi) | Tout — gestion des projets, clients, accès |
| `mdc` | Ingénieur / technicien MDC | Recevoir les demandes, accuser réception, lancer la réception officielle, valider ou refuser |
| `entreprise` | Conducteur de travaux, chef de chantier | Simuler une réception (brouillon privé), soumettre une demande de réception formelle |

---

## 3. Nouveaux objets du modèle de données

### 3.1 Projet

```
Projet
  ├── id
  ├── nom                    : str
  ├── description            : str
  ├── excel_key              : str (R2 — cotes théoriques)
  ├── pk_debut               : str
  ├── pk_fin                 : str
  ├── tolerance_defaut       : float (cm)
  ├── actif                  : bool
  └── membres[]              : [{ user_id, role: "mdc" | "entreprise" }]
```

Un utilisateur peut appartenir à plusieurs projets avec des rôles différents.

### 3.2 DemandeReception

```
DemandeReception
  ├── id
  ├── numero                 : str (ex: "DR-2026-042") — généré automatiquement
  ├── projet_id              → FK Projet
  ├── demandeur_id           → FK User (entreprise)
  ├── pk_debut               : str
  ├── pk_fin                 : str
  ├── parties                : JSON (côtés, éléments à réceptionner)
  ├── date_souhaitee         : date
  ├── heure_souhaitee        : time
  ├── observations_demande   : text (commentaire libre entreprise)
  ├── statut                 : enum (voir §4)
  ├── motif_refus            : text (si refusée)
  ├── created_at             : datetime ← horodatage = preuve légale
  ├── accuse_at              : datetime ← horodatage accusé MDC
  └── fiche_id               → FK FicheReception (si réception effectuée)
```

### 3.3 FicheReception (existant, enrichi)

Ajout d'une FK vers `DemandeReception` pour tracer la chaîne complète :
demande → accusé → réception → fiche signée.

---

## 4. Workflow et statuts

```
[ENTREPRISE]                         [MDC]

  Simule en mode brouillon
  (privé, jamais visible MDC)
          │
          ▼
  Soumet une DemandeReception
  statut = "en_attente"
          │                ─────────────────────────→ Reçoit notification email
          │                                           Accuse réception
          │                ←─────────────────────────
  statut = "accusée"
  (email de confirmation
   horodaté envoyé aux 2 parties)
          │
          │                           MDC examine la demande
          │                           ┌──────────────────────┐
          │                           │ Accepte              │
          │                           │ statut = "acceptée"  │
          │                           │                      │
          │                           │ OU                   │
          │                           │                      │
          │                           │ Refuse               │
          │                           │ statut = "refusée"   │
          │                           │ + motif_refus        │
          │                           └──────────────────────┘
          │
          ▼ (si acceptée)
          MDC lance la réception
          → paramétrage pré-rempli
            depuis la demande
          → saisie des mesures
          → génération fiche PDF
          statut = "clôturée"
          fiche_id = FicheReception.id
```

---

## 5. Mode simulation entreprise

L'entreprise dispose d'un **mode brouillon** dans l'application. C'est une réception simulée, privée, sans archivage R2 et sans valeur officielle.

**Ce qu'ils peuvent faire :**
- Charger les cotes théoriques du projet
- Saisir leurs cotes pratiques mesurées sur le terrain
- Faire des interpolations
- Voir leur propre tableau de bord brouillon

**Ce qu'ils NE peuvent PAS faire :**
- Voir les tolérances réelles (affichage masqué en mode simulation)
- Générer une fiche de réception officielle
- Archiver dans R2
- Voir les vraies réceptions MDC

**Objectif :** permettre à l'entreprise de vérifier son propre travail avant de demander une réception, sans pouvoir calibrer pour tricher.

---

## 6. Règles métier importantes

### Unicité des demandes actives
Une seule demande active (statut `en_attente` ou `accusée`) par tranche de PK et par projet. Si une nouvelle demande couvre une tranche déjà en cours, elle est bloquée avec un message explicite.

### Délai de réponse MDC
Si la MDC n'accuse pas réception dans un délai configurable (ex: 48h), une notification de rappel est envoyée automatiquement. Ce délai peut être paramétré par projet.

### Flux de reprise après non-conformité
Si la réception est non-conforme, la MDC peut clôturer la fiche avec statut `non_conforme`. L'entreprise peut ensuite soumettre une **nouvelle demande** sur la même tranche, avec référence à la demande originale (`demande_parent_id`). L'historique des reprises est ainsi tracé.

### Email horodaté = preuve contractuelle
À chaque changement de statut (`en_attente` → `accusée`, `accusée` → `acceptée`/`refusée`), un email est envoyé aux deux parties via Resend avec :
- Le numéro de demande
- Le statut
- L'horodatage exact
- Un PDF récapitulatif en pièce jointe

---

## 7. Limites identifiées et réponses

| Limite | Risque | Réponse envisagée |
|--------|--------|-------------------|
| Simulation pour calibrer | L'entreprise corrige le terrain après avoir vu les écarts | Masquer les tolérances en mode simulation |
| Qui répond côté MDC ? | Demande reçue par tous, traitée par personne | Système d'assignation ou boîte commune par projet |
| Délai MDC bloque le chantier | Équipes en attente, matériel immobilisé | Délai contractuel paramétrable + rappels automatiques |
| Valeur légale limitée | Timestamp BDD insuffisant légalement | PDF horodaté envoyé par email aux deux parties à chaque étape |
| Données offline | Zéro réseau fréquent sur chantier | À anticiper : mode offline + sync différée (V3) |
| Signature électronique | Canvas ≠ signature qualifiée eIDAS | Intégration service e-signature (V3 ou module payant) |
| Isolation simulation | Données brouillon visibles si mal implémenté | Isolation au niveau des requêtes BDD, pas juste un flag |

---

## 8. Impact sur le modèle économique

La V2 ouvre deux modèles de facturation possibles :

**Option A — Abonnement par projet**
Le maître d'ouvrage ou la MDC souscrit un projet. L'accès entreprise est inclus dans le tarif projet. C'est le modèle le plus propre contractuellement.

**Option B — Abonnement par rôle**
MDC et Entreprise ont chacune un abonnement. Plus complexe à gérer mais potentiellement plus rentable sur les grands projets multi-intervenants.

---

## 9. Ce qui reste à construire pour la V2

- [ ] Modèle `Projet` avec gestion des membres (ManyToMany User ↔ Projet)
- [ ] Modèle `DemandeReception` avec workflow de statuts
- [ ] Interface entreprise : formulaire de demande + vue de suivi
- [ ] Interface MDC : boîte de réception des demandes + actions (accuser, accepter, refuser)
- [ ] Pré-remplissage automatique de la réception depuis une demande acceptée
- [ ] Emails automatiques à chaque changement de statut (Resend)
- [ ] Mode simulation entreprise (flag session, pas d'archivage, tolérances masquées)
- [ ] Flux de reprise (demande liée à une demande parent)
- [ ] Numérotation automatique des demandes (DR-YYYY-NNN)

---

## 10. Ce qui est déjà utilisable en V1 pour la V2

| Existant V1 | Réutilisé en V2 |
|-------------|-----------------|
| Système auth Flask-Login + rôles | Base pour les rôles `mdc` / `entreprise` |
| FicheReception + archivage R2 | Liée à la DemandeReception |
| Envoi email Resend avec PDF | Emails de notification à chaque statut |
| Panel admin | Gestion des projets et membres |
| Template fiche PDF | Identique, avec ajout du numéro de demande |

---

*Ce document est une feuille de route — aucune ligne de code V2 n'a été écrite à ce jour.*
*Implémenter dans l'ordre : Projet + Membres → DemandeReception → Mode simulation → Flux reprise.*

---

## 11. Gestion des contacts et emails par partie prenante

Chaque membre d'un projet a une adresse email configurée, utilisée pour toutes les notifications automatiques. Ce n'est pas forcément l'email de connexion — un chef de projet peut avoir un email de notification différent (ex: boîte partagée d'équipe).

```
MembreProjet
  ├── user_id          → FK User
  ├── projet_id        → FK Projet
  ├── role             : "mdc" | "entreprise"
  ├── email_notif      : str (peut différer de user.email)
  ├── nom_affichage    : str (ex: "Bureau de contrôle CEREMA")
  └── actif            : bool
```

**Règles de notification par événement :**

| Événement | Destinataires |
|-----------|---------------|
| Nouvelle demande de réception | Tous les membres MDC du projet |
| Accusé de réception | Demandeur entreprise + responsable MDC assigné |
| Demande acceptée | Demandeur + tous membres entreprise du projet |
| Demande refusée | Demandeur + motif en clair |
| Réception clôturée (conforme) | Tous les membres du projet |
| Réception non-conforme | Demandeur + chef de projet MDC |
| Rappel délai dépassé | Tous les membres MDC |
| Rapport mensuel | Liste configurable par projet |

---

## 12. Modèle de projet multi-portions

Un grand projet peut couvrir plusieurs tronçons distincts, géographiquement séparés, avec des entreprises et des équipes MDC potentiellement différentes.

```
Projet
  └── Portion[]
        ├── id
        ├── projet_id          → FK Projet
        ├── nom                : str (ex: "Tronçon Nord", "Échangeur Est")
        ├── pk_debut           : str
        ├── pk_fin             : str
        ├── excel_key          : str (R2 — cotes théoriques propres à cette portion)
        ├── membres_specifiques: bool (si True, override les membres du projet parent)
        └── coordonnees_gps    : JSON (voir §14)
```

**Exemple concret — déviation routière 8km :**
```
Projet: "Déviation RD45 — Commune de Valence"
  ├── Portion 1 : "Tronçon Nord"        PK 0+000 → PK 3+500  (Entreprise A)
  ├── Portion 2 : "Échangeur Est"        PK 3+500 → PK 5+200  (Entreprise B)
  └── Portion 3 : "Tronçon Sud"          PK 5+200 → PK 8+000  (Entreprise A)
```

Chaque demande de réception est liée à une `Portion`, pas directement au `Projet`.

---

## 13. Données structurées pour le dashboard — changement fondamental

### Le problème de la V1
En V1, les résultats de réception sont stockés comme **HTML dans R2** (non requêtable). Pour un dashboard, il faut des données agrégables en base SQL.

### Solution : enrichir FicheReception + ajouter ReceptionPoint

```
FicheReception (enrichi)
  ├── ... (existant)
  ├── demande_id         → FK DemandeReception
  ├── portion_id         → FK Portion
  ├── pk_debut           : str
  ├── pk_fin             : str
  ├── conformite_pct     : float  ← calculé et stocké à la clôture
  ├── nb_points_total    : int
  ├── nb_points_conformes: int
  ├── nb_points_nc       : int
  ├── statut_global      : "conforme" | "non_conforme" | "partiel"
  └── tentative_num      : int (1 = première réception, 2 = reprise, etc.)

ReceptionPoint  ← nouvelle table, une ligne par PK × élément
  ├── fiche_id           → FK FicheReception
  ├── pk                 : str
  ├── element_label      : str
  ├── cote_theorique     : float
  ├── cote_mesuree       : float
  ├── ecart              : float
  ├── statut             : "ok" | "nc_pos" | "nc_neg" | "interpolé"
  └── observation        : text
```

`ReceptionPoint` permet les requêtes dashboard comme :
- "Quel est le statut du PK 2+350, élément Tablier_Fini ?"
- "Combien de NC sur la Portion 1 ce mois-ci ?"
- "Quels éléments ont le plus de reprises sur tout le projet ?"

---

## 14. Vue cartographique du projet

### Représentation GPS des tronçons

Chaque `Portion` peut avoir des coordonnées GPS optionnelles, stockées comme une liste de points (tracé GPX simplifié) :

```json
{
  "type": "linestring",
  "points": [
    { "pk": "0+000", "lat": 44.9334, "lng": 4.8921 },
    { "pk": "0+500", "lat": 44.9378, "lng": 4.8956 },
    { "pk": "1+000", "lat": 44.9421, "lng": 4.8989 }
  ]
}
```

Si pas de coordonnées → la vue cartographique est remplacée par la vue linéaire PK.

### Modes de saisie des coordonnées

| Mode | Quand | Comment |
|------|-------|---------|
| Import GPX/KML | Fichier GPS du levé d'implantation disponible | Upload dans le panel admin |
| Saisie manuelle | Petits projets, tracé simple | Formulaire PK → lat/lng dans admin |
| Dessin sur carte | Tracé approximatif | Interface Leaflet.js + clic |

### Rendu carte (Leaflet.js + OpenStreetMap)

- Tracé de chaque portion comme une **polyligne colorée**
- Couleur = statut d'avancement (voir §15)
- Clic sur un segment → popup : portion, % conformité, dernière réception
- Pas de clé API requise (OpenStreetMap est libre)

---

## 15. Vue d'ensemble du projet (dashboard linéaire)

Pour les projets sans coordonnées GPS ou en complément de la carte, une **vue linéaire** représente l'avancement sur l'axe PK.

### Code couleur statut par tranche

| Couleur | Statut |
|---------|--------|
| Gris clair | Aucune demande — non encore entamé |
| Bleu | Demande soumise — en attente MDC |
| Orange | Réception en cours |
| Vert | Réceptionné conforme (1re tentative) |
| Vert foncé | Réceptionné conforme (après reprise) |
| Rouge | Non-conforme — reprise en attente |
| Violet | Refusé par MDC |

### Règle d'agrégation du statut

Un segment PK est "conforme" **uniquement si tous ses éléments sont conformes** lors de la dernière réception. Si 14 éléments sur 15 sont OK → statut "partiel" (orange foncé). Le détail par élément est visible au clic/survol.

### Informations visibles par tranche au survol

```
PK 2+000 → PK 2+500  |  Portion 1 : Tronçon Nord
Dernière réception : 2026-03-15  |  Opérateur : DUPONT
Résultat : ✅ Conforme — 97.3%  (2e tentative)
Éléments : 15/15 conformes
[ Voir la fiche ]  [ Historique des réceptions ]
```

---

## 16. Rapports automatiques

### Types de rapports

| Type | Contenu | Déclenchement |
|------|---------|---------------|
| Rapport journalier | Réceptions du jour, demandes en attente | Manuel ou automatique à 18h |
| Rapport hebdomadaire | Synthèse semaine + NC non résolues | Lundi matin automatique |
| Rapport mensuel | Bilan complet, statistiques, courbe d'avancement | 1er du mois automatique |
| Rapport de portion | État complet d'une portion | À la demande |
| Rapport projet | Synthèse globale de tout le projet | À la demande |

### Contenu d'un rapport mensuel

```
RAPPORT MENSUEL — [Projet] — [Mois/Année]
─────────────────────────────────────────
1. Résumé exécutif
   - % du linéaire réceptionné
   - Taux de conformité global
   - Nombre de demandes traitées

2. Activité du mois
   - Tableau : demandes reçues / traitées / en attente
   - Tableau : réceptions réalisées par portion

3. Non-conformités
   - Liste des NC actives
   - NC résolues ce mois (avec nb tentatives)
   - NC récurrentes (même PK, même élément > 1 fois)

4. Statistiques par élément
   - Quel élément a le plus de NC ? (ex: Tablier_Fini 12% NC)
   - Quel élément est toujours conforme ?

5. Courbe d'avancement
   - Linéaire réceptionné cumulé (graphique)
   - Projection à fin de projet

6. Annexes : fiches de réception du mois (liens R2)
```

### Génération technique

- Rendu Jinja2 → xhtml2pdf (même stack que les fiches)
- Route : `GET /api/rapport?projet_id=X&type=mensuel&periode=2026-03`
- Envoyé par email via Resend à la liste configurable par projet
- Archivé dans R2 : `rapports/{projet_id}/{type}/{periode}.pdf`

### Problème de performance

Un projet de 5km avec 200 PK × 15 éléments × 20 réceptions dans le mois = **60 000 lignes ReceptionPoint** à agréger. Sur Render (instance gratuite), cela peut être lent.

**Solution : table de statistiques pré-calculées**
```
ProjetStats
  ├── projet_id / portion_id
  ├── pk_debut / pk_fin
  ├── date_calcul
  ├── pct_lineaire_receptionnee
  ├── taux_conformite_global
  ├── nb_demandes_total
  ├── nb_nc_actives
  └── elements_stats_json
```
Mise à jour après chaque clôture de réception. Le dashboard lit `ProjetStats`, pas `ReceptionPoint`.

---

## 17. Problèmes architecturaux identifiés

### Problème 1 — Granularité des requêtes spatiales
"Quel est le statut du PK 2+350 ?" est ambigu si une réception couvre PK 2+000 → 2+500 et une autre PK 2+300 → 2+800 (chevauchement). **Règle imposée** : pas de chevauchement autorisé entre deux demandes actives (validé à la soumission).

### Problème 2 — Coordonnées GPS manquantes
La plupart des fichiers Excel topographiques n'ont que des labels PK, pas de GPS. La vue cartographique est **optionnelle** et se dégrade gracieusement en vue linéaire PK si pas de coordonnées.

### Problème 3 — Fiches V1 non migrables
Les fiches HTML archivées en V1 n'ont pas de `ReceptionPoint` associés. Elles restent consultables dans l'historique mais ne contribuent pas aux statistiques dashboard. Séparation nette V1 / V2 dès le premier jour.

### Problème 4 — Conflits de statut sur élément partiel
Si 14 éléments sur 15 sont conformes lors d'une réception : la MDC peut choisir entre "tout rejeter" ou "valider partiellement". Implique un statut `partiel` avec une liste explicite des éléments non validés, qui devront faire l'objet d'une nouvelle demande ciblée.

### Problème 5 — Reports offline
La génération des rapports mensuels ne doit pas bloquer le serveur principal (xhtml2pdf est synchrone). Sur Render sans worker dédié, il faudra soit :
- Accepter un délai (rapport généré en ~10-30s, envoyé par email sans bloquer l'UI)
- Déclencher le rapport en tâche de fond avec une réponse immédiate "rapport en cours de génération"

---

## 18. Checklist complète V2 (mise à jour)

### Fondations (à faire en premier)
- [ ] Modèle `Portion` + `MembreProjet` avec emails de notification
- [ ] Modèle `DemandeReception` avec workflow de statuts et horodatage
- [ ] Enrichissement `FicheReception` avec champs structurés
- [ ] Nouvelle table `ReceptionPoint` (une ligne par PK × élément)
- [ ] Table `ProjetStats` pré-calculée

### Workflow collaboratif
- [ ] Interface entreprise : formulaire demande + suivi statuts
- [ ] Interface MDC : boîte de réception + actions (accuser / accepter / refuser)
- [ ] Pré-remplissage réception depuis demande acceptée
- [ ] Flux de reprise avec `demande_parent_id` et `tentative_num`
- [ ] Emails automatiques Resend à chaque changement de statut
- [ ] Mode simulation entreprise (flag session, tolérances masquées, pas d'archivage)

### Dashboard et visualisation
- [ ] Vue linéaire PK avec code couleur par statut de tranche
- [ ] Détail au survol/clic par tranche (popup)
- [ ] Vue cartographique Leaflet.js (optionnelle, si coordonnées disponibles)
- [ ] Import GPX/KML ou saisie manuelle de coordonnées GPS par portion
- [ ] Page stats projet : taux de conformité, avancement, NC actives
- [ ] Filtres par date, portion, élément, statut

### Rapports
- [ ] Template Jinja2 rapport mensuel + journalier
- [ ] Route API `/api/rapport` avec paramètres
- [ ] Envoi automatique par email (Resend) aux destinataires configurés
- [ ] Archivage R2 des rapports générés
- [ ] Mise à jour de `ProjetStats` après chaque clôture de fiche

---

*Dernière mise à jour : 2026-04-09*
*Sections 11-18 ajoutées : emails par partie prenante, multi-portions, données structurées dashboard, cartographie, vue linéaire, rapports automatiques, problèmes architecturaux.*
