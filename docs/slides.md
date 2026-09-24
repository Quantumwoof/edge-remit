# EdgeRemit — slide outline

PDF deck: [EdgeRemit-slides.pdf](EdgeRemit-slides.pdf).

**Event:** AI Infra Summit Hackathon · lablab.ai · **Intel Online** track  
**Team:** Joshua Jubelo / Quantumwoof · Nigeria  
**Deadline context:** Sep 17 2026 01:00 UTC

---

## Slide 1 — Problem

- Diaspora sends USD → family needs ₦ for rent, school, hospital
- Operators (Wise / Remitly / bank) quote different **all-in** costs
- People ask: *rate this week?* *which rail?* *send now or wait?* *what docs?*
- Cloud-only chat bots fail on flaky mobile data and ship private money talk off-device

---

## Slide 2 — Solution

**EdgeRemit** — remittance timing & fees assistant

1. **Local intent routing** with **Intel OpenVINO** (CPU)
2. Deterministic tools: rate snapshot · fee table · wait-vs-send · checklist
3. Streamlit UI judges can run in one command
4. Optional Speechmatics STT stub (bonus; never blocks demo)

---

## Slide 3 — Stack (Intel Online)

| Layer | Choice |
| --- | --- |
| Edge AI | **Intel OpenVINO Runtime** — BoW → MatMul → SoftMax on CPU |
| Demo fallback | Keyword router, same `Intent` enum (`DEMO OpenVINO path`) |
| App | Streamlit + CLI (`--demo-once`) |
| Tools | Pure Python remittance heuristics (labeled demo data) |
| Bonus | Speechmatics stub via `SPEECHMATICS_API_KEY` |

---

## Slide 4 — Architecture

```
User → Streamlit/CLI → OpenVINO intent router
                         ├─ DEMO path (keywords)
                         └─ LIVE path (OpenVINO CPU)
                     → Intent → tools → plain-language answer
```

Intents: `rate_check` · `fee_compare` · `send_now_advice` · `checklist` · `general`

---

## Slide 5 — Demo

1. `pip install -r requirements.txt`
2. `DEMO_MODE=1 streamlit run app.py`
3. Example #2: `$500` Houston → Lagos fee compare
4. Example #3: rent Friday → **send now** + checklist
5. Sidebar: OpenVINO install status + DEMO/LIVE flags
6. CLI: `python main.py --demo-once` (exit 0, no keys)

---

## Slide 6 — Why Intel / what’s next

- **Why OpenVINO:** tiny on-device classifier → low latency, offline-friendly, private
- **Honest MVP:** DEMO path always works; LIVE compiles a real OpenVINO model when the package is present
- **Next:** train a real text classifier → export ONNX → OpenVINO IR; live FX feeds; Speechmatics realtime mic

---

## Slide 7 — Ask

EdgeRemit: **decide better remittances on the edge** — Intel OpenVINO for intent, practical Nigeria tools for the answer.

MIT · github.com/Quantumwoof/edge-remit
