"""Intel OpenVINO local intent router for EdgeRemit.

Two paths, same Intent enum:

* DEMO_MODE (default) — fast keyword/heuristic router that mirrors live
  intents and logs ``DEMO OpenVINO path``.
* LIVE_OPENVINO — builds a tiny bag-of-words → linear → SoftMax model with
  OpenVINO opset, compiles it for CPU via OpenVINO Runtime, and runs
  inference on-device (edge compute story for Intel Online).

Judges can force either path with env flags; no cloud call is required.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from edge_remit.config import DEMO_MODE, LIVE_OPENVINO, PROJECT_ROOT

logger = logging.getLogger("edge_remit.openvino_router")

# Fixed vocabulary for the LIVE OpenVINO linear classifier (hackathon-sized).
VOCAB: list[str] = [
    "rate", "naira", "dollar", "usd", "exchange", "fx", "parallel", "official",
    "fee", "wise", "remitly", "bank", "cost", "compare", "cheapest", "charge",
    "wait", "send", "now", "timing", "should", "urgent", "rent", "today",
    "checklist", "steps", "nuban", "account", "receive", "need", "how",
    "hello", "hi", "help", "transfer", "remittance", "lagos", "mum", "family",
]

INTENT_LABELS: list[str] = [
    "rate_check",
    "fee_compare",
    "send_now_advice",
    "checklist",
    "general",
]


class Intent(str, Enum):
    RATE_CHECK = "rate_check"
    FEE_COMPARE = "fee_compare"
    SEND_NOW_ADVICE = "send_now_advice"
    CHECKLIST = "checklist"
    GENERAL = "general"


@dataclass
class RouteResult:
    intent: Intent
    confidence: float
    path: str  # "DEMO OpenVINO path" | "LIVE OpenVINO path"
    scores: dict[str, float]
    detail: str = ""


# ---------------------------------------------------------------------------
# DEMO path — keyword / heuristic (mirrors Intent enum)
# ---------------------------------------------------------------------------

RATE_KW = (
    "rate", "naira", "dollar", "fx", "usd", "exchange", "parallel",
    "black market", "i&e", "ie window", "how much is the",
)
FEE_KW = (
    "fee", "wise", "remitly", "western union", "moneygram", "cost",
    "compare", "charge", "spread", "cheapest", "vs", "versus",
)
TIME_KW = (
    "wait", "send now", "timing", "when should", "should i send",
    "should we", "hold off", "delay", "better rate", "urgent", "rent due",
)
CHECK_KW = (
    "step", "checklist", "how do i", "what do i need", "what does she need",
    "what does he need", "nuban", "account number", "to receive", "next steps",
)
GREET_RE = re.compile(
    r"^\s*(hi|hello|hey|yo|good (morning|afternoon|evening))\b", re.I
)


def _demo_route(text: str) -> RouteResult:
    """Keyword router used when DEMO_MODE is on (or OpenVINO unavailable)."""
    t = text.lower().strip()
    scores = {label: 0.0 for label in INTENT_LABELS}

    if GREET_RE.match(t) and len(t.split()) < 8:
        scores["general"] = 0.95
        intent = Intent.GENERAL
    else:
        hits = {
            "rate_check": sum(1 for k in RATE_KW if k in t),
            "fee_compare": sum(1 for k in FEE_KW if k in t),
            "send_now_advice": sum(1 for k in TIME_KW if k in t),
            "checklist": sum(1 for k in CHECK_KW if k in t),
            "general": 0,
        }
        # Soft priors for remittance-ish questions with no keyword hit.
        if sum(hits.values()) == 0:
            if any(w in t for w in ("send", "transfer", "remit", "money", "₦", "$")):
                hits["fee_compare"] = 1
                hits["rate_check"] = 1
            else:
                hits["general"] = 1

        total = float(sum(hits.values()) or 1)
        for k, v in hits.items():
            scores[k] = v / total

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        intent = Intent(best)

    conf = float(scores[intent.value])
    path = "DEMO OpenVINO path"
    logger.info("%s → intent=%s conf=%.2f", path, intent.value, conf)
    print(f"[router] {path} → {intent.value} ({conf:.2f})")
    return RouteResult(
        intent=intent,
        confidence=conf,
        path=path,
        scores=scores,
        detail="keyword/heuristic mirror of OpenVINO Intent enum",
    )


# ---------------------------------------------------------------------------
# LIVE path — OpenVINO Runtime on a tiny BoW linear classifier
# ---------------------------------------------------------------------------

def _bow_vector(text: str) -> np.ndarray:
    tokens = re.findall(r"[a-z0-9&]+", text.lower())
    vec = np.zeros(len(VOCAB), dtype=np.float32)
    for tok in tokens:
        if tok in VOCAB:
            vec[VOCAB.index(tok)] += 1.0
    # L2 normalize so SoftMax is stable.
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec


def _handcrafted_weights() -> tuple[np.ndarray, np.ndarray]:
    """Small weight matrix tuned to the same keyword groups as DEMO.

    Shape: W (n_intents, vocab), b (n_intents,). Hackathon demo weights —
    not a trained production model.
    """
    n_i, n_v = len(INTENT_LABELS), len(VOCAB)
    w = np.zeros((n_i, n_v), dtype=np.float32)
    b = np.array([0.05, 0.05, 0.05, 0.05, 0.15], dtype=np.float32)

    groups = {
        "rate_check": [
            "rate", "naira", "dollar", "usd", "exchange", "fx", "parallel", "official",
        ],
        "fee_compare": [
            "fee", "wise", "remitly", "bank", "cost", "compare", "cheapest", "charge",
        ],
        "send_now_advice": [
            "wait", "send", "now", "timing", "should", "urgent", "rent", "today",
        ],
        "checklist": [
            "checklist", "steps", "nuban", "account", "receive", "need", "how",
        ],
        "general": ["hello", "hi", "help"],
    }
    for intent_name, words in groups.items():
        i = INTENT_LABELS.index(intent_name)
        for word in words:
            if word in VOCAB:
                w[i, VOCAB.index(word)] = 2.5
    # Mild remittance prior toward fee/rate.
    for word in ("transfer", "remittance", "lagos", "mum", "family"):
        if word in VOCAB:
            w[INTENT_LABELS.index("fee_compare"), VOCAB.index(word)] += 0.8
            w[INTENT_LABELS.index("rate_check"), VOCAB.index(word)] += 0.5
    return w, b


class OpenVINOIntentModel:
    """Compile and run a tiny MatMul+Add+SoftMax graph on OpenVINO CPU."""

    def __init__(self) -> None:
        import openvino as ov
        from openvino import opset8 as ops

        self._ov = ov
        w, b = _handcrafted_weights()
        self._w = w
        self._b = b

        # Build IR graph: input(1, V) @ W.T + b → SoftMax → scores(1, I)
        param = ops.parameter([1, len(VOCAB)], np.float32, name="bow")
        weights = ops.constant(w.T)  # (V, I)
        bias = ops.constant(b.reshape(1, -1))  # (1, I)
        matmul = ops.matmul(param, weights, False, False)
        logits = ops.add(matmul, bias)
        probs = ops.softmax(logits, 1)
        model = ov.Model([probs], [param], "edge_remit_intent")

        core = ov.Core()
        self._compiled = core.compile_model(model, "CPU")
        self._output = self._compiled.output(0)
        self.backend = f"OpenVINO {ov.__version__} / CPU"
        logger.info("Compiled LIVE OpenVINO intent model: %s", self.backend)

    def predict(self, text: str) -> RouteResult:
        vec = _bow_vector(text).reshape(1, -1)
        result = self._compiled([vec])[self._output]
        probs = np.asarray(result).reshape(-1)
        idx = int(np.argmax(probs))
        intent = Intent(INTENT_LABELS[idx])
        scores = {INTENT_LABELS[i]: float(probs[i]) for i in range(len(INTENT_LABELS))}
        # Soft floor: if everything is near-uniform (empty BoW), fall to general.
        if float(np.max(probs)) < 0.22 and not text.strip():
            intent = Intent.GENERAL
        path = "LIVE OpenVINO path"
        conf = float(scores[intent.value])
        logger.info("%s → intent=%s conf=%.2f (%s)", path, intent.value, conf, self.backend)
        print(f"[router] {path} → {intent.value} ({conf:.2f}) [{self.backend}]")
        return RouteResult(
            intent=intent,
            confidence=conf,
            path=path,
            scores=scores,
            detail=self.backend,
        )


_live_model: OpenVINOIntentModel | None = None
_live_failed: str | None = None


def _get_live_model() -> OpenVINOIntentModel | None:
    global _live_model, _live_failed
    if _live_model is not None:
        return _live_model
    if _live_failed is not None:
        return None
    try:
        _live_model = OpenVINOIntentModel()
        return _live_model
    except Exception as exc:  # noqa: BLE001 — fall back cleanly for judges
        _live_failed = str(exc)
        logger.warning("LIVE OpenVINO unavailable (%s); using DEMO path", exc)
        return None


def route(text: str, force_demo: bool | None = None) -> RouteResult:
    """Route user text to an Intent via DEMO or LIVE OpenVINO path."""
    use_demo = DEMO_MODE if force_demo is None else force_demo
    want_live = LIVE_OPENVINO and not use_demo

    if want_live:
        model = _get_live_model()
        if model is not None:
            return model.predict(text)
        # Fall through to demo with an honest note.
        result = _demo_route(text)
        result.detail = f"fallback after LIVE failure: {_live_failed}"
        return result

    return _demo_route(text)


def router_status() -> dict[str, Any]:
    """Status blob for Streamlit sidebar / smoke tests."""
    openvino_version = None
    try:
        import openvino as ov

        openvino_version = ov.__version__
    except Exception:  # noqa: BLE001
        openvino_version = None

    return {
        "demo_mode": DEMO_MODE,
        "live_openvino_flag": LIVE_OPENVINO,
        "openvino_installed": openvino_version is not None,
        "openvino_version": openvino_version,
        "live_model_ready": _live_model is not None,
        "live_error": _live_failed,
        "project_root": str(PROJECT_ROOT),
        "intents": INTENT_LABELS,
    }
