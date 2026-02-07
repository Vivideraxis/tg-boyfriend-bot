import os, random, asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from openai import OpenAI

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

Если Таша заботится — тянись к ней.
Если холодна — закрывайся.
Если угроза потери — тревожься.
"""

history = {}
memory = {}

STICKERS = {
    "cute": [],
    "sad": [],
    "jealous": []
}

def mood_trigger(text):
    t = text.lower()
    if any(x in t for x in ["ты с кем", "кто это", "другой", "другая"]):
        return "jealous"
    if any(x in t for x in ["люблю", "рядом", "забочусь", "обнимаю"]):
        return "soft"
    if any(x in t for x in ["пока", "уйду", "не пиши", "отстань"]):
        return "anxious"
    return "normal"

def split(text):
    if len(text) > 140 and random.random() < 0.5:
        mid = len(text)//2
        return [text[:mid].strip(), text[mid:].strip()]
    return [text]

@dp.message(F.text)
async def chat(msg: Message):
    cid = msg.chat.id
    text = msg.text.strip()

    history.setdefault(cid, []).append({"role": "user", "content": text})
    history[cid] = history[cid][-14:]

    await bot.send_chat_action(cid, "typing")

    mood = mood_trigger(text)
    mood_note = {
        "jealous": "Ты слегка ревнив и напряжён.",
        "soft": "Ты таешь, но стесняешься.",
        "anxious": "Ты тревожишься и боишься быть брошенным.",
        "normal": ""
    }[mood]

    messages = [{"role": "system", "content": SYSTEM_PROMPT + mood_note}] + history[cid]

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.95,
        max_tokens=220,
    )

    ans = resp.choices[0].message.content.strip()

    for part in split(ans):
        await msg.answer(part)
        await asyncio.sleep(random.uniform(0.4, 0.9))

    history[cid].append({"role": "assistant", "content": ans})
    history[cid] = history[cid][-14:]

@dp.message(F.sticker)
async def on_sticker(msg: Message):
    await msg.answer("(◍•ᴗ•◍)")

async def main():
    await dp.start_polling(bot)

asyncio.run(main())
