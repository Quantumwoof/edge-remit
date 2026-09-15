# Sample session — EdgeRemit (DEMO OpenVINO path)

Captured from `DEMO_MODE=1 python main.py --demo-once`. Tools and the intent router are really invoked.

```
$ DEMO_MODE=1 python main.py --demo-once
```

```
╔══════════════════════════════════════════════════════════════╗
║  EdgeRemit  ·  Nigeria remittance timing & fees              ║
║  Intel OpenVINO local intent router  ·  Streamlit + CLI      ║
╚══════════════════════════════════════════════════════════════╝
mode: DEMO OpenVINO path · package=…  (no keys required)
Running scripted demo (--demo-once). Tools + router are really called.


you> What's the dollar to naira rate looking like this week?
  🔧 get_usd_ngn_rate
  📡 DEMO OpenVINO path

agent>
**Rate context**
Official I&E window is about ₦1,605 / USD; parallel/street is about ₦1,648. …
_Router: DEMO OpenVINO path → `rate_check`_


you> My brother in Houston wants to send $500 to our mum in Lagos. Wise vs Remitly vs the bank?
  🔧 compare_fees
  📡 DEMO OpenVINO path

agent>
**Fees (illustrative, $500.00 → NGN, mid ~₦1,631)**
- **Wise**: … Best delivered ₦ on this table: **Wise**.
_Router: DEMO OpenVINO path → `fee_compare`_


you> Rent is due Friday. Should we wait for a better rate or send now? What does she need to receive it?
  🔧 recommend_timing → get_usd_ngn_rate → next_steps_checklist
  📡 DEMO OpenVINO path

agent>
**Wait vs send now → SEND NOW**
…
**Next steps**
1. Sender: pick a licensed operator …
_Router: DEMO OpenVINO path → `send_now_advice`_

Demo complete.
```

## What to notice

| Turn | Intent | Tools | Point |
| --- | --- | --- | --- |
| 1 Rate | `rate_check` | `get_usd_ngn_rate` | DEMO OpenVINO path logs; official vs parallel |
| 2 Fees | `fee_compare` | `compare_fees` | $500 US→NG — Wise wins delivered ₦ |
| 3 Timing + steps | `send_now_advice` | timing + checklist | Rent due Friday → send now + NUBAN steps |

## LIVE OpenVINO (optional)

```
$ LIVE_OPENVINO=1 DEMO_MODE=0 python main.py --demo-once --live-openvino
[router] LIVE OpenVINO path → rate_check (0.xx) [OpenVINO … / CPU]
```

## Streamlit

```
$ DEMO_MODE=1 streamlit run app.py
```

Open the local URL Streamlit prints. Use the example buttons, then open the Fee table and Speechmatics stub tabs.
