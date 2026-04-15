"""
Keyboards: All InlineKeyboardMarkup builders for the bot conversation flow.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def trading_type_keyboard() -> InlineKeyboardMarkup:
    """Step 1: Choose Scalp or Swing."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚡ Scalp", callback_data="type:scalp"),
        InlineKeyboardButton(text="🌊 Swing", callback_data="type:swing"),
    )
    return builder.as_markup()


def timeframe_keyboard(trading_type: str) -> InlineKeyboardMarkup:
    """Step 2: Choose timeframe based on trading type."""
    builder = InlineKeyboardBuilder()
    if trading_type == "scalp":
        builder.row(
            InlineKeyboardButton(text="M1", callback_data="tf:M1"),
            InlineKeyboardButton(text="M5", callback_data="tf:M5"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="M15", callback_data="tf:M15"),
            InlineKeyboardButton(text="H1", callback_data="tf:H1"),
        )
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="back:type"))
    return builder.as_markup()


def pair_keyboard() -> InlineKeyboardMarkup:
    """Step 3: Choose trading pair."""
    builder = InlineKeyboardBuilder()
    pairs = ["XAUUSD", "XAGUSD", "EURUSD", "AUDUSD", "USDJPY"]
    for pair in pairs:
        builder.button(text=f"💹 {pair}", callback_data=f"pair:{pair}")
    builder.adjust(2)  # 2 per row
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="back:timeframe"))
    return builder.as_markup()


def analyze_keyboard() -> InlineKeyboardMarkup:
    """Step 4: Trigger analysis or go back."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Analyze Now", callback_data="action:analyze"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Change Pair", callback_data="back:pair"),
        InlineKeyboardButton(text="🏠 Start Over", callback_data="back:start"),
    )
    return builder.as_markup()


def new_analysis_keyboard() -> InlineKeyboardMarkup:
    """After signal delivery: offer fresh start."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔁 New Analysis", callback_data="back:start"))
    return builder.as_markup()
