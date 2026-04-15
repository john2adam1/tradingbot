"""
Data Service: Gathers market intelligence from TradingView, ForexFactory, and Oanda.
Currently uses realistic simulated data. Replace each function with real API calls
when you have API access.
"""
import random
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel


# ── Pydantic Models ──────────────────────────────────────────────────────────

class TradingViewData(BaseModel):
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    rsi: float           # 0–100
    atr: float           # Average True Range in pips
    ema_20: float
    ema_50: float
    ema_200: float
    market_phase: Literal["trending_up", "trending_down", "ranging", "consolidation"]
    last_swing_high: float
    last_swing_low: float
    fvg_detected: bool
    fvg_zone: tuple[float, float] | None     # (low, high) of the gap
    order_block_detected: bool
    order_block_zone: tuple[float, float] | None


class ForexFactoryEvent(BaseModel):
    time_utc: str
    currency: str
    event: str
    impact: Literal["high", "medium", "low"]
    forecast: str
    previous: str


class ForexFactoryData(BaseModel):
    events_next_4h: list[ForexFactoryEvent]
    has_high_impact: bool


class OandaData(BaseModel):
    symbol: str
    long_percent: float    # 0–100
    short_percent: float   # 0–100
    spread_pips: float
    sentiment: Literal["bullish", "bearish", "neutral"]


class MarketData(BaseModel):
    tradingview: TradingViewData
    forexfactory: ForexFactoryData
    oanda: OandaData
    session: str           # Current Forex session label
    uzbek_time: str        # Current time in UZT (UTC+5)


# ── Base prices per pair ──────────────────────────────────────────────────────
BASE_PRICES = {
    "XAUUSD": 2330.0,
    "XAGUSD": 27.50,
    "EURUSD": 1.0850,
    "AUDUSD": 0.6580,
    "USDJPY": 153.80,
}

ATR_PIPS = {
    "XAUUSD": 250,
    "XAGUSD": 180,
    "EURUSD": 80,
    "AUDUSD": 60,
    "USDJPY": 120,
}

PAIR_CURRENCIES = {
    "XAUUSD": ["XAU", "USD"],
    "XAGUSD": ["XAG", "USD"],
    "EURUSD": ["EUR", "USD"],
    "AUDUSD": ["AUD", "USD"],
    "USDJPY": ["USD", "JPY"],
}

HIGH_IMPACT_EVENTS = [
    ("Non-Farm Payroll", "USD"),
    ("CPI m/m", "USD"),
    ("Interest Rate Decision", "USD"),
    ("GDP q/q", "EUR"),
    ("Employment Change", "AUD"),
    ("BOJ Policy Rate", "JPY"),
    ("RBA Rate Statement", "AUD"),
    ("PMI Manufacturing", "EUR"),
]

def _get_session_label(uzbek_hour: int) -> str:
    """Map current Uzbekistan hour to Forex session."""
    if 5 <= uzbek_hour < 13:
        return "🌏 Asian Session"
    elif 13 <= uzbek_hour < 17:
        return "🌍 London Session"
    elif 17 <= uzbek_hour < 21:
        return "🔥 London/NY Overlap (Prime Time)"
    elif 21 <= uzbek_hour < 24 or uzbek_hour < 2:
        return "🌎 New York Session"
    else:
        return "🌙 Off-Hours (Low Liquidity)"


