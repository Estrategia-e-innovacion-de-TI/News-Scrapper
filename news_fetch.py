import os
import sys
import json
import csv
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Tuple, Optional
from zoneinfo import ZoneInfo  # stdlib 3.9+


import yaml
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_datetime64tz_dtype
from newsapi import NewsApiClient
from urllib.parse import urlparse


def domain_from_url(u: str) -> str:
    try:
        netloc = urlparse(u).netloc.lower()
        # quitar puerto si viene (ej. "example.com:8080")
        return netloc.split(":")[0]
    except Exception:
        return ""



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

def start_of_week(dt: datetime, week_start: str) -> datetime:
    # week_start: 'mon' (0) o 'sun' (6-> start on Sunday)
    ws = 0 if week_start.lower().startswith("mon") else 6
    # normalizamos: si domingo = 6, calculamos offset especial
    if ws == 0:
        offset = dt.weekday()          # 0..6 (0 = lunes)
        return (dt - timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # domingo como inicio: convertir weekday() (0..6, 0=lun) a índice con dom=0
        idx_sun0 = (dt.weekday() + 1) % 7  # dom=0, lun=1, ... sáb=6
        return (dt - timedelta(days=idx_sun0)).replace(hour=0, minute=0, second=0, microsecond=0)

def start_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)

def get_date_window(config: dict) -> tuple[date, date]:
    """
    Devuelve (from_date: date, to_date: date) según config['date_window'] y 'timezone'.
    Si no hay 'date_window', usa 'desde el lunes anterior' hasta hoy (comportamiento legacy).
    """
    tzname = (config.get("timezone") or "UTC").strip()
    try:
        tz = ZoneInfo(tzname)
    except Exception:
        tz = ZoneInfo("UTC")

    now = datetime.now(tz)
    today = now.date()

    dw = config.get("date_window") or {}
    mode = (dw.get("mode") or "").lower().strip()

    if mode == "relative":
        unit = (dw.get("unit") or "days").lower()
        amount = int(dw.get("amount") or 7)
        include_today = bool(dw.get("include_today", True))

        if unit == "days":
            to_d = today if include_today else (today - timedelta(days=1))
            from_d = to_d - timedelta(days=amount - 1)
        elif unit == "weeks":
            to_d = today if include_today else (today - timedelta(days=1))
            from_d = to_d - timedelta(weeks=amount) + timedelta(days=1)
        elif unit == "months":
            # aproximación simple: 30 días por mes
            to_d = today if include_today else (today - timedelta(days=1))
            from_d = to_d - timedelta(days=30 * amount) + timedelta(days=1)
        else:
            to_d = today
            from_d = to_d - timedelta(days=6)
        return (from_d, to_d)

    elif mode == "calendar_week":
        which = (dw.get("which") or "previous").lower()
        week_start = (dw.get("week_start") or "mon").lower()

        # inicio de la semana actual en tz
        sow = start_of_week(now, week_start=week_start)
        if which == "previous":
            # ventana: semana completa anterior
            end_prev = sow - timedelta(seconds=1)
            start_prev = start_of_week(sow - timedelta(days=1), week_start=week_start)
            return (start_prev.date(), end_prev.date())
        else:
            # semana actual (inicio hasta hoy)
            return (sow.date(), today)

    elif mode == "calendar_month":
        which = (dw.get("which") or "previous").lower()
        som = start_of_month(now)
        if which == "previous":
            # mes anterior completo
            prev_end = som - timedelta(seconds=1)
            prev_start = start_of_month(som - timedelta(days=1))
            return (prev_start.date(), prev_end.date())
        else:
            # mes en curso: 1er día hasta hoy
            return (som.date(), today)

    elif mode == "fixed":
        try:
            f = datetime.fromisoformat(dw["from"]).date()
            t = datetime.fromisoformat(dw["to"]).date()
            return (f, t)
        except Exception:
            # fallback si algo viene mal formateado
            return (today - timedelta(days=6), today)

    # ---- Legacy / por defecto: desde el lunes anterior ----
    from_legacy = (now - timedelta(days=now.weekday() + 7)).date()
    return (from_legacy, today)


