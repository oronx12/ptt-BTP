# app/services/calculation_service.py
"""
Service de calcul des côtes théoriques depuis la config parsée.

Point d'entrée principal : cotes_pour_pk(pk_str, config)
Point secondaire          : elements_disponibles(config)

Ces fonctions sont stateless — elles ne touchent ni la BDD ni R2.

══════════════════════════════════════════════════════════════════
PRINCIPE DE CALCUL
══════════════════════════════════════════════════════════════════

TERRASSEMENT
────────────
  z_axe      ← AXE_PROFIL_LONG, interpolé au PK
  e_couche   ← AXE_SECTIONS   , offset cumulé signé négatif depuis z_axe
               ex : e_GNT = −0.220  →  z_fond_GNT = z_axe + (−0.220)

  z_fond_couche = z_axe + e_couche        ← addition directe

  Points transversaux (TER_PROFIL_TYPE, même pour toutes les couches) :
    z_ter = z_fond_couche − (pente / 100) × dist_axe

ASSAINISSEMENT (G ou D)
───────────────────────
  z_radier   ← ASS_LONG, interpolé au PK (côte prédéfinie du fil d'eau)
  offset_elt ← ASG_SECTIONS / ASD_SECTIONS, offset signé depuis z_radier
               ex : AG_BP = +0.250  →  z_BP_G = z_radier + 0.250

  z_element = z_radier + offset_elt       ← même principe qu'au-dessus

Chaque résultat porte : key, label, cote, groupe, couche, z_ref, description
══════════════════════════════════════════════════════════════════
"""
from .excel_service import active_section, interp_z, _pk_to_m, _safe_float

# Ordre d'affichage stratigraphique (haut → bas)
_LAYER_ORDER = ['BB', 'GB4', 'GB', 'GNT', 'GRH', 'FF', 'SOL']


# ── Helpers internes ──────────────────────────────────────────────────────────

def _param(params: dict, keyword: str) -> float | None:
    """Première valeur float dont la clé contient `keyword` (insensible casse)."""
    kw = keyword.upper()
    for k, v in params.items():
        if kw in str(k).upper():
            f = _safe_float(v)
            if f is not None:
                return f
    return None


def _layer_offset(params: dict, layer: str) -> float | None:
    """
    Offset cumulé signé d'une couche AXE (cherche _E_<LAYER> dans les params).
    La valeur est déjà négative et cumulative depuis z_axe.
    """
    target = f'_E_{layer.upper()}'
    for k, v in params.items():
        if target in str(k).upper():
            return _safe_float(v)
    return None


def _pk_in_range(pk_m: int, pt: dict) -> bool:
    """True si pk_m est dans la plage de validité d'un point TER."""
    if pt['pk_debut_m'] > pk_m:
        return False
    fin = pt.get('pk_fin_m')
    if fin is not None and pk_m > fin:
        return False
    return True


def _interp_fil_eau(long_data: list, pk_m: int) -> float | None:
    """
    Interpolation linéaire d'une côte depuis un onglet longitudinal
    (ass_long, ass_long_g ou ass_long_d).

    Scanne toutes les entrées pour trouver la première colonne non-structurelle
    (n'importe quel préfixe calculable) car _read_longitudinal n'insère une clé
    que si la valeur est non-None, donc la première entrée peut être incomplète.
    """
    if not long_data:
        return None
    z_col = None
    for entry in long_data:
        candidate = next(
            (k for k in entry if k not in ('pk', 'pk_m')),
            None,
        )
        if candidate:
            z_col = candidate
            break
    if z_col is None:
        return None
    profil = [{'pk_m': r['pk_m'], 'z_axe': r[z_col]}
              for r in long_data if z_col in r]
    if not profil:
        return None
    return interp_z(profil, pk_m)


def _interp_radier(config: dict, pk_m: int, side: str = 'G') -> float | None:
    """
    Retourne la côte fil d'eau pour le côté donné ('G' ou 'D') au PK pk_m.

    Priorité :
      1. ass_long_g / ass_long_d  (onglets AG_* / AD_*)
      2. ass_long générique       (onglet ASS_*)
    """
    if side == 'G':
        z = _interp_fil_eau(config.get('ass_long_g', []), pk_m)
    else:
        z = _interp_fil_eau(config.get('ass_long_d', []), pk_m)
    if z is None:
        z = _interp_fil_eau(config.get('ass_long', []), pk_m)
    return z


