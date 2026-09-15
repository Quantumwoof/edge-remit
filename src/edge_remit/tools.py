"""Remittance tools: rate context, fees, timing, checklist.

All figures are labeled hackathon demos — not live operator quotes.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

# Labeled demo snapshot (Sep 2026 hackathon). Not a tradable quote.
DEMO_FX: dict[str, Any] = {
    "pair": "USD/NGN",
    "as_of": "2026-09-15",
    "official_ie_window": 1605.0,
    "parallel_street": 1648.0,
    "operator_mid_estimate": 1631.0,
    "history": {
        "d7_avg_parallel": 1632.0,
        "d30_avg_parallel": 1598.0,
        "d7_change_pct": 0.98,
        "d30_change_pct": 3.13,
    },
    "trend": "naira_weaker",
    "source": "demo_canned",
    "disclaimer": (
        "Hackathon demo snapshot — not a live tradable quote. "
        "Confirm the rate in Wise/Remitly/your bank before sending."
    ),
}

PROVIDERS: list[dict[str, Any]] = [
    {
        "name": "Wise",
        "fee_fixed_usd": 1.85,
        "fee_pct": 0.0065,
        "fx_markup_pct": 0.004,
        "speed": "often same day to a Nigerian bank; sometimes 1 business day",
        "receive_methods": ["Nigerian bank account (NUBAN)"],
        "notes": "Usually closest to mid-market. Rate lock typically 24–48 hours.",
    },
    {
        "name": "Remitly Express",
        "fee_fixed_usd": 3.99,
        "fee_pct": 0.0,
        "fx_markup_pct": 0.012,
        "speed": "minutes once funded, typical",
        "receive_methods": ["bank", "some mobile wallets on selected corridors"],
        "notes": "You pay extra for speed. First-send promo fees are common.",
    },
    {
        "name": "Remitly Economy",
        "fee_fixed_usd": 0.99,
        "fee_pct": 0.0,
        "fx_markup_pct": 0.018,
        "speed": "1–3 business days typical",
        "receive_methods": ["bank"],
        "notes": "Cheaper headline fee, wider FX spread. Always check delivered NGN.",
    },
    {
        "name": "Bank SWIFT / correspondent",
        "fee_fixed_usd": 25.0,
        "fee_pct": 0.0,
        "fx_markup_pct": 0.025,
        "speed": "2–5 business days; weekends and NIBSS cut-offs add delay",
        "receive_methods": ["Nigerian bank account"],
        "notes": "Intermediary banks may skim extra. Usually worst all-in for small amounts.",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_usd_ngn_rate(focus: str = "overview") -> dict[str, Any]:
    """USD/NGN rate context: official I&E vs parallel, plus a short trend."""
    snapshot = dict(DEMO_FX)
    snapshot["focus"] = focus or "overview"
    snapshot["fetched_at"] = _now_iso()
    return snapshot


def compare_fees(
    amount_usd: float = 500.0,
    corridor: str = "US-NGN",
) -> dict[str, Any]:
    """Rough all-in fee comparison for inbound USD → NGN remittance."""
    try:
        amount = float(amount_usd)
    except (TypeError, ValueError):
        amount = 500.0
    amount = max(50.0, min(amount, 20_000.0))

    mid = float(DEMO_FX["operator_mid_estimate"])
    rows = []
    for provider in PROVIDERS:
        fee = provider["fee_fixed_usd"] + amount * provider["fee_pct"]
        send_after_fee = max(amount - fee, 0.0)
        effective_rate = mid * (1.0 - provider["fx_markup_pct"])
        delivered = send_after_fee * effective_rate
        all_in_cost = amount * mid - delivered
        rows.append(
            {
                "provider": provider["name"],
                "fee_usd": round(fee, 2),
                "fx_markup_pct": provider["fx_markup_pct"] * 100.0,
                "effective_usd_ngn": round(effective_rate, 2),
                "you_receive_ngn": round(delivered, 0),
                "implied_all_in_cost_usd": round(all_in_cost / mid, 2),
                "speed": provider["speed"],
                "receive_methods": provider["receive_methods"],
                "notes": provider["notes"],
            }
        )

    rows.sort(key=lambda r: r["you_receive_ngn"], reverse=True)
    best = rows[0]["provider"] if rows else None
    return {
        "corridor": corridor or "US-NGN",
        "amount_usd": amount,
        "mid_usd_ngn": mid,
        "as_of": DEMO_FX["as_of"],
        "best_delivered": best,
        "providers": rows,
        "disclaimer": (
            "Static hackathon estimates, not live operator quotes. "
            "Promo fees and corridor-specific FX spreads will differ. "
            "Compare the naira the recipient actually receives."
        ),
    }


def recommend_timing(
    direction: str = "inbound",
    urgency: str = "normal",
    amount_usd: float | None = None,
) -> dict[str, Any]:
    """Plain-language wait vs send-now using the rate snapshot."""
    change_30 = float(DEMO_FX["history"]["d30_change_pct"])
    change_7 = float(DEMO_FX["history"]["d7_change_pct"])
    direction = (direction or "inbound").lower()
    if direction not in {"inbound", "outbound"}:
        direction = "inbound"
    urgency = (urgency or "normal").lower()

    if urgency in {"now", "urgent", "today", "asap"}:
        recommendation = "send_now"
        headline = "Send now — the need is time-sensitive."
        why = (
            "Rent, school fees, or hospital bills in Nigeria rarely wait for a "
            "better dollar rate. A missed deadline costs more than a 1–2% FX wiggle."
        )
    elif direction == "inbound":
        if change_30 >= 2.0:
            recommendation = "send_now"
            headline = "Send now — the naira is weaker, so each dollar buys more ₦."
            why = (
                f"Parallel USD/NGN is about {change_30:.1f}% above the 30-day average "
                f"(+{change_7:.1f}% on the week). If the sender can fund today, lock it."
            )
        elif change_30 <= -2.0:
            recommendation = "wait"
            headline = "Waiting a few days might yield more naira — only if it is not urgent."
            why = (
                "The naira has strengthened, so the same USD currently buys fewer ₦. "
                "Watch daily and set a floor; do not wait on hope if bills are due."
            )
        else:
            recommendation = "send_now"
            headline = "Rate is roughly flat — send when the recipient actually needs it."
            why = (
                "Don't overfit daily noise. For a normal transfer, time-to-cash and "
                "name-match matter more than squeezing the last ₦5,000."
            )
    else:
        if change_30 >= 2.0:
            recommendation = "wait"
            headline = "USD is relatively expensive in naira terms — wait if the foreign bill can slip."
            why = (
                f"The dollar buys about {change_30:.1f}% more naira than a month ago, "
                "which means you spend more ₦ per USD. If tuition/rent abroad is not due, wait a week and recheck."
            )
        elif change_30 <= -2.0:
            recommendation = "send_now"
            headline = "USD is cheaper in naira terms than it was — send if you already planned to."
            why = "A stronger naira is a better time to fund a foreign bill, all else equal."
        else:
            recommendation = "send_now"
            headline = "No strong FX edge — send on the due date, not the rumour."
            why = "Flat markets reward planning (docs, account details) over timing."

    return {
        "direction": direction,
        "urgency": urgency,
        "amount_usd": amount_usd,
        "recommendation": recommendation,
        "headline": headline,
        "why": why,
        "rate_context": {
            "parallel_street": DEMO_FX["parallel_street"],
            "official_ie_window": DEMO_FX["official_ie_window"],
            "d7_change_pct": change_7,
            "d30_change_pct": change_30,
            "trend": DEMO_FX["trend"],
        },
        "caveat": (
            "Heuristic on a snapshot, not a forecast. Parallel vs official gaps "
            "can move on CBN headlines. Confirm in-app before you hit send."
        ),
        "source_rate": DEMO_FX.get("source"),
    }


def next_steps_checklist(
    direction: str = "inbound",
    method: str = "wise",
) -> dict[str, Any]:
    """Concrete sender/receiver checklist for a Nigeria remittance."""
    direction = (direction or "inbound").lower()
    method = (method or "wise").lower()

    inbound = [
        "Sender: pick a licensed operator (Wise, Remitly, or your bank) — never a 'man in the group chat' at a too-good rate.",
        "Receiver: send the exact account name as it appears on the NUBAN (10 digits). Name mismatch is the #1 bounce.",
        "Receiver: bank name + account number is enough for Wise/Remitly; BVN is usually NOT required for inbound USD→NGN.",
        "Sender: compare delivered ₦, not the headline fee. Screenshot the rate lock before paying.",
        "Sender: first time to this account? Send a small test (e.g. $20) if timing allows.",
        "Both: avoid Friday evening / Sunday funding — NIBSS and operator cut-offs slip into Monday.",
        "Receiver: if it is cash pickup (WU/MoneyGram), take a valid ID and the MTCN; bank deposit is usually cleaner.",
        "Receiver: OPay/PalmPay wallets only work on corridors the operator lists — confirm before the sender pays.",
    ]
    outbound = [
        "Confirm the foreign account in the destination currency (USD/GBP) and the SWIFT/IBAN exactly.",
        "Budget the official I&E or your bank's USD sale rate — it will not be the street cash rate.",
        "Have BVN + NIN + a stated purpose (tuition, medical, family) ready; banks will ask.",
        "For school fees, use the school's official payment portal or a licensed operator, not a personal third-party account.",
        "Ask your bank for all-in ₦ including SWIFT + correspondent charges before you approve.",
        "Keep SWIFT receipts; some schools only confirm after they see the credit, not the debit.",
    ]

    method_notes = {
        "wise": "Wise: receiver bank must accept USD-sourced NGN credits. Most commercial banks do.",
        "remitly": "Remitly: choose Express vs Economy on purpose. Economy is slower and usually worse FX.",
        "bank": "Bank SWIFT: ask who the correspondent is. Hidden $10–25 intermediary fees are common.",
    }
    steps = inbound if direction != "outbound" else outbound
    return {
        "direction": direction,
        "method": method,
        "steps": steps,
        "method_note": method_notes.get(method, method_notes["wise"]),
        "safety": (
            "Ignore unsolicited 'I can give you dollar at ₦…' DMs. "
            "Romance/invoice-redirect scams are common on remittance corridors."
        ),
    }


def extract_amount(text: str) -> float | None:
    patterns = [
        r"\$\s*([\d,]+(?:\.\d+)?)",
        r"([\d,]+(?:\.\d+)?)\s*(?:usd|dollars?)\b",
    ]
    lower = text.lower()
    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def infer_direction(text: str) -> str:
    t = text.lower()
    outbound_hits = (
        "abroad", "tuition", "out of nigeria", "send dollar",
        "usd from nigeria", "school fees overseas",
    )
    inbound_hits = (
        "mum", "mama", "mom", "dad", "family", "lagos", "abuja",
        "receive", "brother", "sister", "houston", "uk", "canada",
        "diaspora", "send to", "sending to",
    )
    if any(h in t for h in outbound_hits) and not any(h in t for h in inbound_hits):
        return "outbound"
    return "inbound"


def infer_urgency(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("rent", "hospital", "urgent", "today", "friday", "due", "school fee")):
        return "urgent"
    if any(w in t for w in ("can wait", "flexible", "next month", "no rush")):
        return "flexible"
    return "normal"


def infer_method(text: str) -> str:
    t = text.lower()
    if "wise" in t:
        return "wise"
    if "remitly" in t:
        return "remitly"
    if "swift" in t or ("bank" in t and "remitly" not in t):
        return "bank"
    return "wise"
