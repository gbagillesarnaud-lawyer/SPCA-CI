"""Évaluateur d'expressions sécurisé pour les formules du Rules Registry.

Seuls sont autorisés : nombres, chaînes, booléens, variables du contexte, opérateurs
arithmétiques / de comparaison / logiques, expression conditionnelle `a if c else b`,
et les fonctions explicitement fournies. Aucune fonction Python arbitraire.
"""
from __future__ import annotations

import ast
from decimal import Decimal


class MissingInput(Exception):
    """Une donnée nécessaire au calcul est absente (→ NON CONTRÔLABLE — INFORMATION MANQUANTE)."""

    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class RuleError(Exception):
    """Formule invalide ou non évaluable."""


_BIN = {
    ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b, ast.FloorDiv: lambda a, b: a // b, ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}
_CMP = {
    ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
}


def _num(v):
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    return v


def evaluate(expr: str, variables: dict, functions: dict):
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise RuleError(f"Syntaxe invalide : {expr} ({e})") from e

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return _num(n.value)
        if isinstance(n, ast.Name):
            if n.id in ("True", "False", "None"):
                return {"True": True, "False": False, "None": None}[n.id]
            if n.id not in variables or variables[n.id] is None:
                raise MissingInput(n.id)
            return _num(variables[n.id])
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            if isinstance(n.op, ast.USub):
                return -v
            if isinstance(n.op, ast.UAdd):
                return v
            if isinstance(n.op, ast.Not):
                return not v
        if isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                r = True
                for x in n.values:
                    r = ev(x)
                    if not r:
                        return r
                return r
            r = False
            for x in n.values:
                r = ev(x)
                if r:
                    return r
            return r
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for op, comp in zip(n.ops, n.comparators):
                right = ev(comp)
                if type(op) not in _CMP or not _CMP[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, (ast.List, ast.Tuple)):
            return [ev(x) for x in n.elts]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in functions and not n.keywords:
            return _num(functions[n.func.id](*[ev(a) for a in n.args]))
        raise RuleError(f"Élément non autorisé dans la formule : {ast.dump(n)[:80]}")

    return ev(tree)
