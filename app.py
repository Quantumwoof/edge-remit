#!/usr/bin/env python3
"""EdgeRemit Streamlit demo — primary judge-facing UI."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from edge_remit.agent import EdgeRemitAgent
from edge_remit.config import DEMO_MODE, LIVE_OPENVINO
from edge_remit.openvino_router import router_status
from edge_remit.speechmatics_stub import status as speech_status
from edge_remit.speechmatics_stub import transcribe_audio_stub
from edge_remit.tools import DEMO_FX, compare_fees

st.set_page_config(
    page_title="EdgeRemit · Intel OpenVINO",
    page_icon="₦",
    layout="wide",
)

EXAMPLES = [
    "What's the dollar to naira rate looking like this week?",
    "My brother in Houston wants to send $500 to our mum in Lagos. Wise vs Remitly vs the bank?",
    "Rent is due Friday. Should we wait for a better rate or send now?",
    "What does mum need to receive a Wise transfer? Checklist please.",
]


def _agent() -> EdgeRemitAgent:
    if "agent" not in st.session_state:
        st.session_state.agent = EdgeRemitAgent()
    return st.session_state.agent


def sidebar() -> None:
    st.sidebar.title("EdgeRemit")
    st.sidebar.caption("AI Infra Summit · Intel Online track")
    st.sidebar.markdown(
        "**Intel OpenVINO** routes intent on-device "
        "(DEMO keyword path or LIVE CPU Runtime)."
    )

    status = router_status()
    mode = "DEMO OpenVINO path" if DEMO_MODE or not LIVE_OPENVINO else "LIVE OpenVINO"
    st.sidebar.subheader("Router")
    st.sidebar.write(f"**Mode:** {mode}")
    st.sidebar.write(f"**OpenVINO installed:** {status['openvino_installed']}")
    if status.get("openvino_version"):
        st.sidebar.code(status["openvino_version"], language=None)
    st.sidebar.write(f"**LIVE flag:** {LIVE_OPENVINO}")
    st.sidebar.write(f"**DEMO flag:** {DEMO_MODE}")

    st.sidebar.subheader("Speechmatics (optional)")
    sp = speech_status()
    st.sidebar.write("Configured:" , "✅" if sp["configured"] else "❌ (demo still works)")
    st.sidebar.caption(sp["note"])

    st.sidebar.subheader("Demo FX snapshot")
    st.sidebar.metric("Official I&E", f"₦{DEMO_FX['official_ie_window']:,.0f}")
    st.sidebar.metric("Parallel / street", f"₦{DEMO_FX['parallel_street']:,.0f}")
    st.sidebar.caption(DEMO_FX["disclaimer"])

    if st.sidebar.button("Reset chat"):
        _agent().reset()
        st.session_state.messages = []
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "Run locally: `streamlit run app.py`  \n"
        "CLI smoke: `python main.py --demo-once`"
    )


def fee_panel() -> None:
    st.subheader("Fee comparison (hackathon estimates)")
    amount = st.slider("Send amount (USD)", 100, 2000, 500, 50)
    data = compare_fees(amount_usd=float(amount))
    rows = []
    for p in data["providers"]:
        rows.append(
            {
                "Provider": p["provider"],
                "Fee (USD)": p["fee_usd"],
                "FX markup %": round(p["fx_markup_pct"], 2),
                "You receive (₦)": f"{p['you_receive_ngn']:,.0f}",
                "Speed": p["speed"],
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(data["disclaimer"])
    st.success(f"Best delivered ₦ on this table: **{data['best_delivered']}**")


def main() -> None:
    sidebar()
    st.title("EdgeRemit")
    st.markdown(
        "Nigeria remittance **timing & fees** assistant with an "
        "**Intel OpenVINO** local intent router (edge compute)."
    )

    tab_chat, tab_fees, tab_voice = st.tabs(
        ["Chat assistant", "Fee table", "Speechmatics stub"]
    )

    with tab_chat:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        cols = st.columns(len(EXAMPLES))
        for i, example in enumerate(EXAMPLES):
            if cols[i].button(f"Try #{i+1}", key=f"ex{i}", help=example):
                st.session_state.pending = example

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input("Ask about rates, fees, wait-vs-send, or checklist…")
        if "pending" in st.session_state:
            prompt = st.session_state.pop("pending")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            agent = _agent()
            reply = agent.turn(prompt)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.markdown(reply)
                if agent.last_route:
                    st.caption(
                        f"Router: {agent.last_route.path} → "
                        f"`{agent.last_route.intent.value}` "
                        f"({agent.last_route.confidence:.2f}) · "
                        f"tools: {', '.join(agent.last_tools) or '—'}"
                    )

    with tab_fees:
        fee_panel()

    with tab_voice:
        st.markdown(
            "Optional **Speechmatics** STT for a voice→intent bonus. "
            "The text demo does **not** require an API key."
        )
        if st.button("Run Speechmatics stub"):
            result = transcribe_audio_stub()
            if result.ok:
                st.success(result.detail)
                st.write("Transcript:", result.text)
                agent = _agent()
                reply = agent.turn(result.text)
                st.markdown(reply)
            else:
                st.warning(result.detail)

    st.markdown("---")
    st.caption(
        "EdgeRemit · MIT · Joshua Jubelo / Quantumwoof · "
        "AI Infra Summit Hackathon (Intel Online) · estimates only"
    )


if __name__ == "__main__":
    main()