# ---------- Lectura de emisores desde Excel ----------
def load_emisores_excel(path: str = "data/clientes.xlsx") -> List[Tuple[str, Optional[str], List[str]]]:
    """
    Lee el Excel con columnas en la hoja principal:
      - Emisor (obligatoria): término de búsqueda
      - Idioma (opcional): 'es', 'en', etc.
      - ExcluirDominios (opcional): lista separada por ';'

    Retorna lista de tuplas:
      [(emisor, idioma_preferido|None, exclude_domains:list[str]), ...]
    """
    p = Path(path)
    if not p.exists():
        print(f"ADVERTENCIA: No existe {path}. No se cargarán emisores externos.", file=sys.stderr)
        return []
    # lee la primera hoja por defecto
    df = pd.read_excel(p, engine="openpyxl")
    if "Emisor" not in df.columns:
        print("ERROR: El Excel debe contener una columna 'Emisor'.", file=sys.stderr)
        sys.exit(1)

    emisores: List[Tuple[str, Optional[str], List[str]]] = []
    for _, row in df.iterrows():
        emisor = str(row.get("Emisor") or "").strip()
        idioma = str(row.get("Idioma") or "").strip().lower() or None
        excl_raw = str(row.get("ExcluirDominios") or "").strip()
        exclude_domains = [d.strip().lower() for d in excl_raw.split(";") if d.strip()] if excl_raw else []
        if not emisor:
            continue
        emisores.append((emisor, idioma, exclude_domains))
    return emisores

def load_global_excludes_excel(path: str = "data/clientes.xlsx", sheet_name: str = "Excludes") -> List[str]:
    """
    Lee la hoja 'Excludes' con una columna 'Domain' (dominios a excluir globalmente).
    Si no existe la hoja, retorna lista vacía.
    """
    p = Path(path)
    if not p.exists():
        return []
    try:
        df = pd.read_excel(p, sheet_name=sheet_name, engine="openpyxl")
    except Exception:
        return []
    if "Domain" not in df.columns:
        return []
    domains = []
    for _, row in df.iterrows():
        d = str(row.get("Domain") or "").strip().lower()
        if d:
            domains.append(d)
    return domains


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

        # Fechas (usando configuraciones avanzadas)
    from_date, to_date = get_date_window(config)


    # Parámetros globales
    domains = config.get("domains", [])
    domains_csv = ",".join(domains) if domains else None
    languages_default: List[str] = config.get("languages", ["es", "en"])
    page_size = int(config.get("limits", {}).get("per_query_page_size", 50))
    if page_size > 100:
        page_size = 100  # límite NewsAPI

    rows = []

    # Cargar emisores (cada emisor es un término de búsqueda)
    emisores = load_emisores_excel("data/clientes.xlsx")          # -> (emisor, idioma, exclude_domains)
    global_excludes = load_global_excludes_excel("data/clientes.xlsx")  # si la tienes
    global_excludes_set = set(global_excludes)

    if not emisores:
        print("ADVERTENCIA: No hay emisores en data/clientes.xlsx; no se hará ninguna búsqueda.", file=sys.stderr)

    for emisor, lang_pref, exclude_domains_emisor in emisores:
        # set combinado de exclusiones (global + por emisor)
        excludes = {d.lower() for d in exclude_domains_emisor} | global_excludes_set

        # helper para filtrar por dominio (subdominios incluidos)
        def is_excluded(url: str) -> bool:
            dom = domain_from_url(url)
            if not dom:
                return False
            return any(dom == ex or dom.endswith("." + ex) for ex in excludes)

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
                url = item.get("url")
                if not title or desc is None or not url:
                    continue

                # aplicar EXCLUSIONES
                if excludes and is_excluded(url):
                    continue

                rows.append({
                    "emisor": emisor,
                    "termino_consulta": emisor,
                    "idioma": lang,
                    "fuente": (item.get("source") or {}).get("name"),
                    "titulo": title,
                    "autor": item.get("author"),
                    "descripcion": desc,
                    "url": url,
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

