#!/usr/bin/env python
"""SPCA-CI v0.2 — point d'entrée du moteur d'audit.

  python moteur/spca_audit.py --input dossiers/<ID>/audit_request.json [--referentiel referentiel] [--sortie rapports/<ID>]
"""
import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from spca.pipeline import audit, load_config, persist  # noqa: E402


def main(argv=None):
    W = ICI.parent
    ap = argparse.ArgumentParser(description="SPCA-CI — audit de bulletin de paie (Côte d'Ivoire)")
    ap.add_argument("--input", required=True, help="audit_request.json (schéma Registre des inputs §29)")
    ap.add_argument("--referentiel", default=str(W / "referentiel"))
    ap.add_argument("--sortie", help="dossier de sortie (défaut : rapports/<audit_id>)")
    ap.add_argument("--journal", default=str(W / "journal" / "journal_audit.jsonl"), help="'' pour désactiver")
    ap.add_argument("--escalades", default=str(W / "escalades"), help="'' pour désactiver")
    ap.add_argument("--config", default=str(ICI / "config_spca.json"))
    a = ap.parse_args(argv)
    req = json.loads(Path(a.input).read_text(encoding="utf-8"))
    res = audit(req, Path(a.referentiel), load_config(Path(a.config)))
    out = Path(a.sortie) if a.sortie else W / "rapports" / res["audit_id"]
    persist(res, out, Path(a.journal) if a.journal else None, Path(a.escalades) if a.escalades else None)
    print(json.dumps({"audit_id": res["audit_id"], "status": res["status"], "confidence": res["confidence"],
                      "risk": res["risk_summary"], "escalations": len(res["human_escalations"]), "sortie": str(out)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
