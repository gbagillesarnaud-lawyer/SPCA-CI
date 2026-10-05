"""Constantes et structures communes SPCA-CI."""
from __future__ import annotations

import datetime as dt
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

AGENT_VERSION = "0.2.0"

# Messages standardisés (spec §15)
MSG_INFO = "NON CONTRÔLABLE — INFORMATION MANQUANTE"
MSG_SOURCE = "SOURCE NON VÉRIFIÉE"
MSG_REGLE = "RÈGLE APPLICABLE NON DÉTERMINÉE"
MSG_NQ = "ÉCART NON QUANTIFIABLE EN L'ÉTAT"
MSG_FRAUDE = "INDICE NÉCESSITANT INVESTIGATION"
ESCALADE_TXT = "ESCALADE REQUISE — VALIDATION PAR JURISTE / EXPERT FISCAL / EXPERT SOCIAL AVANT CORRECTION."

# Statuts de contrôle
CONFORME, NON_CONFORME, NA = "CONFORME", "NON_CONFORME", "NON_APPLICABLE"
RESULTATS_CONCLUSIFS = {CONFORME, NON_CONFORME}

# Statuts d'input (registre des inputs §31)
IN_STATUTS = {"VERIFIED", "UNVERIFIED", "MISSING", "CONFLICTING", "NOT_APPLICABLE", "CALCULATED", "HUMAN_VALIDATED"}

FAMILLES = {
    "C01": "Salaire minimum", "C02": "Primes et indemnités", "C03": "Temps de travail",
    "C04": "Congés et absences", "C05": "CNPS", "C06": "CMU", "C07": "Fiscalité",
    "C08": "Retenues", "C09": "Net à payer", "C10": "Mentions du bulletin", "C11": "Rupture du contrat",
    "C12": "Prestations sociales CNPS",
}
PRIORITE = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}


def D(x) -> Decimal | None:
    if x is None or x == "" or isinstance(x, bool):
        return None
    try:
        return Decimal(str(x))
    except Exception:  # noqa: BLE001
        return None


def arrondir(v, mode: str = "unite") -> Decimal:
    v = Decimal(v)
    if mode == "aucun":
        return v
    pas = {"unite": Decimal("1"), "dizaine": Decimal("10"), "centime": Decimal("0.01")}.get(mode, Decimal("1"))
    return (v / pas).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * pas


def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "oui" if v else "non"
    try:
        v = Decimal(v)
    except Exception:  # noqa: BLE001
        return str(v)
    if v == v.to_integral():
        return f"{int(v):,}".replace(",", " ")
    return f"{v:,.2f}".replace(",", " ")


def norm_txt(s) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return "".join(c for c in s.upper() if c.isalnum() or c == " ").strip()


def periode_bornes(periode: str) -> tuple[dt.date, dt.date]:
    a, m = (int(x) for x in periode.split("-")[:2])
    debut = dt.date(a, m, 1)
    fin = (dt.date(a + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
    return debut, fin


@dataclass
class Field:
    """Donnée à cinq dimensions : VALUE / SOURCE / DATE / CONFIDENCE / STATUS."""
    name: str
    value: object = None
    source: str | None = None
    page: int | None = None
    zone: str | None = None
    confidence: float | None = None
    error_code: str | None = None
    status: str = "MISSING"

    @property
    def present(self) -> bool:
        return self.value is not None and self.status not in ("MISSING", "NOT_APPLICABLE")

    def ref(self) -> str:
        loc = self.source or "source non renseignée"
        if self.page:
            loc += f" p.{self.page}"
        if self.zone:
            loc += f" {self.zone}"
        return loc

    def as_dict(self) -> dict:
        return {"field": self.name, "value": self.value, "source": self.source, "page": self.page,
                "zone": self.zone, "confidence": self.confidence, "status": self.status}


@dataclass
class Control:
    control_id: str          # C01..C12
    order: int               # ordre XXXII (1..22)
    control_name: str
    status: str              # CONFORME / NON_CONFORME / NON_APPLICABLE / message standardisé
    rule_id: str | None = None
    rule_version: int | None = None
    observed_value: object = None
    expected_value: object = None
    difference: object = None
    legal_reference: str = "—"
    finding: str = ""
    recommendation: str = "—"
    trace: list = field(default_factory=list)
    reserves: list = field(default_factory=list)
    evidence_fields: list = field(default_factory=list)
    base_severity: str | None = None
    severity: str | None = None
    impact_type: str | None = None   # rappel_salarie / cnps / cmu / fiscal / patronal / trop_percu
    favorable_to: str | None = None  # salarie / employeur
    risk_variables: dict = field(default_factory=dict)
    human_flags: list = field(default_factory=list)
    confidence: float | None = None
    error_code: str | None = None
