# profile_utils.py
import json
import pandas as pd
from copy import deepcopy
from pathlib import Path

# ---------- helpers ----------
def load_json(path):
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(obj, path):
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def df_from_records(records):
    return pd.DataFrame.from_records(records)

# ---------- geometry logic ----------
def Z_surf(x, params):
    """
    Fonction piecewise : surface en fonction de x (demi-profil)
    params doit contenir : Z0, s, s_acc, x_ch
    """
    Z0 = params.get("Z0", 0.0)
    s = params.get("s", 0.025)
    s_acc = params.get("s_acc", 0.032)
    x_ch = params.get("x_ch", 6.5)
    if x <= x_ch:
        return Z0 - s * x
    else:
        return (Z0 - s * x_ch) - s_acc * (x - x_ch)

def recalc_layers(params, layers, objects=None):
    """
    Recalcule tous les polygones (4 points) pour chaque layer en demi-profil.
    - params: dict (Z0, s, s_acc, x_ch, x_qn, w_qn, x_acc_end ...)
    - layers: list of {"name":..., "t":...} (top->bottom order)
    - objects: list of other objects (ex: caniveau) (optional); if given, they must follow a dict format similar to layers with extra attributes
    Returns: list of records each with layer + P1_x,P1_z,...,P4_x,P4_z,thickness
    """
    recs = []
    x_in = params.get("X0", 0.0)   # usually 0
    x_out = params.get("x_ch", 6.5)
    # compute top at x_in and x_out
    top_in = Z_surf(x_in, params)
    top_out = Z_surf(x_out, params)

    current_top_in = top_in
    current_top_out = top_out

    for lyr in layers:
        t = float(lyr.get("t", 0.0))
        top_in = current_top_in
        top_out = current_top_out
        bot_in = top_in - t
        bot_out = top_out - t
        recs.append({
            "layer": lyr.get("name", ""),
            "P1_x": round(x_in, 6), "P1_z": round(top_in, 6),
            "P2_x": round(x_out, 6), "P2_z": round(top_out, 6),
            "P3_x": round(x_out, 6), "P3_z": round(bot_out, 6),
            "P4_x": round(x_in, 6), "P4_z": round(bot_in, 6),
            "thickness": t
        })
        # update for next
        current_top_in = bot_in
        current_top_out = bot_out

    # handle additional objects (quart-niveau, caniveau...) if provided
    if objects:
        for obj in objects:
            kind = obj.get("type")
            if kind == "quart_niveau":
                t_qn = float(obj.get("t", 0.2))
                x_qn = float(obj.get("x", params.get("x_qn", 7.0)))
                w_qn = float(obj.get("w", obj.get("w_qn", 0.5)))
                left = x_qn - w_qn/2
                right = x_qn + w_qn/2
                top_left = Z_surf(left, params)
                top_right = Z_surf(right, params)
                recs.append({
                    "layer": obj.get("name","quart_niveau"),
                    "P1_x": round(left,6), "P1_z": round(top_left,6),
                    "P2_x": round(right,6), "P2_z": round(top_right,6),
                    "P3_x": round(right,6), "P3_z": round(top_right - t_qn,6),
                    "P4_x": round(left,6), "P4_z": round(top_left - t_qn,6),
                    "thickness": t_qn
                })
            elif kind == "caniveau":
                w = float(obj.get("w", 0.4))
                d = float(obj.get("d", 0.15))
                center_x = float(obj.get("x", params.get("x_ch", x_out)))
                left = center_x - w/2
                right = center_x + w/2
                top_left = Z_surf(left, params)
                top_right = Z_surf(right, params)
                recs.append({
                    "layer": obj.get("name","caniveau"),
                    "P1_x": round(left,6), "P1_z": round(top_left,6),
                    "P2_x": round(right,6), "P2_z": round(top_right,6),
                    "P3_x": round(right,6), "P3_z": round(top_right - d,6),
                    "P4_x": round(left,6), "P4_z": round(top_left - d,6),
                    "thickness": d
                })
            # add other object types similarly
    return recs

# ---------- IO helpers ----------
def write_outputs(recs, params, out_prefix="profile_out"):
    """
    Ecrit CSV, XLSX et JSON dans le répertoire courant. Retourne les chemins écrits.
    """
    df = df_from_records(recs)
    csv_path = f"{out_prefix}.csv"
    xlsx_path = f"{out_prefix}.xlsx"
    json_path = f"{out_prefix}.json"
    df.to_csv(csv_path, index=False)
    with pd.ExcelWriter(xlsx_path) as writer:
        df.to_excel(writer, sheet_name="layers", index=False)
        pd.DataFrame([params]).to_excel(writer, sheet_name="params", index=False)
    save_json({"params": params, "layers": recs}, json_path)
    return {"csv": csv_path, "xlsx": xlsx_path, "json": json_path}

# ---------- high-level function ----------
def update_profile_from_file(profile_json_path, new_Z0=None, new_X0=None):
    """
    - charge profile_json_path (which contient params + layers + objects)
    - modifie Z0 si demandé, X0 si demandé
    - recalcule et ecrit les outputs avec prefix contenant new Z0
    """
    data = load_json(profile_json_path)
    params = deepcopy(data.get("params", {}))
    layers = deepcopy(data.get("layers_def", data.get("layers", [])))  # accept either key
    objects = deepcopy(data.get("objects", data.get("extras", None)))

    if new_Z0 is not None:
        params["Z0"] = float(new_Z0)
    if new_X0 is not None:
        params["X0"] = float(new_X0)

    recs = recalc_layers(params, layers, objects=objects)
    prefix = f"profile_Z0_{params.get('Z0'):.3f}"
    out = write_outputs(recs, params, out_prefix=prefix)
    return {"params": params, "records": recs, "outputs": out}
