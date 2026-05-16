# app/services/visualization_service.py
"""
Service de visualisation du modèle RECEPTA.
Génère :
  - Un SVG de profil en travers type (depuis config AXE/ASG/ASD/TER)
  - Le contexte de données pour le template Jinja2
"""
import json

# Couleurs des couches de chaussée
_LAYER_COLORS = {
    'BB':  '#2c2c2c',
    'GB':  '#4a4a4a',
    'GNT': '#8a8a8a',
    'GRH': '#8a8a8a',
    'FF':  '#5b4ca8',
    'SOL': '#8b6914',
}
_LAYER_ORDER = ['BB', 'GB4', 'GB', 'GNT', 'GRH', 'FF', 'SOL']

_CANAL_COLOR_G  = '#1a6fb5'
_CANAL_COLOR_D  = '#7c3aed'
_TER_DOT_COLOR  = '#f59e0b'
_SURFACE_COLOR  = '#1e3a5f'


def _find_param(params: dict, keyword: str, default=None):
    """Première valeur dont la clé contient `keyword` (insensible à la casse)."""
    kw = keyword.upper()
    for k, v in params.items():
        if kw in str(k).upper() and isinstance(v, (int, float)):
            return float(v)
    return default


def _extract_layers(params: dict) -> list:
    """Extrait les épaisseurs de couches depuis les params d'une section AXE."""
    layers = []
    for k, v in params.items():
        if not isinstance(v, (int, float)):
            continue
        ku = k.upper()
        for layer_name in _LAYER_ORDER:
            if f'_E_{layer_name}' in ku or ku.endswith(f'_E_{layer_name}'):
                color = next(
                    (c for n, c in _LAYER_COLORS.items() if n in ku),
                    '#777777'
                )
                if not any(la['name'] == layer_name for la in layers):
                    lbl = (f'{layer_name} {int(round(v * 100))}cm'
                           if v < 1 else f'{layer_name} {v:.2f}m')
                    layers.append({
                        'name': layer_name,
                        'thickness_m': float(v),
                        'color': color,
                        'label': lbl,
                    })
                break

    layers.sort(
        key=lambda la: next(
            (i for i, n in enumerate(_LAYER_ORDER) if n in la['name'].upper()), 99
        )
    )
    return layers


