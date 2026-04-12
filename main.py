import os
import json
import re
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import httpx
import google.generativeai as genai
from dotenv import load_dotenv, find_dotenv

# .env faylini qidirish va undagi o'zgaruvchilarni xotiraga yuklash
# override=True yordamida o'zgaruvchilarni qaytadan ishonchli o'qilishini ta'minlaymiz
load_dotenv(find_dotenv(), override=True)

app = FastAPI(title="TradingView to Telegram via Gemini API")

def get_env_var(key: str) -> str:
    val = os.getenv(key)
    if not val:
        print(f"DIQQAT: {key} o'zgaruvchisi topilmadi! Iltimos, .env faylni tekshiring.")
        return ""
    return val

GEMINI_API_KEY = get_env_var("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = get_env_var("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_env_var("TELEGRAM_CHAT_ID")

# Konsolga .env dan o'qilgan maxfiy parollarni qisman yashirilgan holda chiqarish
def mask_key(k: str) -> str:
    if not k: return "Topilmadi yoki Xato"
    k = k.strip() # Ortiqcha probellarni tozalaymiz
    if len(k) <= 8: return "***"
    return f"{k[:4]}...{k[-4:]}"

print("\n" + "="*40)
print("      YUKLANGAN O'ZGARUVCHILAR")
print("="*40)
print(f"GEMINI_API_KEY:     {mask_key(GEMINI_API_KEY)}")
print(f"TELEGRAM_BOT_TOKEN: {mask_key(TELEGRAM_BOT_TOKEN)}")
# TELEGRAM_CHAT_ID qisqa bo'lishi mumkin, shuning uchun ko'proq qismini ko'rsatamiz
_chat_id = TELEGRAM_CHAT_ID.strip() if TELEGRAM_CHAT_ID else "Topilmadi"
print(f"TELEGRAM_CHAT_ID:   {_chat_id}")
print("="*40 + "\n")

# Telegram_CHAT_ID tozalanganini ishonch hosil qilamiz
TELEGRAM_CHAT_ID = TELEGRAM_CHAT_ID.strip() if TELEGRAM_CHAT_ID else ""
TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN.strip() if TELEGRAM_BOT_TOKEN else ""


# Gemini uchun System Prompt
GEMINI_SYSTEM_PROMPT = """Siz professional ICT (Inner Circle Trader) tahlilchisiz. Sizga TradingView'dan JSON formatida narx ma'lumotlari, indikator ko'rsatkichlari va grafik holati keladi.

Sizning vazifangiz:

Quyidagi konsepsiyalar asosida tahlil qiling: Order Blocks, Fair Value Gap (FVG), Liquidity Hunt (BSL/SSL), Kill Zones va Market Structure Shift (MSS).

Agar barcha shartlar mos kelsa, aniq signal bering: BUY yoki SELL.

Har doim Stop Loss (SL) va Take Profit (TP) darajalarini hisoblab chiqing.

Agar holat noaniq bo'lsa, 'Kutish kerak' deb javob bering.

Javob formati: Faqat JSON formatida javob bering:
{
  "signal": "BUY/SELL/WAIT",
  "entry": 0.000,
  "sl": 0.000,
  "tp": 0.000,
  "reason": "Kisqa tahlil"
}"""

async def send_to_telegram(message: str):
    """Telegram bot orqali xabar yuborish"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Telegram yuborishda xatolik yuz berdi: {e}")

async def analyze_with_gemini(tv_data: dict) -> dict:
    """TradingView ma'lumotlarini Gemini SDK yordamida yuborish"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # model generation config and system prompt setup
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=GEMINI_SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        response = await model.generate_content_async(
            f"TradingView ma'lumotlari: {json.dumps(tv_data)}"
        )
        
        message_content = response.text
        
        # JSON blockni matndan qidirib topish
        json_match = re.search(r'\{.*\}', message_content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"signal": "ERROR", "reason": "Gemini JSON formatida javob bermadi."}
        
    except Exception as e:
        print(f"Gemini SDK xatolik yuz berdi: {e}")
        return {"signal": "ERROR", "reason": str(e)}

def format_telegram_message(ai_response: dict, tv_data: dict) -> str:
    """AI javobini Telegram xabariga o'girish"""
    signal = ai_response.get("signal", "WAIT")
    pair = tv_data.get("symbol", tv_data.get("pair", "Noma'lum valyuta"))
    
    if signal in ["WAIT", "Kutish kerak"]:
        return f"⏸ <b>KUTISH TAVSIYA ETILADI</b> | #{pair}\n\n📝 Sabab: {ai_response.get('reason', '')}"
    elif signal in ["BUY", "SELL"]:
        emoji = "🟢" if signal == "BUY" else "🔴"
        return (f"{emoji} <b>YANGI SIGNAL: {signal}</b> | #{pair}\n\n"
                f"🎯 <b>Entry:</b> {ai_response.get('entry')}\n"
                f"🛑 <b>Stop Loss:</b> {ai_response.get('sl')}\n"
                f"💰 <b>Take Profit:</b> {ai_response.get('tp')}\n\n"
                f"📝 <b>Tahlil:</b>\n{ai_response.get('reason')}")
    else:
        return f"⚠️ <b>Xatolik yuz berdi</b>\nSabab: {ai_response.get('reason')}"

@app.post("/webhook")
async def tradingview_webhook(request: Request, background_tasks: BackgroundTasks):
    """TradingView'dan kelgan webhookni qabul qilish"""
    try:
        # TradingView'dan JSON ma'lumotni o'qib olish
        tv_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Noto'g'ri JSON format")
    
    # Asosiy jarayonni Background process tarzida ishga tushirish (Webhook tezda 200 javob qaytarishi uchun)
    async def process_task(data: dict):
        ai_response = await analyze_with_gemini(data)
        message = format_telegram_message(ai_response, data)
        await send_to_telegram(message)
        
    background_tasks.add_task(process_task, tv_data)
    
    return {"status": "success", "message": "Webhook muvaffaqiyatli qabul qilindi"}

if __name__ == "__main__":
    import uvicorn
    # Test qilish uchun faylni to'g'ridan to'g'ri ishga tushirganda
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
