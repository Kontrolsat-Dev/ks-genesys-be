# app/domains/mapping/engine.py
# Ingest engine for mapping and transforming data rows based on a profile configuration.

from __future__ import annotations

import re
from typing import Any

from app.core.normalize import clean_text, to_decimal_str, to_int

JSON = dict[str, Any]


def supported_ops_for_api() -> list[dict[str, Any]]:
    return [
        {"op": "eq", "label": "=", "arity": 2, "input": "any"},
        {"op": "ne", "label": "≠", "arity": 2, "input": "any"},
        {"op": "gt", "label": ">", "arity": 2, "input": "number"},
        {"op": "gte", "label": "≥", "arity": 2, "input": "number"},
        {"op": "lt", "label": "<", "arity": 2, "input": "number"},
        {"op": "lte", "label": "≤", "arity": 2, "input": "number"},
        {"op": "regex", "label": "Regex", "arity": 2, "input": "regex"},
        {"op": "contains", "label": "Contém", "arity": 2, "input": "text"},
        {"op": "startswith", "label": "Começa por", "arity": 2, "input": "text"},
        {"op": "endswith", "label": "Termina em", "arity": 2, "input": "text"},
        {"op": "in", "label": "Em lista", "arity": 2, "input": "array"},
        {"op": "empty_any_of", "label": "Vazio (qualquer)", "arity": 1, "input": "array"},
    ]


def _is_ref(x: Any) -> bool:
    return isinstance(x, str) and x.startswith("$") and len(x) > 1


def _empty(x: Any) -> bool:
    return (
        x is None
        or (isinstance(x, str) and x.strip() == "")
        or (isinstance(x, list | dict) and len(x) == 0)  # UP038
    )


def _to_float(x: Any) -> float | None:
    s = clean_text(x)
    if s is None:
        return None
    s = to_decimal_str(s)
    try:
        return float(s) if s is not None else None
    except Exception:
        return None


# cond ops
def _op_eq(a, b):
    fa, fb = _to_float(a), _to_float(b)
    return (
        (fa == fb)
        if (fa is not None and fb is not None)
        else ((clean_text(a) or "") == (clean_text(b) or ""))
    )


def _op_ne(a, b):
    return not _op_eq(a, b)


def _op_gt(a, b):
    fa, fb = _to_float(a), _to_float(b)
    return fa is not None and fb is not None and fa > fb


def _op_gte(a, b):
    fa, fb = _to_float(a), _to_float(b)
    return fa is not None and fb is not None and fa >= fb


def _op_lt(a, b):
    fa, fb = _to_float(a), _to_float(b)
    return fa is not None and fb is not None and fa < fb


def _op_lte(a, b):
    fa, fb = _to_float(a), _to_float(b)
    return fa is not None and fb is not None and fa <= fb


def _op_contains(a, b):
    return str(b) in str(a)


def _op_startswith(a, b):
    return str(a).startswith(str(b))


def _op_endswith(a, b):
    return str(a).endswith(str(b))


def _op_regex(a, pat):
    try:
        return re.search(str(pat), str(a)) is not None
    except re.error:
        return False


def _op_in(a, coll):
    if isinstance(coll, list):
        return str(a) in [str(x) for x in coll]
    return str(a) in [s.strip() for s in str(coll).split(",")]


_OPS = {
    "eq": _op_eq,
    "ne": _op_ne,
    "gt": _op_gt,
    "gte": _op_gte,
    "lt": _op_lt,
    "lte": _op_lte,
    "contains": _op_contains,
    "startswith": _op_startswith,
    "endswith": _op_endswith,
    "regex": _op_regex,
    "in": _op_in,
}