def generate_section_svg(config: dict) -> str:
    """Génère un SVG de profil en travers type depuis la config parsée."""
    W, H = 900, 360
    SURFACE_Y  = 90     # y de la surface de la chaussée
    H_SCALE    = 500    # px par mètre (axe vertical)
    PX_PER_M_H = 30     # px par mètre (axe horizontal)
    CX         = W // 2

    # Extraire les paramètres
    axe_sec  = config.get('sections', {}).get('AXE', [])
    asg_sec  = config.get('sections', {}).get('ASG', [])
    asd_sec  = config.get('sections', {}).get('ASD', [])

    first_axe = axe_sec[0]['params'] if axe_sec else {}
    first_asg = asg_sec[0]['params'] if asg_sec else {}
    first_asd = asd_sec[0]['params'] if asd_sec else {}

    largeur       = _find_param(first_axe, 'LARGEUR', default=7.0)
    devers_pct    = _find_param(first_axe, 'DEVERS',  default=2.5)
    half_road_px  = (largeur / 2) * PX_PER_M_H

    layers = _extract_layers(first_axe)
    if not layers:
        layers = [
            {'name': 'BB',  'thickness_m': 0.06, 'color': '#2c2c2c', 'label': 'BB 6cm'},
            {'name': 'GB4', 'thickness_m': 0.12, 'color': '#4a4a4a', 'label': 'GB4 12cm'},
            {'name': 'GNT', 'thickness_m': 0.30, 'color': '#8a8a8a', 'label': 'GNT 30cm'},
            {'name': 'FF',  'thickness_m': 0.35, 'color': '#5b4ca8', 'label': 'FF 35cm'},
        ]

    asg_dist = (_find_param(first_asg, 'DIST_AXE')
                or _find_param(first_asg, 'DIST_AXE_M')
                or _find_param(first_asg, 'DIST'))
    asg_dim  = _find_param(first_asg, 'DIM', default=0.5) or 0.5

    asd_dist = (_find_param(first_asd, 'DIST_AXE')
                or _find_param(first_asd, 'DIST_AXE_M')
                or _find_param(first_asd, 'DIST'))
    asd_dim  = _find_param(first_asd, 'DIM', default=0.5) or 0.5

    # Points TER (on déduplique par label)
    ter_pts = config.get('ter_points', [])
    ter_seen: dict = {}
    for pt in ter_pts:
        lbl = pt.get('label')
        if lbl and lbl not in ter_seen:
            ter_seen[lbl] = pt
    ter_list = list(ter_seen.values())[:10]

    # ── SVG ───────────────────────────────────────────────────────────────────
    el: list[str] = []
    el.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'style="width:100%;height:auto;font-family:Inter,sans-serif;">'
    )

    # Fond
    el.append(f'<rect width="{W}" height="{H}" fill="#0d1f38"/>')

    # Plateforme
    road_left  = CX - half_road_px
    road_right = CX + half_road_px
    plat_ext   = max(half_road_px + 30,
                     (asg_dist or 0) * PX_PER_M_H + 40,
                     (asd_dist or 0) * PX_PER_M_H + 40)
    plat_ext   = min(plat_ext, CX - 10)
    el.append(
        f'<rect x="{CX - plat_ext:.0f}" y="{SURFACE_Y - 8}" '
        f'width="{plat_ext * 2:.0f}" height="8" fill="{_SURFACE_COLOR}" rx="2"/>'
    )

    # Couches de chaussée
    cur_y = SURFACE_Y
    for layer in layers:
        lh = max(8, layer['thickness_m'] * H_SCALE)
        el.append(
            f'<rect x="{road_left:.0f}" y="{cur_y:.0f}" '
            f'width="{road_right - road_left:.0f}" height="{lh:.0f}" '
            f'fill="{layer["color"]}" stroke="#0d1f38" stroke-width="0.5"/>'
        )
        if lh >= 12:
            ty = cur_y + lh / 2 + 4
            el.append(
                f'<text x="{CX}" y="{ty:.0f}" text-anchor="middle" '
                f'font-size="9" fill="#e2e8f0" font-weight="600" opacity="0.9">'
                f'{layer["label"]}</text>'
            )
        cur_y += lh

    road_bottom_y = cur_y

    # Axe (pointillés)
    el.append(
        f'<line x1="{CX}" y1="{SURFACE_Y - 20}" x2="{CX}" y2="{road_bottom_y + 12}" '
        f'stroke="#00ffff" stroke-width="1" stroke-dasharray="4,3" opacity="0.7"/>'
    )
    el.append(
        f'<text x="{CX}" y="{SURFACE_Y - 25}" text-anchor="middle" '
        f'font-size="8" fill="#00ffff" font-weight="700">▲ AXE</text>'
    )

    # Canaux
    def _canal(canal_x, dim_m, color, label, side):
        cw  = max(18, dim_m * PX_PER_M_H * 0.8)
        ch  = max(20, dim_m * H_SCALE * 0.7)
        x1  = canal_x - cw if side == 'g' else canal_x
        x2  = canal_x      if side == 'g' else canal_x + cw
        y1  = SURFACE_Y
        y2  = y1 + ch
        pts = f'{x1:.0f},{y1:.0f} {x2:.0f},{y1:.0f} {x2:.0f},{y2:.0f} {x1:.0f},{y2:.0f}'
        el.append(
            f'<polygon points="{pts}" fill="{color}" fill-opacity="0.22" '
            f'stroke="{color}" stroke-width="1.5"/>'
        )
        el.append(
            f'<line x1="{x1:.0f}" y1="{y2:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
            f'stroke="{color}" stroke-width="2.5"/>'
        )
        mx = (x1 + x2) / 2
        el.append(
            f'<text x="{mx:.0f}" y="{y1 + ch / 2 + 4:.0f}" text-anchor="middle" '
            f'font-size="8" fill="{color}" font-weight="700">{label}</text>'
        )

    if asg_dist:
        _canal(CX - asg_dist * PX_PER_M_H, asg_dim, _CANAL_COLOR_G, 'Can. G', 'g')
    if asd_dist:
        _canal(CX + asd_dist * PX_PER_M_H, asd_dim, _CANAL_COLOR_D, 'Can. D', 'd')

    # Points TER
    for pt in ter_list:
        dist = pt.get('dist_axe_m')
        if dist is None:
            continue
        cote = str(pt.get('cote', '')).upper()
        sign = -1 if 'G' in cote else 1
        px_x = CX + sign * dist * PX_PER_M_H
        el.append(
            f'<circle cx="{px_x:.0f}" cy="{SURFACE_Y:.0f}" r="5" '
            f'fill="{_TER_DOT_COLOR}" stroke="#fff" stroke-width="1.2"/>'
        )
        lbl = (pt.get('label') or '').replace('_', ' ')[:10]
        el.append(
            f'<text x="{px_x:.0f}" y="{SURFACE_Y - 9:.0f}" text-anchor="middle" '
            f'font-size="7" fill="{_TER_DOT_COLOR}">{lbl}</text>'
        )

    # Cote largeur
    arr_y = road_bottom_y + 18
    el.append(
        f'<line x1="{road_left:.0f}" y1="{arr_y:.0f}" x2="{road_right:.0f}" y2="{arr_y:.0f}" '
        f'stroke="#475569" stroke-width="1"/>'
    )
    el.append(
        f'<text x="{CX}" y="{arr_y + 13:.0f}" text-anchor="middle" '
        f'font-size="9" fill="#94a3b8">Largeur chaussée : {largeur:.1f} m'
        f' — Dévers : {devers_pct:.1f} %</text>'
    )

    # Légendes gauche/droite
    el.append(
        f'<text x="{road_left - 6:.0f}" y="{SURFACE_Y + 14:.0f}" '
        f'text-anchor="end" font-size="9" fill="#64748b" font-weight="600">GAUCHE</text>'
    )
    el.append(
        f'<text x="{road_right + 6:.0f}" y="{SURFACE_Y + 14:.0f}" '
        f'font-size="9" fill="#64748b" font-weight="600">DROITE</text>'
    )

    # Titre
    el.append(
        f'<text x="{W // 2}" y="18" text-anchor="middle" font-size="10" '
        f'fill="#00ffff" font-weight="700" letter-spacing="1.5">PROFIL EN TRAVERS TYPE</text>'
    )

    el.append('</svg>')
    return '\n'.join(el)


