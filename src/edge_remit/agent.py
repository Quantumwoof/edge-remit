"""EdgeRemit agent: OpenVINO intent router → remittance tools → synthesis."""

from __future__ import annotations

from typing import Any

from edge_remit.openvino_router import Intent, RouteResult, route
from edge_remit.synthesizer import synthesize
from edge_remit.tools import (
    compare_fees,
    extract_amount,
    get_usd_ngn_rate,
    infer_direction,
    infer_method,
    infer_urgency,
    next_steps_checklist,
    recommend_timing,
)


class EdgeRemitAgent:
    """Single-turn agent used by Streamlit and the CLI."""

    def __init__(self) -> None:
        self.last_route: RouteResult | None = None
        self.last_tools: list[str] = []
        self.history: list[dict[str, str]] = []

    def reset(self) -> None:
        self.last_route = None
        self.last_tools = []
        self.history = []

    def turn(self, user_text: str, force_demo: bool | None = None) -> str:
        text = (user_text or "").strip()
        route_result = route(text, force_demo=force_demo)
        self.last_route = route_result
        intent = route_result.intent

        amount = extract_amount(text)
        direction = infer_direction(text)
        urgency = infer_urgency(text)
        method = infer_method(text)

        results: dict[str, Any] = {}
        used: list[str] = []

        def _call(name: str, fn, **kwargs) -> None:  # type: ignore[no-untyped-def]
            results[name] = fn(**kwargs)
            used.append(name)

        if intent == Intent.RATE_CHECK:
            _call("get_usd_ngn_rate", get_usd_ngn_rate, focus="overview")
        elif intent == Intent.FEE_COMPARE:
            args: dict[str, Any] = {"corridor": "US-NGN"}
            if amount:
                args["amount_usd"] = amount
            _call("compare_fees", compare_fees, **args)
        elif intent == Intent.SEND_NOW_ADVICE:
            args = {"direction": direction, "urgency": urgency}
            if amount:
                args["amount_usd"] = amount
            _call("recommend_timing", recommend_timing, **args)
            # Timing questions often want rate context too.
            _call("get_usd_ngn_rate", get_usd_ngn_rate, focus="overview")
        elif intent == Intent.CHECKLIST:
            _call(
                "next_steps_checklist",
                next_steps_checklist,
                direction=direction,
                method=method,
            )
        elif intent == Intent.GENERAL:
            # Greetings stay light; remittance-ish general still gets rate+fees.
            lower = text.lower()
            if any(w in lower for w in ("send", "transfer", "remit", "money", "$", "₦")):
                args = {"corridor": "US-NGN"}
                if amount:
                    args["amount_usd"] = amount
                _call("get_usd_ngn_rate", get_usd_ngn_rate, focus="overview")
                _call("compare_fees", compare_fees, **args)
        else:
            _call("get_usd_ngn_rate", get_usd_ngn_rate, focus="overview")

        # Multi-intent enrichment: if user mentions rent + checklist cues together.
        if intent == Intent.SEND_NOW_ADVICE and any(
            k in text.lower() for k in ("need", "checklist", "nuban", "account", "receive")
        ):
            _call(
                "next_steps_checklist",
                next_steps_checklist,
                direction=direction,
                method=method,
            )

        reply = synthesize(intent, results, route_result)
        self.last_tools = used
        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": reply})
        return reply