class IngestEngine:
    def __init__(self, profile: JSON | None):
        self.profile = profile or {}
        raw_fields = self.profile.get("fields") or {}
        if isinstance(raw_fields, list):
            tmp: JSON = {}
            for row in raw_fields:
                if isinstance(row, dict) and row.get("target"):
                    cfg = {k: v for k, v in row.items() if k != "target"}
                    tmp[row["target"]] = cfg
            self.fields_cfg = tmp
        else:
            self.fields_cfg = dict(raw_fields)

        self._field_sources: dict[str, str] = {}
        for k, v in self.fields_cfg.items():
            if isinstance(v, dict):
                src = v.get("source") or v.get("from")
                if src:
                    self._field_sources[k] = src

        req = [
            k
            for k, v in self.fields_cfg.items()
            if isinstance(v, dict) and v.get("required") is True
        ]
        if isinstance(self.profile.get("required"), list):
            for k in self.profile["required"]:
                if k not in req:
                    req.append(k)
        self.required: list[str] = req

        self.rules: list[JSON] = list(self.profile.get("rules") or [])
        self.drop_if: list[JSON] = list(self.profile.get("drop_if") or [])
        self.row_selector: JSON | None = self.profile.get("row_selector")
        self.defaults: JSON = dict(self.profile.get("defaults") or {})

    def _resolve_token(self, token: Any, mapped: JSON, raw: JSON) -> Any:
        if not _is_ref(token):
            return token
        name = str(token)[1:]
        if name in mapped:
            return mapped.get(name)
        if name in raw:
            return raw.get(name)
        src = self._field_sources.get(name)
        return raw.get(src) if src else None

    def _normalize_set_key(self, k: str) -> str:
        return k[1:] if isinstance(k, str) and k.startswith("$") else k

    def _eval_condition(self, cond: JSON, mapped: JSON, raw: JSON) -> bool:
        if not isinstance(cond, dict) or not cond:
            return False
        if "and" in cond:
            items = cond["and"] if isinstance(cond["and"], list) else [cond["and"]]
            return all(self._eval_condition(c, mapped, raw) for c in items)
        if "or" in cond:
            items = cond["or"] if isinstance(cond["or"], list) else [cond["or"]]
            return any(self._eval_condition(c, mapped, raw) for c in items)
        ((op, args),) = cond.items()
        op = str(op).lower()
        if op == "empty_any_of":
            items = args if isinstance(args, list) else [args]
            return any(_empty(self._resolve_token(i, mapped, raw)) for i in items)
        fn = _OPS.get(op)
        if not fn or not isinstance(args, list) or len(args) != 2:
            return False
        a = self._resolve_token(args[0], mapped, raw)
        b = self._resolve_token(args[1], mapped, raw)
        return fn(a, b)

    def _apply_defaults(self, mapped: JSON) -> None:
        for k, v in self.defaults.items():
            if _empty(mapped.get(k)):
                mapped[k] = v

    def _apply_field_transforms(self, target: str, cfg: JSON, mapped: JSON, raw: JSON) -> None:
        if not isinstance(cfg, dict):
            return
        if target not in mapped and not (cfg.get("source") or cfg.get("from")):
            return
        val = mapped.get(target)
        if cfg.get("trim") and isinstance(val, str):
            val = val.strip()
        if cfg.get("lowercase") and isinstance(val, str):
            val = val.lower()
        if cfg.get("uppercase") and isinstance(val, str):
            val = val.upper()
        to_num = cfg.get("to_number")
        if isinstance(to_num, dict) and isinstance(val, str | int | float):  # UP038
            dec = to_num.get("decimal") or "."
            thou = to_num.get("thousands") or ""
            s = str(val)
            if thou:
                s = s.replace(thou, "")
            if dec != ".":
                s = s.replace(dec, ".")
            val = s
        vmap = cfg.get("value_map")
        if isinstance(vmap, dict):
            key = "" if val is None else str(val)
            if key in vmap:
                val = vmap[key]
        derive = cfg.get("derive")
        if isinstance(derive, dict) and derive.get("when"):
            conds = derive.get("when") or []
            if not isinstance(conds, list):
                conds = [conds]
            ok = all(self._eval_condition(c, mapped, raw) for c in conds)
            chosen = derive.get("then") if ok else derive.get("else", val)
            val = self._resolve_token(chosen, mapped, raw)
        mapped[target] = val

    def _apply_global_rules(self, mapped: JSON, raw: JSON) -> None:
        for rule in self.rules:
            conds = rule.get("when") or []
            if not isinstance(conds, list):
                conds = [conds]
            if not all(self._eval_condition(c, mapped, raw) for c in conds):
                continue
            set_ops = rule.get("set") or {}
            for k, v in set_ops.items():
                key = self._normalize_set_key(k)
                mapped[key] = self._resolve_token(v, mapped, raw)

    def map_row(self, raw: JSON) -> tuple[JSON | None, str | None]:
        mapped: JSON = {}
        for target, cfg in self.fields_cfg.items():
            if isinstance(cfg, dict):
                src = cfg.get("source") or cfg.get("from")
                if src:
                    mapped[target] = raw.get(src)
        self._apply_defaults(mapped)
        for target, cfg in self.fields_cfg.items():
            if isinstance(cfg, dict):
                self._apply_field_transforms(target, cfg, mapped, raw)
        self._apply_global_rules(mapped, raw)
        if self.row_selector and not self._eval_condition(self.row_selector, mapped, raw):
            return None, "row_filtered"
        for cond in self.drop_if:
            if self._eval_condition(cond, mapped, raw):
                return None, "dropped"
        for req in self.required:
            if _empty(mapped.get(req)):
                return None, f"required_missing:{req}"
        if mapped.get("gtin") is not None:
            mapped["gtin"] = (clean_text(mapped["gtin"]) or "").strip()
        if mapped.get("price") is not None:
            mapped["price"] = (to_decimal_str(mapped["price"]) or "").strip()
        if mapped.get("stock") is not None:
            s = to_int(mapped["stock"])
            mapped["stock"] = max(0, s) if s is not None else 0
        return mapped, None
