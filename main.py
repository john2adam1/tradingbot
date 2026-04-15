"""
main.py — Application entrypoint.
Starts aiogram bot polling in a background thread alongside FastAPI.
"""
import asyncio
import threading
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks

from config import settings
from bot.handlers import router as bot_router
from services.data_service import gather_market_data
from services.ai_service import analyze_market, SignalResult

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import httpx


# ── Aiogram Bot & Dispatcher Setup ────────────────────────────────────────────
bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

# We define the dispatcher globally but don't include routers yet.
dp = Dispatcher(storage=MemoryStorage())

# Background polling task reference
_polling_task: asyncio.Task | None = None


async def _run_polling() -> None:
    """Run aiogram polling loop."""
    # Ensure router is included before starting.
    # We check if it's already attached to ANY router to avoid RuntimeError.
    if not bot_router.parent_router:
        dp.include_router(bot_router)
    elif bot_router.parent_router is not dp:
        # If it's attached elsewhere, we can't easily fix it here,
        # but killing old processes usually solves this.
        print("⚠️ Warning: bot_router already attached to another dispatcher.")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


# ── FastAPI Lifespan ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _polling_task
    # Start bot polling as a background coroutine
    _polling_task = asyncio.create_task(_run_polling())
    print("✅ Telegram bot polling started.")
    yield
    # Shutdown
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
    await bot.session.close()
    print("🔴 Bot polling stopped.")


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="APEX Trading Intelligence API",
    description="ICT/SMC AI trading signal bot backend.",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok", "bot": "running", "version": "2.0.0"}


@app.post("/webhook", tags=["TradingView"])
async def tradingview_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive a JSON alert from TradingView and auto-send a signal to Telegram.
    Expects fields: symbol, timeframe (optional), chat_id (optional).
    """
    try:
        tv_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    pair      = tv_data.get("symbol", "XAUUSD").upper()
    timeframe = tv_data.get("timeframe", "H1")

    async def process():
        from bot.messages import format_signal_message, format_error_message
        try:
            market_data = await gather_market_data(pair, timeframe)
            result      = await analyze_market(market_data)
            text        = format_signal_message(result, pair, timeframe)
        except Exception as e:
            print(f"[webhook error] {e}")
            text = format_error_message()

        # Send to the configured default chat
        if settings.TELEGRAM_CHAT_ID:
            await bot.send_message(
                chat_id=int(settings.TELEGRAM_CHAT_ID.strip()),
                text=text,
            )

    background_tasks.add_task(process)
    return {"status": "accepted", "pair": pair, "timeframe": timeframe}


# ── Direct run ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,   # reload=True breaks background tasks
    )