def _ass_elements_from_params(params: dict, pfx: str) -> list[dict]:
    """
    Extrait tous les éléments ASG/ASD d'une section.
    Retourne [{elt_name, offset}] pour chaque colonne dont le préfixe est pfx.
    """
    elts = []
    for k, v in params.items():
        parts = str(k).split('_')
        if parts[0].upper() != pfx.upper():
            continue
        offset = _safe_float(v)
        if offset is None:
            continue
        elt_name = '_'.join(parts[1:])
        if not elt_name:
            continue
        elts.append({'elt_name': elt_name, 'offset': offset})
    return elts


# ── Fonction principale ───────────────────────────────────────────────────────

def cotes_pour_pk(pk_str: str, config: dict) -> list:
    """
    Calcule les côtes théoriques pour un PK depuis la config parsée.

    Résultat : liste de {key, label, cote, groupe, couche, z_ref, description}
    Groupes   : 'AXE' | 'TER' | 'ASG' | 'ASD'
    """
    pk_m = _pk_to_m(pk_str)
    if pk_m is None:
        return []

    z_axe = interp_z(config.get('profil_long', []), pk_m)
    if z_axe is None:
        return []

    result = []

    # ── TERRASSEMENT ──────────────────────────────────────────────────────────

    # 1. AXE : surface + couches
    axe_secs = config.get('sections', {}).get('AXE', [])
    axe_sec  = active_section(axe_secs, pk_m)
    axe_p    = axe_sec['params'] if axe_sec else {}

    # Construire la liste ordonnée des couches avec leur z_ref
    couches_axe: list[dict] = []

    z_surf = round(z_axe, 4)
    couches_axe.append({'key': 'surface', 'label': 'Surface axe', 'z_ref': z_surf})
    result.append({
        'key':         'AXE_surface',
        'label':       'Surface axe',
        'cote':        z_surf,
        'groupe':      'AXE',
        'couche':      'surface',
        'z_ref':       z_surf,
        'description': "Surface de la chaussée à l'axe (NGF)",
    })

    for layer in _LAYER_ORDER:
        e_couche = _layer_offset(axe_p, layer)
        if e_couche is not None:
            z_fond = round(z_axe + e_couche, 4)   # e_couche déjà négatif et cumulé
            couche_key = f'fond_{layer}'
            couches_axe.append({'key': couche_key, 'label': f'Fond {layer}', 'z_ref': z_fond})
            result.append({
                'key':         f'AXE_{couche_key}',
                'label':       f'Fond {layer}',
                'cote':        z_fond,
                'groupe':      'AXE',
                'couche':      couche_key,
                'z_ref':       z_fond,
                'description': f'Fond couche {layer} (offset {e_couche:+.4f} m depuis surface)',
            })

    # 2. TER : points transversaux — un jeu par couche AXE
    ter_pts: list[dict] = []
    seen_ter: set = set()
    for pt in config.get('ter_points', []):
        lbl = pt.get('label', '')
        if not lbl or lbl in seen_ter:
            continue
        if not _pk_in_range(pk_m, pt):
            continue
        dist  = pt.get('dist_axe_m')
        pente = pt.get('pente_pct') or 0.0
        side  = 'G' if 'G' in str(pt.get('cote', '')).upper() else 'D'
        if dist is not None:
            seen_ter.add(lbl)
            ter_pts.append({'lbl': lbl, 'dist': dist, 'pente': pente, 'side': side})

    for c in couches_axe:
        z_ref = c['z_ref']
        for pt in ter_pts:
            lbl   = pt['lbl']
            dist  = pt['dist']
            pente = pt['pente']
            side  = pt['side']
            z_ter = round(z_ref - abs(pente) / 100.0 * dist, 4)
            result.append({
                'key':         f"TER_{lbl}__{c['key']}",
                'label':       f"{lbl.replace('_', ' ')} ({side})",
                'cote':        z_ter,
                'groupe':      'TER',
                'couche':      c['key'],
                'z_ref':       z_ref,
                'description': (
                    f"À {dist:.1f} m de l'axe, côté {side} — "
                    f"réf. {c['label']} ({z_ref:.4f} m NGF)"
                ),
            })

    # ── ASSAINISSEMENT ────────────────────────────────────────────────────────
    # Référence : côte fil d'eau par côté depuis AG_*/AD_* (ou ASS_* en fallback)

    for grp, side, pfx in (('ASG', 'G', 'AG'), ('ASD', 'D', 'AD')):
        secs = config.get('sections', {}).get(grp, [])
        sec  = active_section(secs, pk_m)
        if sec is None:
            continue

        z_fe = _interp_radier(config, pk_m, side=side)
        if z_fe is None:
            continue

        p    = sec['params']
        elts = _ass_elements_from_params(p, pfx)

        for elt in elts:
            elt_name = elt['elt_name']
            offset   = elt['offset']
            z_elt    = round(z_fe + offset, 4)
            label    = elt_name.replace('_', ' ').capitalize()
            result.append({
                'key':         f'{grp}_{elt_name.lower()}',
                'label':       f'{label} ({side})',
                'cote':        z_elt,
                'groupe':      grp,
                'couche':      elt_name.lower(),
                'z_ref':       round(z_fe, 4),
                'description': (
                    f'{label} côté {side} — '
                    f'z_fil_eau_{side}={z_fe:.4f} + offset {offset:+.4f} m'
                ),
            })

    return result


