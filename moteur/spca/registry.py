"""Chargement du référentiel : règles calculables, paramètres versionnés et tables."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

REQUIRED_RULE_KEYS = ("rule_id", "version", "name", "control_id", "order", "expected", "status")


def _dates(obj):
    f = obj.get("effective_from")
    t = obj.get("effective_to")
    return (dt.date.fromisoformat(f) if f else None, dt.date.fromisoformat(t) if t else None)


def in_force(obj, date: dt.date) -> bool | None:
    """True / False, ou None si la date d'effet n'est pas renseignée."""
    f, t = _dates(obj)
    if f is None:
        return None
    return f <= date and (t is None or date <= t)


class Registry:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.rules: list[dict] = []
        self.params: list[dict] = []
        self.tables: dict[str, dict] = {}
        self.rejected: list[str] = []
        self._load()

    def _read(self, f: Path):
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            self.rejected.append(f"{f.name} : JSON invalide ({e})")
            return None

    def _load(self):
        base = self.root / "PAYROLL_RULES" if (self.root / "PAYROLL_RULES").exists() else self.root
        if not base.exists():
            self.rejected.append(f"Référentiel absent : {base}")
            return
        for f in sorted(base.rglob("*.json")):
            if f.name.startswith("_"):
                continue
            data = self._read(f)
            if data is None:
                continue
            part = f.relative_to(base).parts[0]
            items = data if isinstance(data, list) else [data]
            if part == "parameters":
                for p in items:
                    if p.get("status") != "validee":
                        self.rejected.append(f"Paramètre {p.get('param_id')} : statut '{p.get('status')}' (non validé)")
                    else:
                        self.params.append(p)
            elif part == "tables":
                if data.get("status") != "validee":
                    self.rejected.append(f"Table {data.get('table_id', f.stem)} : statut '{data.get('status')}' (non validée)")
                else:
                    self.tables[data.get("table_id", f.stem)] = data
            else:
                for r in items:
                    miss = [k for k in REQUIRED_RULE_KEYS if k not in r]
                    if miss:
                        self.rejected.append(f"{r.get('rule_id', f.name)} : champs manquants {miss}")
                    elif r["status"] != "validee":
                        self.rejected.append(f"{r['rule_id']} v{r['version']} : statut '{r['status']}' (non validée)")
                    else:
                        r["_file"] = str(f)
                        self.rules.append(r)

    # -- paramètres
    def param(self, pid: str, date: dt.date):
        """Retourne (param, conflit:bool) ou (None, False)."""
        cands = [p for p in self.params if p.get("param_id") == pid and in_force(p, date)]
        if not cands:
            return None, False
        cands.sort(key=lambda p: p["effective_from"], reverse=True)
        conflit = len(cands) > 1 and cands[0]["effective_from"] == cands[1]["effective_from"] and cands[0]["value"] != cands[1]["value"]
        return cands[0], conflit

    def params_at(self, date: dt.date) -> tuple[dict, dict, list]:
        vals, meta, conflicts = {}, {}, []
        for pid in sorted({p["param_id"] for p in self.params}):
            p, c = self.param(pid, date)
            if p:
                vals[pid] = p["value"]
                meta[pid] = p
                if c:
                    conflicts.append(pid)
        return vals, meta, conflicts

    def version(self) -> str:
        v = self.tables.get("_ruleset", {}).get("version")
        return v or "CI-PAYROLL-" + str(len(self.rules)) + "R-" + str(len(self.params)) + "P"
