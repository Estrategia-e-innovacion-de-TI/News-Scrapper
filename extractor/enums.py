"""Extensible enums and YAML-based category loading for News Radar.

Enums define the base sets; `load_categories()` reads from YAML so
categories can be extended without code changes.
"""
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Literal

import yaml


# ---------------------------------------------------------------------------
# Static enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    H = "H"
    M = "M"
    L = "L"


class ARAS_Categories(str, Enum):
    """Categorías ARAS — extensibles vía aras_categories.yaml."""
    LAVADO_ACTIVOS = "lavado_activos"
    FINANCIAMIENTO_TERRORISMO = "financiamiento_terrorismo"
    FRAUDE = "fraude"
    CORRUPCION = "corrupcion"
    SANCIONES = "sanciones"
    PEP = "pep"
    AMBIENTAL = "ambiental"
    SOCIAL = "social"
    LICENCIAS_PERMISOS_AMBIENTALES = "licencias_permisos_ambientales"
    PROCESOS_SANCIONATORIOS_AMBIENTALES = "procesos_sancionatorios_ambientales"
    CONFLICTOS_COMUNIDADES = "conflictos_comunidades"
    PROTESTAS_BLOQUEOS = "protestas_bloqueos"
    TRABAJO_INFANTIL_FORZOSO = "trabajo_infantil_forzoso"
    TRASLAPE_AREAS_PROTEGIDAS = "traslape_areas_protegidas"
    IMPACTOS_AMBIENTALES_SOCIALES = "impactos_ambientales_sociales"
    DESPLAZAMIENTO_INVOLUNTARIO = "desplazamiento_involuntario"
    ACCIDENTES_LABORALES = "accidentes_laborales"
    CONTAMINACION = "contaminacion"
    DEFORESTACION = "deforestacion"
    DERRAME = "derrame"
    INCENDIO = "incendio"
    HALLAZGO_ARQUEOLOGICO = "hallazgo_arqueologico"
    COMUNIDAD_INDIGENA = "comunidad_indigena"
    OTRO = "otro"


class Risk_Types(str, Enum):
    """Tipos de riesgo emergente — extensibles vía risk_types.yaml."""
    CIBERNETICO = "cibernetico"
    OPERACIONAL = "operacional"
    FRAUDE = "fraude"
    ASG = "asg"
    IA = "ia"
    TALENTO = "talento"
    REGULATORIO = "regulatorio"
    AMBIENTAL = "ambiental"
    SOCIAL = "social"
    LABORAL = "laboral"
    OTRO = "otro"


class Materialized_Events(str, Enum):
    """Eventos materializados detectables en noticias."""
    MULTA = "multa"
    PERDIDA = "perdida"
    OUTAGE = "outage"
    BREACH = "breach"
    NEAR_MISS = "near_miss"
    SANCION = "sancion"
    DEMANDA = "demanda"
    SUSPENSION_ACTIVIDADES = "suspension_actividades"
    SUSPENSION_LICENCIA = "suspension_licencia"
    FATALIDAD = "fatalidad"
    BLOQUEO = "bloqueo"
    DERRAME = "derrame"
    INCENDIO = "incendio"
    INUNDACION = "inundacion"
    DENUNCIA = "denuncia"
    CONFLICTO_LABORAL = "conflicto_laboral"


class MaturityStage(str, Enum):
    """Gartner-inspired hype cycle stages."""
    INNOVATION_TRIGGER = "innovation_trigger"
    PEAK_OF_INFLATED_EXPECTATIONS = "peak_of_inflated_expectations"
    TROUGH_OF_DISILLUSIONMENT = "trough_of_disillusionment"
    SLOPE_OF_ENLIGHTENMENT = "slope_of_enlightenment"
    PLATEAU_OF_PRODUCTIVITY = "plateau_of_productivity"


# ---------------------------------------------------------------------------
# Base sets derived from enums (used as defaults when YAML is absent)
# ---------------------------------------------------------------------------

_ARAS_BASE: set[str] = {m.value for m in ARAS_Categories}
_RISK_BASE: set[str] = {m.value for m in Risk_Types}


# ---------------------------------------------------------------------------
# Dynamic YAML loading
# ---------------------------------------------------------------------------

def _resolve_yaml_path(yaml_path: str | Path) -> Path:
    """Resolve a YAML path relative to the package root (news_radar_mvp/)."""
    p = Path(yaml_path)
    if p.is_absolute():
        return p
    # Relative paths are resolved from the package root (parent of extractor/)
    package_root = Path(__file__).resolve().parent.parent
    return package_root / p


def load_categories(yaml_path: str | Path) -> set[str]:
    """Load a set of category strings from a YAML file.

    Expected YAML structure::

        categories:
          - lavado_activos
          - financiamiento_terrorismo
          ...

    Returns the set of strings listed under the ``categories`` key.
    Raises ``FileNotFoundError`` if the file does not exist.
    """
    resolved = _resolve_yaml_path(yaml_path)
    with open(resolved, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "categories" not in data:
        raise ValueError(f"YAML file {resolved} must contain a 'categories' key")
    cats = data["categories"]
    if not isinstance(cats, list):
        raise ValueError(f"'categories' in {resolved} must be a list")
    return set(cats)


def get_valid_categories(
    query_type: str,
    *,
    aras_yaml: str | Path = "aras_categories.yaml",
    risk_yaml: str | Path = "risk_types.yaml",
) -> set[str]:
    """Return the valid category set for a given *query_type*.

    Tries to load from the corresponding YAML file first; falls back to the
    base enum values if the file is not found.

    Parameters
    ----------
    query_type:
        ``"aras"`` or ``"riesgos"``.
    aras_yaml:
        Path to the ARAS categories YAML (relative to package root).
    risk_yaml:
        Path to the risk types YAML (relative to package root).
    """
    if query_type == "aras":
        try:
            return load_categories(aras_yaml)
        except FileNotFoundError:
            return _ARAS_BASE
    elif query_type == "riesgos":
        try:
            return load_categories(risk_yaml)
        except FileNotFoundError:
            return _RISK_BASE
    else:
        raise ValueError(f"Unknown query_type: {query_type!r}. Expected 'aras' or 'riesgos'.")