def build_projet_context(config: dict) -> dict:
    """Construit le contexte pour le template de visualisation."""
    profil   = config.get('profil_long', [])
    sections = config.get('sections', {})
    ter_pts  = config.get('ter_points', [])

    # Chart.js
    chart_labels = [p['pk'] for p in profil]
    chart_z      = [p.get('z_axe') for p in profil]

    # Longueur totale
    longueur_m = None
    if len(profil) >= 2:
        longueur_m = profil[-1]['pk_m'] - profil[0]['pk_m']

    axe_sec = sections.get('AXE', [])
    asg_sec = sections.get('ASG', [])
    asd_sec = sections.get('ASD', [])

    # Couches de la première section AXE
    layers = _extract_layers(axe_sec[0]['params'] if axe_sec else {})

    # Labels TER uniques
    ter_labels = sorted({pt.get('label', '') for pt in ter_pts if pt.get('label')})

    return {
        'gen':             config.get('gen', {}),
        'profil_long':     profil,
        'chart_labels':    json.dumps(chart_labels),
        'chart_z':         json.dumps(chart_z),
        'longueur_m':      longueur_m,
        'n_pk':            len(profil),
        'n_axe_sections':  len(axe_sec),
        'n_asg_sections':  len(asg_sec),
        'n_asd_sections':  len(asd_sec),
        'n_ter_points':    len(ter_labels),
        'has_asg':         bool(asg_sec),
        'has_asd':         bool(asd_sec),
        'has_profil':      bool(profil),
        'ter_labels':      ter_labels,
        'layers':          layers,
        'axe_sections':    axe_sec,
        'asg_sections':    asg_sec,
        'asd_sections':    asd_sec,
        'section_svg':     generate_section_svg(config),
        'errors':          config.get('errors', []),
        'available_elements': config.get('available_elements', {}),
    }