# ── Éléments disponibles (sans valeur de côte) ────────────────────────────────

def elements_disponibles(config: dict) -> list:
    """
    Retourne la liste des éléments mesurables depuis la config.
    Chaque élément : {key, label, groupe, couche, description}

    TER : un jeu par couche AXE.
    ASG / ASD : un élément par paramètre de section (offsets depuis z_radier).
    """
    elts = []

    # ── AXE : surface + couches ───────────────────────────────────────────────
    couches_axe: list[dict] = []

    if config.get('profil_long'):
        couches_axe.append({'key': 'surface', 'label': 'Surface axe'})
        elts.append({
            'key':         'AXE_surface',
            'label':       'Surface axe',
            'groupe':      'AXE',
            'couche':      'surface',
            'description': "Surface de la chaussée à l'axe",
        })

        axe_secs = config.get('sections', {}).get('AXE', [])
        axe_p    = axe_secs[0]['params'] if axe_secs else {}

        for layer in _LAYER_ORDER:
            e = _layer_offset(axe_p, layer)
            if e is not None:
                couche_key = f'fond_{layer}'
                couches_axe.append({'key': couche_key, 'label': f'Fond {layer}'})
                elts.append({
                    'key':         f'AXE_{couche_key}',
                    'label':       f'Fond {layer}',
                    'groupe':      'AXE',
                    'couche':      couche_key,
                    'description': f'Fond couche {layer} (offset {e:+.4f} m)',
                })

    # ── TER : un jeu par couche AXE ───────────────────────────────────────────
    seen_ter: set = set()
    ter_pts: list[dict] = []
    for pt in config.get('ter_points', []):
        lbl = pt.get('label', '')
        if lbl and lbl not in seen_ter:
            seen_ter.add(lbl)
            side = 'G' if 'G' in str(pt.get('cote', '')).upper() else 'D'
            dist = pt.get('dist_axe_m')
            ter_pts.append({'lbl': lbl, 'side': side, 'dist': dist})

    for c in couches_axe:
        for pt in ter_pts:
            lbl  = pt['lbl']
            side = pt['side']
            dist = pt['dist']
            elts.append({
                'key':         f"TER_{lbl}__{c['key']}",
                'label':       f"{lbl.replace('_', ' ')} ({side})",
                'groupe':      'TER',
                'couche':      c['key'],
                'description': (
                    f"À {dist:.1f} m axe, côté {side} — réf. {c['label']}"
                    if dist else f"Point TER {lbl} ({side}) — réf. {c['label']}"
                ),
            })

    # ── ASG / ASD : éléments depuis ASG/ASD_SECTIONS (offsets depuis z_fil_eau) ─
    for grp, side, pfx in (('ASG', 'G', 'AG'), ('ASD', 'D', 'AD')):
        secs = config.get('sections', {}).get(grp, [])
        if not secs:
            continue
        p        = secs[0]['params']
        elts_ass = _ass_elements_from_params(p, pfx)
        has_ref  = bool(
            config.get('ass_long_g' if side == 'G' else 'ass_long_d')
            or config.get('ass_long')
        )

        for elt in elts_ass:
            elt_name = elt['elt_name']
            offset   = elt['offset']
            label    = elt_name.replace('_', ' ').capitalize()
            ref_src  = f"AG_Z_fil_eau" if side == 'G' else f"AD_Z_fil_eau"
            desc = (
                f'{label} ({side}) — z_fil_eau_{side} + offset {offset:+.4f} m  [réf. {ref_src}]'
                if has_ref
                else f'{label} ({side}) — offset {offset:+.4f} m (référence fil d\'eau manquante)'
            )
            elts.append({
                'key':         f'{grp}_{elt_name.lower()}',
                'label':       f'{label} ({side})',
                'groupe':      grp,
                'couche':      elt_name.lower(),
                'description': desc,
            })

    return elts
