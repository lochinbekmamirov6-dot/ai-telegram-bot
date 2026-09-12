import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiohttp import web
from openai import AsyncOpenAI

# Kalitlar Render Environment Variables bo'limidan olinadi
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TARGET_TOPIC_ID = 143  # AI Yordamchi mavzusining Topic ID si

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


@dp.message(F.message_thread_id == TARGET_TOPIC_ID)
async def handle_ai_topic(message: types.Message):
  if not message.text:
    return

  await bot.send_chat_action(message.chat.id, "typing")

  try:
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "Siz guruhdagi aqlli AI yordamchisiz. Berilgan"
                    " savollarga aniq javob bering."
                ),
            },
            {"role": "user", "content": message.text},
        ],
    )
    await message.reply(response.choices[0].message.content)
  except Exception as e:
    logging.error(f"Xatolik: {e}")


# Render portini tinglash uchun soxta server (Render to'xtatib qo'ymasligi uchun)
async def handle_ping(request):
  return web.Response(text="Bot active")


async def main():
  logging.basicConfig(level=logging.INFO)

  # Render portini ochish
  app = web.Application()
  app.router.add_get("/", handle_ping)
  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.getenv("PORT", 10000))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()

  # Bot polling
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
