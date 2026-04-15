"""
Messages: HTML-formatted Telegram message templates.
Uses monospaced fonts and emojis for a premium institutional signal look.
"""
from services.ai_service import SignalResult


WELCOME_MESSAGE = (
    "🤖 <b>APEX Trading Intelligence</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Welcome. I am your AI-powered institutional analyst.\n"
    "I leverage <b>ICT · SMC · Fundamentals</b> to find high-probability setups.\n\n"
    "📌 <i>Quality over quantity — I only signal when conditions align.</i>\n\n"
    "Let's begin. Select your <b>Trading Type</b>:"
)


def step_timeframe_message(trading_type: str) -> str:
    label = "⚡ Scalp" if trading_type == "scalp" else "🌊 Swing"
    return (
        f"✅ Type: <b>{label}</b>\n\n"
        "Now select your <b>Timeframe</b>:"
    )


def step_pair_message(trading_type: str, timeframe: str) -> str:
    label = "⚡ Scalp" if trading_type == "scalp" else "🌊 Swing"
    return (
        f"✅ Type: <b>{label}</b>  |  ✅ TF: <b>{timeframe}</b>\n\n"
        "Select the <b>Trading Pair</b>:"
    )


def step_analyze_message(trading_type: str, timeframe: str, pair: str) -> str:
    label = "⚡ Scalp" if trading_type == "scalp" else "🌊 Swing"
    return (
        "📋 <b>Analysis Parameters</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"  <code>Type      : {label}</code>\n"
        f"  <code>Timeframe : {timeframe}</code>\n"
        f"  <code>Pair      : {pair}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Ready? Press <b>Analyze Now</b> to generate your signal."
    )


LOADING_MESSAGE = (
    "⏳ <b>Gathering Market Intelligence...</b>\n\n"
    "<code>📡 Fetching TradingView data...</code>\n"
    "<code>📰 Scanning ForexFactory calendar...</code>\n"
    "<code>📊 Reading Oanda sentiment...</code>\n"
    "<code>🧠 Running APEX AI analysis...</code>"
)


def format_signal_message(result: SignalResult, pair: str, timeframe: str) -> str:
    """Format the AI signal into a premium HTML Telegram message."""
    signal = result.signal.upper()

    if signal == "BUY":
        header = f"🟢 <b>BUY SIGNAL</b> | <code>{pair}</code> [{timeframe}]"
        signal_line = "🟢 <b>BUY</b>"
    elif signal == "SELL":
        header = f"🔴 <b>SELL SIGNAL</b> | <code>{pair}</code> [{timeframe}]"
        signal_line = "🔴 <b>SELL</b>"
    else:
        return format_wait_message(result, pair, timeframe)

    entry_str = f"{result.entry:.5f}" if result.entry else "—"
    sl_str    = f"{result.sl:.5f}"    if result.sl    else "—"
    tp_str    = f"{result.tp:.5f}"    if result.tp    else "—"

    return (
        f"{header}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"  {signal_line}\n\n"
        f"  🎯 <code>Entry  : {entry_str}</code>\n"
        f"  🛑 <code>SL     : {sl_str}</code>\n"
        f"  💰 <code>TP     : {tp_str}</code>\n\n"
        f"  📐 <code>R:R    : {result.rr_ratio}</code>\n"
        f"  🏆 <code>Win %  : {result.win_probability}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🕐 <code>{result.uzbek_time}</code>  {result.session}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>Analysis:</b>\n<i>{result.reason}</i>\n\n"
        "⚠️ <i>Not financial advice. Use proper risk management.</i>"
    )


def format_wait_message(result: SignalResult, pair: str, timeframe: str) -> str:
    return (
        f"⏸ <b>NO SIGNAL</b> | <code>{pair}</code> [{timeframe}]\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🕐 <code>{result.uzbek_time}</code>  {result.session}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ <b>Wait for Better Conditions</b>\n\n"
        f"📝 <b>Reason:</b>\n<i>{result.reason}</i>\n\n"
        "💡 <i>Patience is the edge. I'll signal when conditions align.</i>"
    )


def format_error_message() -> str:
    return (
        "⚠️ <b>Analysis Failed</b>\n\n"
        "Could not retrieve market data or the AI returned an unexpected response.\n"
        "Please try again in a moment."
    )
