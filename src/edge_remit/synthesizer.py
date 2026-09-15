"""Turn tool JSON into plain-language answers for Streamlit / CLI."""

from __future__ import annotations

from typing import Any

from edge_remit.openvino_router import Intent, RouteResult


def _fmt_naira(value: float) -> str:
    return f"₦{value:,.0f}"


def _fmt_usd(value: float) -> str:
    return f"${value:,.2f}"


def synthesize(intent: Intent, results: dict[str, Any], route: RouteResult) -> str:
    parts: list[str] = []
    fx = results.get("get_usd_ngn_rate") or {}
    fees = results.get("compare_fees") or {}
    timing = results.get("recommend_timing") or {}
    checklist = results.get("next_steps_checklist") or {}

    if intent == Intent.GENERAL and not any((fx, fees, timing, checklist)):
        return (
            "Hey — I'm **EdgeRemit**. I help people in Nigeria time USD↔NGN "
            "transfers and compare rough fees (Wise, Remitly, bank).\n\n"
            "Ask me about the dollar rate, a $500 send to Lagos, whether to wait, "
            "or what mum needs to receive ₦.\n\n"
            f"_Router: {route.path} → `{route.intent.value}`_"
        )

    if fx:
        official = fx.get("official_ie_window")
        parallel = fx.get("parallel_street")
        hist = fx.get("history") or {}
        src = fx.get("source", "demo")
        parts.append(
            "**Rate context**\n"
            f"Official I&E window is about ₦{official:,.0f} / USD; parallel/street "
            f"is about ₦{parallel:,.0f}. That is {hist.get('d30_change_pct', '?')}% "
            f"weaker than the 30-day parallel average "
            f"({hist.get('d7_change_pct', '?')}% on the week). "
            f"Source: `{src}`. This is context, not a rate you can trade — confirm in-app."
        )

    if fees:
        amount = fees.get("amount_usd", 500)
        mid = fees.get("mid_usd_ngn")
        lines = [
            f"**Fees (illustrative, {_fmt_usd(amount)} → NGN, mid ~₦{mid:,.0f})**"
        ]
        for row in fees.get("providers") or []:
            lines.append(
                f"- **{row['provider']}**: fee {_fmt_usd(row['fee_usd'])}, "
                f"you receive about {_fmt_naira(row['you_receive_ngn'])}, "
                f"{row['speed']}."
            )
        best = fees.get("best_delivered")
        if best:
            lines.append(
                f"Best delivered ₦ on this table: **{best}**. "
                "Always compare the naira on screen, not the headline fee."
            )
        if fees.get("disclaimer"):
            lines.append(f"_{fees['disclaimer']}_")
        parts.append("\n".join(lines))

    if timing:
        rec = timing.get("recommendation", "send_now").replace("_", " ")
        parts.append(
            f"**Wait vs send now → {rec.upper()}**\n"
            f"{timing.get('headline', '')} {timing.get('why', '')}"
        )

    if checklist:
        steps = checklist.get("steps") or []
        shown = steps[:6]
        numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(shown, 1))
        note = checklist.get("method_note") or ""
        safety = checklist.get("safety") or ""
        parts.append(f"**Next steps**\n{numbered}\n\n{note}\n\n{safety}".strip())

    if not parts:
        parts.append(
            "I can help with USD/NGN context, a rough Wise vs Remitly vs bank "
            "comparison, whether to wait or send now, and a receive checklist. "
            "Try: “My brother wants to send $500 to Lagos this week.”"
        )

    parts.append(
        "_Estimates only — hackathon demos, not live quotes. "
        "EdgeRemit does not move money or lock rates._"
    )
    parts.append(
        f"_Router: {route.path} → `{route.intent.value}` "
        f"(conf {route.confidence:.2f})_"
    )
    return "\n\n".join(parts)
