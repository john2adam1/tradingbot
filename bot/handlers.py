"""
Handlers: All aiogram FSM command and callback handlers.
Uses a Router that is registered in main.py.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards import (
    trading_type_keyboard,
    timeframe_keyboard,
    pair_keyboard,
    analyze_keyboard,
    new_analysis_keyboard,
)
from bot.messages import (
    WELCOME_MESSAGE,
    LOADING_MESSAGE,
    step_timeframe_message,
    step_pair_message,
    step_analyze_message,
    format_signal_message,
    format_error_message,
)
from services.data_service import gather_market_data
from services.ai_service import analyze_market

router = Router()


# ── FSM State Group ───────────────────────────────────────────────────────────
class AnalysisFlow(StatesGroup):
    choosing_type      = State()
    choosing_timeframe = State()
    choosing_pair      = State()
    confirm_analyze    = State()
    analyzing          = State()


# ── /start command ────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AnalysisFlow.choosing_type)
    await message.answer(WELCOME_MESSAGE, reply_markup=trading_type_keyboard())


# ── Step 1: Trading Type ──────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("type:"))
async def cb_trading_type(callback: CallbackQuery, state: FSMContext) -> None:
    trading_type = callback.data.split(":")[1]   # "scalp" or "swing"
    await state.update_data(trading_type=trading_type)
    await state.set_state(AnalysisFlow.choosing_timeframe)

    await callback.message.edit_text(
        step_timeframe_message(trading_type),
        reply_markup=timeframe_keyboard(trading_type),
    )
    await callback.answer()


# ── Step 2: Timeframe ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("tf:"))
async def cb_timeframe(callback: CallbackQuery, state: FSMContext) -> None:
    timeframe = callback.data.split(":")[1]   # e.g. "M5"
    data = await state.get_data()
    await state.update_data(timeframe=timeframe)
    await state.set_state(AnalysisFlow.choosing_pair)

    await callback.message.edit_text(
        step_pair_message(data["trading_type"], timeframe),
        reply_markup=pair_keyboard(),
    )
    await callback.answer()


# ── Step 3: Pair ──────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("pair:"))
async def cb_pair(callback: CallbackQuery, state: FSMContext) -> None:
    pair = callback.data.split(":")[1]   # e.g. "XAUUSD"
    data = await state.get_data()
    await state.update_data(pair=pair)
    await state.set_state(AnalysisFlow.confirm_analyze)

    await callback.message.edit_text(
        step_analyze_message(data["trading_type"], data["timeframe"], pair),
        reply_markup=analyze_keyboard(),
    )
    await callback.answer()


# ── Step 4: Analyze ───────────────────────────────────────────────────────────
@router.callback_query(F.data == "action:analyze")
async def cb_analyze(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    pair      = data.get("pair", "XAUUSD")
    timeframe = data.get("timeframe", "H1")

    await state.set_state(AnalysisFlow.analyzing)

    # Show loading message immediately
    await callback.message.edit_text(LOADING_MESSAGE)
    await callback.answer()

    try:
        market_data = await gather_market_data(pair, timeframe)
        result      = await analyze_market(market_data)
        text        = format_signal_message(result, pair, timeframe)
    except Exception as e:
        print(f"[analyze error] {e}")
        text = format_error_message()

    await callback.message.edit_text(
        text,
        reply_markup=new_analysis_keyboard(),
        parse_mode="HTML",
    )
    await state.clear()


# ── Back Navigation ───────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("back:"))
async def cb_back(callback: CallbackQuery, state: FSMContext) -> None:
    destination = callback.data.split(":")[1]

    if destination == "start":
        await state.clear()
        await state.set_state(AnalysisFlow.choosing_type)
        await callback.message.edit_text(WELCOME_MESSAGE, reply_markup=trading_type_keyboard())

    elif destination == "type":
        await state.clear()
        await state.set_state(AnalysisFlow.choosing_type)
        await callback.message.edit_text(WELCOME_MESSAGE, reply_markup=trading_type_keyboard())

    elif destination == "timeframe":
        current = await state.get_data()
        trading_type = current.get("trading_type", "scalp")
        await state.set_state(AnalysisFlow.choosing_timeframe)
        await callback.message.edit_text(
            step_timeframe_message(trading_type),
            reply_markup=timeframe_keyboard(trading_type),
        )

    elif destination == "pair":
        current = await state.get_data()
        await state.set_state(AnalysisFlow.choosing_pair)
        await callback.message.edit_text(
            step_pair_message(current.get("trading_type","scalp"), current.get("timeframe","M5")),
            reply_markup=pair_keyboard(),
        )

    await callback.answer()
