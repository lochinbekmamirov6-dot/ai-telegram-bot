import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiohttp import web
from groq import AsyncGroq

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TARGET_TOPIC_ID = 143

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncGroq(api_key=GROQ_API_KEY)


@dp.message()
async def handle_ai_message(message: types.Message):
  if not message.text:
    return

  if (
      message.chat.type in ["group", "supergroup"]
      and message.message_thread_id != TARGET_TOPIC_ID
  ):
    return

  await bot.send_chat_action(message.chat.id, "typing")

  try:
    response = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "Siz aqlli va xushmuomala AI yordamchisiz.",
            },
            {"role": "user", "content": message.text},
        ],
    )
    await message.reply(response.choices[0].message.content)
  except Exception as e:
    # Xatolik yuz bersa, sababini to'g'ridan-to me telegramga yuboradi
    await message.reply(f"Xatolik yuz berdi:\n{e}", parse_mode="Markdown")


async def handle_ping(request):
  return web.Response(text="Bot active")


async def main():
  logging.basicConfig(level=logging.INFO)

  app = web.Application()
  app.router.add_get("/", handle_ping)
  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.getenv("PORT", 10000))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()

  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
