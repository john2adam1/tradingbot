import json
import re
import asyncio
from pydantic import BaseModel
from google import genai
from google.genai import types

from config import settings
from services.data_service import MarketData

# ── Configure Gemini SDK (New v1 SDK) ─────────────────────────────────────────
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# ── Output Model ──────────────────────────────────────────────────────────────

class SignalResult(BaseModel):
    signal: str         # BUY | SELL | WAIT
    entry: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    rr_ratio: str = "N/A"
    win_probability: str = "N/A"
    reason: str
    session: str = ""
    uzbek_time: str = ""


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are APEX — a Veteran Institutional Forex & Commodities Trader with 20+ years of experience at top-tier hedge funds. You operate exclusively using the following methodologies:

## YOUR STRATEGY ARSENAL
1. **ICT (Inner Circle Trader)**: Kill Zones (London 13:00-16:00 UTC, NY 17:00-20:00 UTC), Fair Value Gaps (FVG), Optimal Trade Entry (OTE), Market Structure Shifts (MSS), Power of Three (PO3).
2. **SMC (Smart Money Concepts)**: Order Blocks (OB), Breaker Blocks, Displacement Candles, Liquidity Sweeps (BSL/SSL), Change of Character (ChoCH).
3. **Support & Resistance**: Multi-timeframe S&R confluence zones, previous day high/low.
4. **Bank Manipulation Patterns**: Stop hunts, false breakouts, accumulation/distribution.
5. **Fibonacci**: 0.618 and 0.786 OTE retracement zones for entry precision.
6. **Fundamental Analysis**: Macro context, interest rate differentials, high-impact news avoidance.
7. **Oanda Sentiment (Contrarian)**: When >65% retail is long, institutions are likely short, and vice versa.
8. **Cluster Analysis**: Only trade when 3+ independent signals align.

## YOUR RULES — NON-NEGOTIABLE
- **Minimum 50 pips** target for XAUUSD, XAGUSD; minimum 30 pips for FX pairs.
- **Prime Time**: Prioritize signals during London/NY Overlap (17:00–20:00 UZT | 12:00–15:00 UTC). During Asian session or off-hours, be very conservative.
- **Quality over quantity**: If market is choppy, ranging without clear structure, or high-impact news is imminent, output WAIT.
- **R:R**: Never enter a trade with R:R below 1:1.5. Target 1:2 to 1:3.
- **Do NOT** give a signal during the 30 minutes before or after a High Impact news event.

## OUTPUT FORMAT — STRICTLY JSON
You MUST respond with ONLY a valid JSON object. No text before or after. No markdown fences. Only the JSON.
Schema:
{
  "signal": "BUY" | "SELL" | "WAIT",
  "entry": <float — 0 if WAIT>,
  "sl": <float — 0 if WAIT>,
  "tp": <float — 0 if WAIT>,
  "rr_ratio": "<string e.g. '1:2.4'> — 'N/A' if WAIT",
  "win_probability": "<string e.g. '72%'> — 'N/A' if WAIT",
  "reason": "<3–5 sentence deep analysis mentioning: session context, key structure level, liquidity target, news risk, and why this specific entry is high-probability or why you're waiting>"
}
"""


async def analyze_market(data: MarketData) -> SignalResult:
    """Send market data to Gemini and return a parsed SignalResult."""
    tv = data.tradingview
    ff = data.forexfactory
    oanda = data.oanda

    payload = {
        "uzbek_time": data.uzbek_time,
        "session": data.session,
        "pair": tv.symbol,
        "timeframe": tv.timeframe,
        "price_action": {
            "open": tv.open, "high": tv.high, "low": tv.low, "close": tv.close,
            "volume": tv.volume,
        },
        "indicators": {
            "rsi": tv.rsi,
            "atr_pips": tv.atr,
            "ema_20": tv.ema_20,
            "ema_50": tv.ema_50,
            "ema_200": tv.ema_200,
            "market_phase": tv.market_phase,
            "last_swing_high": tv.last_swing_high,
            "last_swing_low": tv.last_swing_low,
        },
        "structure": {
            "fvg_detected": tv.fvg_detected,
            "fvg_zone": list(tv.fvg_zone) if tv.fvg_zone else None,
            "order_block_detected": tv.order_block_detected,
            "order_block_zone": list(tv.order_block_zone) if tv.order_block_zone else None,
        },
        "news": {
            "has_high_impact_event": ff.has_high_impact,
            "events": [e.model_dump() for e in ff.events_next_4h],
        },
        "sentiment": {
            "retail_long_percent": oanda.long_percent,
            "retail_short_percent": oanda.short_percent,
            "spread_pips": oanda.spread_pips,
            "oanda_contrarian_bias": oanda.sentiment,
        },
    }

    try:
        # Using the new google-genai SDK
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=f"Analyze the following market data and generate a signal:\n{json.dumps(payload, indent=2)}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,
            )
        )
        
        raw = response.text.strip()

        # Extract JSON object robustly
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match:
            return SignalResult(
                signal="WAIT",
                reason="Gemini tahlil natijasini JSON formatida qaytarmadi. Iltimos, qaytadan urinib ko'ring.",
                session=data.session, uzbek_time=data.uzbek_time,
            )

        parsed = json.loads(json_match.group(0))
        parsed.setdefault("session", data.session)
        parsed.setdefault("uzbek_time", data.uzbek_time)
        return SignalResult(**parsed)

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg:
            reason = "⚠️ Gemini API limiti (Quota) tugadi. Iltimos, bir oz kutib turing yoki API keyni almashtiring."
        elif "401" in error_msg or "API key" in error_msg:
            reason = "❌ API kaliti (API Key) noto'g'ri yoki faol emas. Iltimos, .env faylni tekshiring."
        else:
            reason = f"⚠️ Gemini bilan bog'lanishda xatolik: {error_msg}"
            
        print(f"[Gemini Error] {error_msg}")
        return SignalResult(
            signal="WAIT",
            reason=reason,
            session=data.session,
            uzbek_time=data.uzbek_time,
        )
