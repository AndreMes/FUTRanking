"""Metadados editoriais complementares para clubes sem liga nacional brasileira."""
from __future__ import annotations


# A base nacional identifica automaticamente os clubes brasileiros. Para clubes
# estrangeiros, a fonte atual não fornece país no evento; este mapa é extensível.
COUNTRY_OVERRIDES = {
    "Estudiantes de La Plata": "Argentina",
}

