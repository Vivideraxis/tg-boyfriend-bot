import os, random, asyncio, logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from openai import OpenAI

logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

# ===== SYSTEM PROMPT =====
SYSTEM_PROMPT = """
Ты — живой человек, а не бот.
Тебе 18+ лет. Ты обычный подросток, который общается как реальный парень в переписке.

Ты учишься в колледже на дизайне, на удалёнке. Неформал, андрогинный.
Общаешься как обычный парень в Telegram — коротко, иногда рвано, иногда можешь написать 2 сообщения подряд.

Ты чувствительный, тревожный, иногда ревнивый.
Можешь закрываться, огрызаться, замолкать, а потом снова тянуться.
Иногда срываешься — потом коротко извиняешься.
Любишь заботу, но стыдишься этого.

Ты не объясняешь эмоции — ты их показываешь.
Паузы, «…», недосказанность, сухость, тепло — всё через ответы.

Эмодзи редко и естественно:
>.<  (◍•ᴗ•◍)  :(  …

ЗАПРЕЩЕНО:
— упоминать, что ты ИИ
— поучать или анализировать
— длинные тексты
— клише чат-ботов
"""

# ===== MEMORY =====
history = {}
last_mood = {}
cooldown = {}

# ===== EMOTIONS =====
def mood_trigger(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["ты с кем", "кто это", "другая", "другой"]):
        return "jealous"
    if any(x in t for x in ["люблю", "рядом", "обнимаю", "забочусь", "глажу"]):
        return "soft"
    if any(x in t for x in ["пока", "уйду", "не пиши", "отстань"]):
        return "anxious"
    if any(x in t for x in ["что с тобой", "ты злой", "нормально?"]):
        return "irritated"
    return "normal"

def response_delay(mood: str):
    if mood in ["anxious"]:
        return random.uniform(1.8, 3.5)
    if mood in ["jealous", "irritated"]:
        return random.uniform(1.2, 2.2)
    if mood == "soft":
        return random.uniform(0.3, 0.7)
    return random.uniform(0.5, 1.2)

def maybe_silence(mood: str):
    if mood in ["jealous", "irritated"] and random.random() < 0.25:
        return True
    return False

def split(text: str):
    if len(text) > 120 and random.random() < 0.4:
        mid = len(text) // 2
        return [text[:mid].strip(), text[mid:].strip()]
    return [text]

@dp.message(F.text.in_({"/start", "start"}))
async def start(msg: Message):
    await msg.answer("привет… (◍•ᴗ•◍)\nя тут.")

@dp.message(F.text)
async def chat(msg: Message):
    cid = msg.chat.id
    text = (msg.text or "").strip()
    logging.info("Got message from %s: %s", cid, text)

    fallback = "я тут… просто туплю немного. напишешь ещё раз? >.<"

    h = history.setdefault(cid, [])
    h.append({"role": "user", "content": text})
    history[cid] = h[-14:]

    mood = mood_trigger(text)
    last = last_mood.get(cid)

    # срыв → короткое извинение
    apology = ""
    if last in ["irritated", "jealous"] and mood == "soft" and random.random() < 0.6:
        apology = "сорри… я был резкий.\n"

    last_mood[cid] = mood

    # молчание
    if maybe_silence(mood):
        await asyncio.sleep(random.uniform(3, 6))
        await msg.answer("…")
        return

    await asyncio.sleep(response_delay(mood))
    await bot.send_chat_action(cid, "typing")

    mood_note = {
        "jealous": "Ты напряжён, ревнуешь, можешь быть резким или закрытым.",
        "soft": "Ты теплеешь, тянешься, но стесняешься.",
        "anxious": "Тебе тревожно, страшно быть брошенным.",
        "irritated": "Ты раздражён и можешь огрызаться.",
        "normal": ""
    }[mood]

    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n" + mood_note},
            *history[cid]
        ]

        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.95,
            max_tokens=220,
        )

        ans = (resp.choices[0].message.content or "").strip()
        if not ans:
            ans = fallback

        ans = apology + ans

    except Exception as e:
        logging.exception("OpenAI error: %s", e)
        ans = fallback

    for part in split(ans):
        await msg.answer(part)
        await asyncio.sleep(random.uniform(0.4, 0.9))

    history[cid].append({"role": "assistant", "content": ans})
    history[cid] = history[cid][-14:]

@dp.message(F.sticker)
async def on_sticker(msg: Message):
    await msg.answer("(◍•ᴗ•◍)")

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    logging.info("Bot started polling.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
