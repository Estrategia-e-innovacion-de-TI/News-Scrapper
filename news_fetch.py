import os
import sys
import json
import csv
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Tuple, Optional

import yaml
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_datetime64tz_dtype
from newsapi import NewsApiClient


# ---------- Utilidades ----------
def previous_monday(d: datetime) -> date:
    """lunes anterior a la fecha actual (sin incluir el lunes de esta semana)."""
    return (d - timedelta(days=d.weekday() + 7)).date()

def load_config(path: str = "config.yml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_folder(p: str) -> None:
    Path(p).mkdir(parents=True, exist_ok=True)

def iso(dt) -> str:
    if isinstance(dt, (datetime, date)):
        return dt.isoformat()
    return str(dt)


# ---------- Lectura de emisores desde Excel ----------
def load_emisores_excel(path: str = "data/clientes.xlsx") -> List[Tuple[str, Optional[str]]]:
    """
    Lee el Excel con columnas:
      - Emisor (obligatoria): término de búsqueda
      - Idioma (opcional): 'es', 'en', etc.

    Retorna lista de tuplas: [(emisor, idioma_preferido|None), ...]
    """
    p = Path(path)
    if not p.exists():
        print(f"ADVERTENCIA: No existe {path}. No se cargarán emisores externos.", file=sys.stderr)
        return []
    df = pd.read_excel(p, engine="openpyxl")
    if "Emisor" not in df.columns:
        print("ERROR: El Excel debe contener una columna 'Emisor'.", file=sys.stderr)
        sys.exit(1)

    emisores: List[Tuple[str, Optional[str]]] = []
    for _, row in df.iterrows():
        emisor = str(row.get("Emisor") or "").strip()
        idioma = str(row.get("Idioma") or "").strip().lower() or None
        if not emisor:
            continue
        emisores.append((emisor, idioma))
    return emisores


# ---------- Normalización de fechas para IO ----------
def prepare_frames_for_io(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Devuelve (df_excel, df_text):
      - df_excel: datetimes naive (sin tz) para Excel
      - df_text:  datetimes como strings ISO 'YYYY-MM-DDTHH:MM:SS' para CSV/JSONL
    """
    df_excel = df.copy()

    # 1) Quitar tz en columnas datetime tz-aware (Excel no soporta tz)
    for col in df_excel.columns:
        if is_datetime64tz_dtype(df_excel[col]):
            # si tiene tz, convertir a UTC y quitar tz
            df_excel[col] = df_excel[col].dt.tz_convert("UTC").dt.tz_localize(None)
        elif is_datetime64_any_dtype(df_excel[col]):
            # asegurar dtype datetime (naive)
            df_excel[col] = pd.to_datetime(df_excel[col], errors="coerce")

    # 2) Para CSV/JSONL: formatear datetimes como texto ISO
    df_text = df_excel.copy()
    for col in df_text.columns:
        if is_datetime64_any_dtype(df_text[col]):
            df_text[col] = df_text[col].dt.strftime("%Y-%m-%dT%H:%M:%S")

    return df_excel, df_text


# ---------- Core ----------
def fetch_news(config: dict, api_key: str) -> pd.DataFrame:
    newsapi = NewsApiClient(api_key=api_key)

    # Fechas
    if config.get("since_previous_monday", True):
        from_date = previous_monday(datetime.today())
    else:
        from_date = (datetime.today() - timedelta(days=7)).date()

    to_date = date.today()

    # Parámetros globales
    domains = config.get("domains", [])
    domains_csv = ",".join(domains) if domains else None
    languages_default: List[str] = config.get("languages", ["es", "en"])
    page_size = int(config.get("limits", {}).get("per_query_page_size", 50))
    if page_size > 100:
        page_size = 100  # límite NewsAPI

    rows = []

    # Cargar emisores (cada emisor es un término de búsqueda)
    emisores = load_emisores_excel("data/clientes.xlsx")
    if not emisores:
        print("ADVERTENCIA: No hay emisores en data/clientes.xlsx; no se hará ninguna búsqueda.", file=sys.stderr)

    for emisor, lang_pref in emisores:
        langs_to_use = [lang_pref] if lang_pref else languages_default
        for lang in langs_to_use:
            try:
                resp = newsapi.get_everything(
                    q=emisor,
                    language=lang,
                    from_param=from_date,
                    to=to_date,
                    domains=domains_csv,
                    sort_by="publishedAt",
                    page=1,
                    page_size=page_size
                )
            except Exception as e:
                print(f"ERROR al consultar NewsAPI para '{emisor}' ({lang}): {e}", file=sys.stderr)
                continue

            articles = (resp or {}).get("articles", [])
            for item in articles:
                title = item.get("title")
                desc = item.get("description")
                if not title or desc is None:
                    continue
                rows.append({
                    "emisor": emisor,                 # 👈 guardamos el emisor origen
                    "termino_consulta": emisor,       # alias por compatibilidad
                    "idioma": lang,
                    "fuente": (item.get("source") or {}).get("name"),
                    "titulo": title,
                    "autor": item.get("author"),
                    "descripcion": desc,
                    "url": item.get("url"),
                    "url_imagen": item.get("urlToImage"),
                    "contenido": item.get("content"),
                    "fecha_publicacion": item.get("publishedAt"),
                    "fecha_consulta_desde": iso(from_date),
                    "fecha_consulta_hasta": iso(to_date),
                })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Normalización + dedupe
    df["titulo"] = df["titulo"].astype(str).str.strip()
    df["url"] = df["url"].astype(str).str.strip()

    # Parseo de fechas (incluye publishedAt con 'Z', que es UTC tz-aware)
        # Parseo de fechas (incluye publishedAt con 'Z', que es UTC tz-aware)
    if "fecha_publicacion" in df.columns:
        # Parsear con utc=True para homogenizar; luego quitamos tz antes de Excel
        df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"], errors="coerce", utc=True)

    df = df.drop_duplicates(subset=["titulo", "url"], keep="first")

    # Ordenar por fecha_publicacion si existe
    if "fecha_publicacion" in df.columns:
        df = df.sort_values(by="fecha_publicacion", ascending=False, na_position="last")

    return df


def save_outputs(df: pd.DataFrame, config: dict) -> None:
    # --- preparar dataframes para IO ---
    from pandas.api.types import is_datetime64_any_dtype, is_datetime64tz_dtype

    def prepare_frames_for_io(df_in: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        df_excel = df_in.copy()
        for col in df_excel.columns:
            if is_datetime64tz_dtype(df_excel[col]):
                df_excel[col] = df_excel[col].dt.tz_convert("UTC").dt.tz_localize(None)
            elif is_datetime64_any_dtype(df_excel[col]):
                df_excel[col] = pd.to_datetime(df_excel[col], errors="coerce")
        df_text = df_excel.copy()
        for col in df_text.columns:
            if is_datetime64_any_dtype(df_text[col]):
                df_text[col] = df_text[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
        return df_excel, df_text

    df_excel, df_text = prepare_frames_for_io(df)

    out_cfg = config.get("output", {})
    folder = out_cfg.get("folder", "data")
    csv_name = out_cfg.get("csv_name", "news.csv")
    jsonl_name = out_cfg.get("jsonl_name", "news.jsonl")
    excel_cfg = out_cfg.get("excel", {})
    excel_folder = excel_cfg.get("folder", "data/noticias")
    filename_template = excel_cfg.get("filename_template", "{fecha_consulta_hasta}.xlsx")

    Path(folder).mkdir(parents=True, exist_ok=True)
    Path(excel_folder).mkdir(parents=True, exist_ok=True)

    csv_path = Path(folder) / csv_name
    jsonl_path = Path(folder) / jsonl_name

    # CSV consolidado
    if not df_text.empty:
        if csv_path.exists():
            old = pd.read_csv(csv_path)
            all_df = pd.concat([old, df_text], ignore_index=True)
            all_df = all_df.drop_duplicates(subset=["titulo", "url"], keep="first")
            all_df.to_csv(csv_path, index=False, quoting=csv.QUOTE_MINIMAL)
        else:
            df_text.to_csv(csv_path, index=False, quoting=csv.QUOTE_MINIMAL)

        # JSONL append-only
        with open(jsonl_path, "a", encoding="utf-8") as f:
            for _, row in df_text.iterrows():
                f.write(json.dumps(row.dropna().to_dict(), ensure_ascii=False) + "\n")

    # Excel por corrida
    run_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    fecha_consulta_hasta = None
    if "fecha_consulta_hasta" in df_excel.columns and not df_excel.empty:
        try:
            fecha_consulta_hasta = pd.to_datetime(
                df_excel["fecha_consulta_hasta"].iloc[0], errors="coerce"
            ).date().isoformat()
        except Exception:
            fecha_consulta_hasta = str(df_excel["fecha_consulta_hasta"].iloc[0])

    fecha_consulta_desde = None
    if "fecha_consulta_desde" in df_excel.columns and not df_excel.empty:
        try:
            fecha_consulta_desde = pd.to_datetime(
                df_excel["fecha_consulta_desde"].iloc[0], errors="coerce"
            ).date().isoformat()
        except Exception:
            fecha_consulta_desde = str(df_excel["fecha_consulta_desde"].iloc[0])

    fname = filename_template.format(
        fecha_consulta_hasta=fecha_consulta_hasta or run_timestamp[:10],
        fecha_consulta_desde=fecha_consulta_desde or "",
        run_timestamp=run_timestamp
    )
    excel_path = Path(excel_folder) / fname

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_excel.to_excel(writer, sheet_name="news", index=False)

        # hoja extra para garantizar cambio (opcional pero útil en pruebas)
        meta = pd.DataFrame([{
            "generated_at_utc": run_timestamp,
            "rows": int(len(df_excel))
        }])
        meta.to_excel(writer, sheet_name="run_info", index=False)

    print(f"✅ Guardado Excel por corrida en {excel_path}")
    print(f"📰 Registros nuevos en esta corrida: {len(df_excel)}")


def main():
    cfg = load_config()
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        print("ERROR: define la variable de entorno NEWSAPI_KEY (GitHub Secret o local).", file=sys.stderr)
        sys.exit(1)

    df = fetch_news(cfg, api_key)   # 👈 AQUÍ se llama a fetch_news
    if df.empty:
        print("No se obtuvieron noticias nuevas.")
        return
    save_outputs(df, cfg)           # 👈 y se guardan salidas


if __name__ == "__main__":
    main()

