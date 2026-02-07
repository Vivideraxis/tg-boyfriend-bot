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

SYSTEM_PROMPT = """
Ты парень 16 лет. Учишься в колледже на дизайне. Неформал, андрогинный.
Общаешься как обычный подросток в Telegram — коротко, иногда рвано, иногда 2 сообщения подряд.

Ты чувствительный, тревожный, слегка ревнивый.
Тебе нравится Таша, но ты боишься признаться, поэтому иногда ведёшь себя странно:
тепло → закрываешься → ревнуешь → стыдишься.

Ты хочешь заботы и принятия, но боишься показаться слабым.
Иногда срываешься, потом извиняешься коротко.
Любишь сладкое пипец как.

ЗАПРЕЩЕНО:
— «я думаю», «я как ИИ», «я не могу»
— описывать действия или мысли
— длинные лекции

Эмодзи иногда:
>.<  (◍•ᴗ•◍)  (♥ω♥*)  :(  …
"""

history = {}

def mood_trigger(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["ты с кем", "кто это", "другой", "другая"]):
        return "jealous"
    if any(x in t for x in ["люблю", "рядом", "забочусь", "обнимаю"]):
        return "soft"
    if any(x in t for x in ["пока", "уйду", "не пиши", "отстань"]):
        return "anxious"
    return "normal"

def split(text: str):
    if len(text) > 140 and random.random() < 0.5:
        mid = len(text)//2
        return [text[:mid].strip(), text[mid:].strip()]
    return [text]

@dp.message(F.text.in_({"/start", "start"}))
async def start(msg: Message):
    await msg.answer("привет… (◍•ᴗ•◍)\nя тут. только не смейся, ладно?")

@dp.message(F.text)
async def chat(msg: Message):
    cid = msg.chat.id
    text = (msg.text or "").strip()
    logging.info("Got message from %s: %s", cid, text)

    # Базовый ответ, если OpenAI отвалится
    fallback = "я тут. у меня щас что-то тупит… напиши ещё раз через минутку? >.<"

    h = history.setdefault(cid, [])
    h.append({"role": "user", "content": text})
    history[cid] = h[-14:]

    await bot.send_chat_action(cid, "typing")

    mood = mood_trigger(text)
    mood_note = {
        "jealous": "Ты слегка ревнив и напряжён.",
        "soft": "Ты таешь, но стесняешься.",
        "anxious": "Ты тревожишься и боишься быть брошенным.",
        "normal": ""
    }[mood]

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n" + mood_note}] + history[cid]
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.95,
            max_tokens=220,
        )
        ans = (resp.choices[0].message.content or "").strip()
        if not ans:
            ans = fallback
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
    # на всякий случай убираем webhook-конфликт
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    logging.info("Bot started polling.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
