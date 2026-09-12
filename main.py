import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiohttp import web


BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

TARGET_TOPIC_ID = 143

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message()
async def handle_ai_message(message: types.Message):
    if not message.text:
        return

    # Faqat kerakli topicda ishlasin
    if (
        message.chat.type in ["group", "supergroup"]
        and message.message_thread_id != TARGET_TOPIC_ID
    ):
        return

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/gemini-3.5-flash-lite:generateContent"
        )

        params = {
            "key": GEMINI_API_KEY
        }

        data = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": "Siz aqlli va xushmuomala AI yordamchisiz. "
                                "Foydalanuvchiga o'zbek tilida tushunarli javob bering."
                    }
                ]
            },
            "contents": [
                {
                    "parts": [
                        {
                            "text": message.text
                        }
                    ]
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                params=params,
                json=data
            ) as response:

                result = await response.json()

                if response.status != 200:
                    error_message = result.get(
                        "error",
                        {}
                    ).get(
                        "message",
                        "Noma'lum Gemini xatosi"
                    )

                    await message.reply(
                        f"Gemini xatosi:\n{error_message}"
                    )
                    return

        answer = result["candidates"][0]["content"]["parts"][0]["text"]

        await message.reply(answer)

    except Exception as e:
        logging.exception("AI xatosi")

        await message.reply(
            f"Xatolik yuz berdi:\n{e}"
        )


async def handle_ping(request):
    return web.Response(text="Bot active")


async def main():
    logging.basicConfig(level=logging.INFO)

    app = web.Application()
    app.router.add_get("/", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
