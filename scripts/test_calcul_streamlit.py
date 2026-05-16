"""
scripts/test_calcul_streamlit.py
Test interactif du moteur de calcul RECEPTA — workflow 5 étapes.

Usage :
    streamlit run scripts/test_calcul_streamlit.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

from app.services.excel_service import parse_modele_config, active_section, _pk_to_m
from app.services.calculation_service import (
    _layer_offset, _interp_radier,
    _ass_elements_from_params, _pk_in_range,
    _LAYER_ORDER,
)
from app.services.excel_service import interp_z

st.set_page_config(page_title="RECEPTA — Test calcul", page_icon="🔭", layout="wide")
st.title("🔭 RECEPTA — Test du moteur de calcul")
st.caption("Workflow : Mode → Côté → Couche/Élément → PK → Côtes théoriques")

# ─────────────────────────────────────────────────────────────────────────────
# Chargement fichier
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_EXCEL = ROOT / "data" / "clients" / "01_projet_Dani.xlsx"

with st.sidebar:
    st.header("📂 Fichier Excel")
    uploaded = st.file_uploader("Importer un .xlsx", type=["xlsx"])
    use_default = st.checkbox(
        f"Fichier par défaut (`{DEFAULT_EXCEL.name}`)",
        value=not bool(uploaded),
        disabled=bool(uploaded),
    )

@st.cache_data(show_spinner="Parsing Excel…")
def load_bytes(data: bytes) -> dict:
    return parse_modele_config(data)

@st.cache_data(show_spinner="Parsing Excel…")
def load_path(path: str) -> dict:
    return parse_modele_config(path)

config = None
if uploaded:
    config = load_bytes(uploaded.read())
    label_src = uploaded.name
elif use_default:
    if DEFAULT_EXCEL.exists():
        config = load_path(str(DEFAULT_EXCEL))
        label_src = DEFAULT_EXCEL.name
    else:
        st.error(f"Fichier introuvable : `{DEFAULT_EXCEL}`")
        st.stop()
else:
    st.info("Importez un fichier ou cochez « Fichier par défaut ».")
    st.stop()

if config["errors"]:
    with st.expander("⚠️ Avertissements parsing", expanded=False):
        for e in config["errors"]:
            st.warning(e)

# Résumé parsing
has_axe   = bool(config.get("profil_long"))
has_ter   = bool(config.get("ter_points"))
has_ass_g = bool(config.get("ass_long_g"))
has_ass_d = bool(config.get("ass_long_d"))
has_ass   = bool(config.get("ass_long"))
has_asg   = bool(config.get("sections", {}).get("ASG"))
has_asd   = bool(config.get("sections", {}).get("ASD"))
all_pks   = [r["pk"] for r in config.get("profil_long", [])]

st.success(
    f"**{label_src}** — {len(all_pks)} PK | "
    f"AXE {'✓' if has_axe else '✗'}  "
    f"TER {'✓' if has_ter else '✗'}  "
    f"AG_Z_fil_eau {'✓' if has_ass_g else '✗'}  "
    f"AD_Z_fil_eau {'✓' if has_ass_d else '✗'}  "
    f"ASG {'✓' if has_asg else '✗'}  "
    f"ASD {'✓' if has_asd else '✗'}"
)

if not all_pks:
    st.error("Aucun PK dans le profil en long.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 1 — Mode
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.header("Étape 1 — Mode")

modes_dispo = []
if has_axe and has_ter:
    modes_dispo.append("Terrassement")
if (has_ass_g or has_ass_d or has_ass) and (has_asg or has_asd):
    modes_dispo.append("Assainissement")

if not modes_dispo:
    st.error("Aucun mode calculable dans ce fichier.")
    st.stop()

mode = st.radio("Mode de réception", modes_dispo, horizontal=True)

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 2 — Côté
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.header("Étape 2 — Côté")

if mode == "Terrassement":
    sides_ter = set()
    for pt in config.get("ter_points", []):
        sides_ter.add("G" if "G" in str(pt.get("cote", "")).upper() else "D")
    cotes_options = []
    if "G" in sides_ter: cotes_options.append("Gauche (G)")
    if "D" in sides_ter: cotes_options.append("Droit (D)")
    if len(sides_ter) == 2: cotes_options.append("G + D")
else:
    cotes_options = []
    if has_asg and (has_ass_g or has_ass): cotes_options.append("Gauche (G)")
    if has_asd and (has_ass_d or has_ass): cotes_options.append("Droit (D)")
    if len(cotes_options) == 2:            cotes_options.append("G + D")

if not cotes_options:
    st.warning("Aucun côté disponible.")
    st.stop()

cote_choix = st.radio("Côté", cotes_options, horizontal=True)
filtre_G = "G" in cote_choix
filtre_D = "D" in cote_choix

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 3 — Couche / Élément
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.header("Étape 3 — Couche / Élément à réceptionner")

if mode == "Terrassement":
    axe_secs = config.get("sections", {}).get("AXE", [])
    axe_p    = axe_secs[0]["params"] if axe_secs else {}

    couches_axe = [("surface", "Surface axe (ligne rouge)")]
    for layer in _LAYER_ORDER:
        e = _layer_offset(axe_p, layer)
        if e is not None:
            couches_axe.append((f"fond_{layer}", f"Fond {layer}  (offset {e:+.4f} m)"))

    if not couches_axe:
        st.warning("Aucune couche AXE.")
        st.stop()

    couche_idx = st.selectbox(
        "Couche à réceptionner",
        range(len(couches_axe)),
        format_func=lambda i: couches_axe[i][1],
    )
    couche_key, couche_label = couches_axe[couche_idx]
    st.info(f"Réception : **{couche_label}** — points TER côté **{cote_choix}**")

else:  # Assainissement
    # Construire liste éléments par côté
    elts_g, elts_d = [], []
    for grp, side, pfx, lst in (("ASG","G","AG",elts_g), ("ASD","D","AD",elts_d)):
        secs = config.get("sections", {}).get(grp, [])
        if not secs:
            continue
        p = secs[0]["params"]
        for elt in _ass_elements_from_params(p, pfx):
            lbl = f"{elt['elt_name'].replace('_',' ').capitalize()} ({side})  offset {elt['offset']:+.4f} m"
            lst.append((grp, pfx, elt["elt_name"], elt["offset"], side, lbl))

    elts_dispo = (elts_g if filtre_G else []) + (elts_d if filtre_D else [])
    if not elts_dispo:
        st.warning("Aucun élément disponible.")
        st.stop()

    elt_idx = st.selectbox(
        "Élément à réceptionner",
        range(len(elts_dispo)),
        format_func=lambda i: elts_dispo[i][5],
    )
    grp_sel, pfx_sel, elt_name_sel, offset_sel, side_sel, elt_label = elts_dispo[elt_idx]
    st.info(f"z = z_fil_eau_{side_sel} (AG/AD_Z_fil_eau) + offset {offset_sel:+.4f} m")

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 4 — Choix des PK
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.header("Étape 4 — Choix des PK")

saisie_mode = st.radio("Mode de saisie", ["PK unique", "Plage"], horizontal=True)

if saisie_mode == "PK unique":
    pk_sel = st.selectbox("PK", all_pks)
    pks_selected = [pk_sel]
else:
    c1, c2 = st.columns(2)
    with c1:
        pk_debut = st.selectbox("PK début", all_pks, index=0)
    with c2:
        pk_fin = st.selectbox("PK fin", all_pks, index=len(all_pks) - 1)
    d_m = _pk_to_m(pk_debut) or 0
    f_m = _pk_to_m(pk_fin)   or 0
    if d_m >= f_m:
        st.error("PK début ≥ PK fin.")
        st.stop()
    pks_selected = [p for p in all_pks if d_m <= (_pk_to_m(p) or 0) <= f_m]
    st.info(f"{len(pks_selected)} PK sélectionnés.")

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 5 — Calcul et affichage
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.header("Étape 5 — Côtes théoriques")

def _calc_ter(pks, couche_key, couche_label, axe_p, config, filtre_G, filtre_D):
    """Calcule les côtes TER pour chaque PK, retourne rows G et rows D."""
    rows_g, rows_d = [], []
    for pk_str in pks:
        pk_m  = _pk_to_m(pk_str)
        if pk_m is None: continue
        z_axe = interp_z(config.get("profil_long", []), pk_m)
        if z_axe is None: continue

        axe_p_pk = (active_section(config.get("sections", {}).get("AXE", []), pk_m) or {}).get("params", {})
        if couche_key == "surface":
            z_ref = round(z_axe, 4)
        else:
            layer = couche_key.replace("fond_", "")
            e     = _layer_offset(axe_p_pk, layer)
            z_ref = round(z_axe + e, 4) if e is not None else None
        if z_ref is None: continue

        for pt in config.get("ter_points", []):
            if not _pk_in_range(pk_m, pt): continue
            side  = "G" if "G" in str(pt.get("cote", "")).upper() else "D"
            if side == "G" and not filtre_G: continue
            if side == "D" and not filtre_D: continue
            lbl   = pt.get("label", "")
            dist  = pt.get("dist_axe_m")
            pente = pt.get("pente_pct") or 0.0
            if dist is None: continue
            z_ter = round(z_ref - abs(pente) / 100.0 * dist, 4)
            row = {
                "PK": pk_str,
                "Point": f"{lbl}",
                "Dist. axe (m)": dist,
                "z_ref couche (m NGF)": z_ref,
                "Côte théorique (m NGF)": z_ter,
            }
            (rows_g if side == "G" else rows_d).append(row)
    return rows_g, rows_d


def _calc_ass(pks, grp_sel, elt_name_sel, offset_sel, side_sel, config):
    """Calcule les côtes assainissement pour chaque PK."""
    rows = []
    for pk_str in pks:
        pk_m = _pk_to_m(pk_str)
        if pk_m is None: continue
        z_fe = _interp_radier(config, pk_m, side=side_sel)
        if z_fe is None: continue
        z_elt = round(z_fe + offset_sel, 4)
        rows.append({
            "PK": pk_str,
            "Élément": f"{elt_name_sel.replace('_',' ').capitalize()} ({side_sel})",
            "z_fil_eau (m NGF)": round(z_fe, 4),
            f"Offset (m)": offset_sel,
            "Côte théorique (m NGF)": z_elt,
        })
    return rows


if mode == "Terrassement":
    axe_p = (config.get("sections", {}).get("AXE", [{}]) or [{}])[0].get("params", {})
    rows_g, rows_d = _calc_ter(pks_selected, couche_key, couche_label, axe_p, config, filtre_G, filtre_D)

    if filtre_G:
        st.subheader("📋 Côté Gauche")
        if rows_g:
            df_g = pd.DataFrame(rows_g)
            st.dataframe(df_g, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun point TER côté G pour ces PK.")

    if filtre_D:
        st.subheader("📋 Côté Droit")
        if rows_d:
            df_d = pd.DataFrame(rows_d)
            st.dataframe(df_d, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun point TER côté D pour ces PK.")

    # Export CSV
    all_rows = rows_g + rows_d
    if all_rows and len(pks_selected) > 1:
        df_all = pd.DataFrame(all_rows)
        st.download_button(
            "⬇️ Télécharger CSV",
            data=df_all.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            file_name=f"ter_{couche_key}_{pks_selected[0].replace('+','p')}.csv",
            mime="text/csv",
        )

else:  # Assainissement
    # Un seul élément sélectionné — afficher selon le côté
    rows = _calc_ass(pks_selected, grp_sel, elt_name_sel, offset_sel, side_sel, config)

    side_label = "Gauche" if side_sel == "G" else "Droit"
    st.subheader(f"📋 Côté {side_label}")
    if rows:
        df_ass = pd.DataFrame(rows)
        st.dataframe(df_ass, use_container_width=True, hide_index=True)
        if len(pks_selected) > 1:
            st.download_button(
                "⬇️ Télécharger CSV",
                data=df_ass.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                file_name=f"ass_{grp_sel}_{elt_name_sel}_{pks_selected[0].replace('+','p')}.csv",
                mime="text/csv",
            )
    else:
        st.warning("Aucune côte calculée — vérifiez que AG_Z_fil_eau / AD_Z_fil_eau contient les PK sélectionnés.")

# ─────────────────────────────────────────────────────────────────────────────
# Debug — structure config
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("🔍 Structure config parsée (debug)", expanded=False):
    st.subheader(f"profil_long — {len(config.get('profil_long',[]))} PK")
    st.dataframe(pd.DataFrame(config["profil_long"][:5]), use_container_width=True, hide_index=True)

    for key, label in [("ass_long_g", "AG_Z_fil_eau (Gauche)"),
                        ("ass_long_d", "AD_Z_fil_eau (Droit)"),
                        ("ass_long",   "ASS_LONG (générique)")]:
        data = config.get(key, [])
        st.subheader(f"{label} — {len(data)} entrées")
        if data:
            df_tmp = pd.DataFrame(data)
            st.dataframe(df_tmp.head(8), use_container_width=True, hide_index=True)
            st.caption(f"Colonnes : {list(df_tmp.columns)}")
        else:
            st.warning(f"Vide — onglet {'AG_*' if 'g' in key else ('AD_*' if 'd' in key else 'ASS_*')} non trouvé ou non parsé.")

    for grp in ["AXE", "ASG", "ASD"]:
        secs = config.get("sections", {}).get(grp, [])
        if secs:
            st.subheader(f"sections {grp} — {len(secs)} section(s)")
            rows_s = [{"pk_debut_m": s["pk_debut_m"], "pk_fin_m": s.get("pk_fin_m"),
                       **s["params"]} for s in secs]
            st.dataframe(pd.DataFrame(rows_s), use_container_width=True, hide_index=True)

    if config.get("ter_points"):
        st.subheader(f"ter_points — {len(config['ter_points'])} point(s)")
        st.dataframe(pd.DataFrame(config["ter_points"]), use_container_width=True, hide_index=True)