async def fetch_tradingview_data(pair: str, timeframe: str) -> TradingViewData:
    """Simulate realistic TradingView price action and indicator data."""
    base = BASE_PRICES[pair]
    volatility = base * 0.003   # 0.3% candle spread

    close = round(base + random.uniform(-volatility, volatility), 5)
    open_ = round(close + random.uniform(-volatility * 0.5, volatility * 0.5), 5)
    high = round(max(open_, close) + random.uniform(0, volatility * 0.7), 5)
    low = round(min(open_, close) - random.uniform(0, volatility * 0.7), 5)

    trend_bias = random.choice(["up", "up", "down", "sideways"])
    if trend_bias == "up":
        ema_20 = round(close * 0.9990, 5)
        ema_50 = round(close * 0.9975, 5)
        ema_200 = round(close * 0.9940, 5)
        phase = "trending_up"
    elif trend_bias == "down":
        ema_20 = round(close * 1.0012, 5)
        ema_50 = round(close * 1.0030, 5)
        ema_200 = round(close * 1.0065, 5)
        phase = "trending_down"
    else:
        ema_20 = round(close * 1.0002, 5)
        ema_50 = round(close * 0.9998, 5)
        ema_200 = round(close * 0.9990, 5)
        phase = random.choice(["ranging", "consolidation"])

    rsi = round(random.gauss(50, 18), 1)
    rsi = max(10.0, min(90.0, rsi))

    atr = ATR_PIPS[pair]
    swing_high = round(high + atr * 1.5 * (base / 10000 if pair not in ["XAUUSD", "XAGUSD"] else 1), 5)
    swing_low = round(low - atr * 1.5 * (base / 10000 if pair not in ["XAUUSD", "XAGUSD"] else 1), 5)

    fvg = random.random() < 0.4
    fvg_zone = None
    if fvg:
        fvg_mid = close + random.uniform(-volatility, volatility) * 0.5
        fvg_zone = (round(fvg_mid - volatility * 0.3, 5), round(fvg_mid + volatility * 0.3, 5))

    ob = random.random() < 0.5
    ob_zone = None
    if ob:
        ob_mid = close + random.uniform(-volatility * 2, volatility * 2)
        ob_zone = (round(ob_mid - volatility * 0.4, 5), round(ob_mid + volatility * 0.4, 5))

    return TradingViewData(
        symbol=pair, timeframe=timeframe,
        open=open_, high=high, low=low, close=close,
        volume=random.randint(5000, 80000),
        rsi=rsi, atr=float(atr),
        ema_20=ema_20, ema_50=ema_50, ema_200=ema_200,
        market_phase=phase,
        last_swing_high=swing_high, last_swing_low=swing_low,
        fvg_detected=fvg, fvg_zone=fvg_zone,
        order_block_detected=ob, order_block_zone=ob_zone,
    )


async def fetch_forexfactory_data(pair: str) -> ForexFactoryData:
    """Simulate ForexFactory economic calendar for the next 4 hours."""
    currencies = PAIR_CURRENCIES.get(pair, ["USD"])
    events: list[ForexFactoryEvent] = []

    # Randomly include 0–2 events
    num_events = random.randint(0, 3)
    for _ in range(num_events):
        name, currency = random.choice(HIGH_IMPACT_EVENTS)
        if currency in currencies or random.random() < 0.3:
            impact = random.choice(["high", "high", "medium", "low"])
            events.append(ForexFactoryEvent(
                time_utc=f"{random.randint(8, 15):02d}:{random.choice(['00', '30'])} UTC",
                currency=currency,
                event=name,
                impact=impact,
                forecast=f"{random.uniform(-0.5, 1.5):.1f}%",
                previous=f"{random.uniform(-0.3, 1.2):.1f}%",
            ))

    has_high = any(e.impact == "high" for e in events)
    return ForexFactoryData(events_next_4h=events, has_high_impact=has_high)


async def fetch_oanda_data(pair: str) -> OandaData:
    """Simulate Oanda retail sentiment and spread data."""
    long_pct = round(random.uniform(25, 75), 1)
    short_pct = round(100 - long_pct, 1)
    spread = round(random.uniform(0.5, 4.5), 1)

    if long_pct >= 60:
        # Contrarian: most retail longs → institutions likely short
        sentiment = "bearish"
    elif short_pct >= 60:
        sentiment = "bullish"
    else:
        sentiment = "neutral"

    return OandaData(
        symbol=pair,
        long_percent=long_pct,
        short_percent=short_pct,
        spread_pips=spread,
        sentiment=sentiment,
    )


async def gather_market_data(pair: str, timeframe: str) -> MarketData:
    """Orchestrate all data fetches and return a combined MarketData object."""
    import asyncio
    tv, ff, oanda = await asyncio.gather(
        fetch_tradingview_data(pair, timeframe),
        fetch_forexfactory_data(pair),
        fetch_oanda_data(pair),
    )

    now_utc = datetime.now(timezone.utc)
    uzbek_hour = (now_utc.hour + 5) % 24
    uzbek_time = f"{uzbek_hour:02d}:{now_utc.minute:02d} UZT"
    session = _get_session_label(uzbek_hour)

    return MarketData(
        tradingview=tv,
        forexfactory=ff,
        oanda=oanda,
        session=session,
        uzbek_time=uzbek_time,
    )
