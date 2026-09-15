"""Interactive CLI and a non-interactive --demo-once path for judges."""

from __future__ import annotations

import argparse
import sys

from edge_remit.agent import EdgeRemitAgent
from edge_remit.config import DEMO_MODE, LIVE_OPENVINO
from edge_remit.openvino_router import router_status
from edge_remit.speechmatics_stub import status as speech_status

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║  EdgeRemit  ·  Nigeria remittance timing & fees              ║
║  Intel OpenVINO local intent router  ·  Streamlit + CLI      ║
╚══════════════════════════════════════════════════════════════╝
"""

DEMO_ONCE_TURNS = [
    "What's the dollar to naira rate looking like this week?",
    "My brother in Houston wants to send $500 to our mum in Lagos. Wise vs Remitly vs the bank?",
    "Rent is due Friday. Should we wait for a better rate or send now? What does she need to receive it?",
]


def _mode_line() -> str:
    st = router_status()
    ov = st.get("openvino_version") or "not installed"
    if LIVE_OPENVINO and not DEMO_MODE:
        return f"mode: LIVE_OPENVINO · OpenVINO {ov}"
    return f"mode: DEMO OpenVINO path · package={ov}  (no keys required)"


def _print_turn(user: str, reply: str, tools: list[str], route_path: str) -> None:
    print(f"\nyou> {user}")
    if tools:
        print("  🔧 " + " → ".join(tools))
    print(f"  📡 {route_path}")
    print(f"\nagent>\n{reply}\n")


def run_demo_once(agent: EdgeRemitAgent) -> int:
    print(BANNER.strip())
    print(_mode_line())
    print("Running scripted demo (--demo-once). Tools + router are really called.\n")
    for user in DEMO_ONCE_TURNS:
        reply = agent.turn(user)
        path = agent.last_route.path if agent.last_route else "?"
        _print_turn(user, reply, agent.last_tools, path)
    print("Demo complete.")
    return 0


def run_prompts(agent: EdgeRemitAgent, prompts: list[str]) -> int:
    print(BANNER.strip())
    print(_mode_line())
    for user in prompts:
        reply = agent.turn(user)
        path = agent.last_route.path if agent.last_route else "?"
        _print_turn(user, reply, agent.last_tools, path)
    return 0


def run_interactive(agent: EdgeRemitAgent) -> int:
    print(BANNER.strip())
    print(_mode_line())
    print(f"Speechmatics: {speech_status()}")
    print("Type a question.  /help  /reset  /status  /quit\n")
    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return 0
        if not user:
            continue
        lowered = user.lower()
        if lowered in {"/quit", "/exit", "quit", "exit"}:
            print("bye.")
            return 0
        if lowered == "/reset":
            agent.reset()
            print("Conversation cleared.")
            continue
        if lowered == "/status":
            print(router_status())
            print(speech_status())
            continue
        if lowered == "/help":
            print(
                "Ask about USD/NGN, compare Wise vs Remitly vs bank, "
                "whether to wait, or what mum needs to receive ₦.\n"
                "Commands: /reset /status /quit"
            )
            continue
        reply = agent.turn(user)
        if agent.last_tools:
            print("  🔧 " + " → ".join(agent.last_tools))
        if agent.last_route:
            print(f"  📡 {agent.last_route.path} → {agent.last_route.intent.value}")
        print(f"\nagent>\n{reply}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="edge-remit",
        description="Nigeria remittance timing/fees assistant with OpenVINO intent routing.",
    )
    parser.add_argument(
        "--demo-once",
        action="store_true",
        help="Run a 3-turn scripted session and exit (for judges / CI).",
    )
    parser.add_argument(
        "--prompt",
        action="append",
        default=[],
        help="Run one user turn and print the reply. Repeatable. Then exit.",
    )
    parser.add_argument(
        "--live-openvino",
        action="store_true",
        help="Force LIVE OpenVINO path for this process (requires openvino package).",
    )
    args = parser.parse_args(argv)

    if args.live_openvino:
        import os

        os.environ["LIVE_OPENVINO"] = "1"
        os.environ["DEMO_MODE"] = "0"
        # Reload flags used by router.
        from edge_remit import config as cfg

        cfg.LIVE_OPENVINO = True
        cfg.DEMO_MODE = False

    agent = EdgeRemitAgent()
    if args.demo_once:
        return run_demo_once(agent)
    if args.prompt:
        return run_prompts(agent, args.prompt)
    if not sys.stdin.isatty():
        prompts = [line.strip() for line in sys.stdin if line.strip()]
        if not prompts:
            return run_demo_once(agent)
        return run_prompts(agent, prompts)
    return run_interactive(agent)


if __name__ == "__main__":
    raise SystemExit(main())
