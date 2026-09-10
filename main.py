import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from openai import AsyncOpenAI

# Kalitlar va Topic ID
BOT_TOKEN = "8828352481:AAH6aKWWkV8Ty1f9_JjXTjPuGeooTTHO3Eg"
OPENAI_API_KEY = "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"
TARGET_TOPIC_ID = 143  # AI Yordamchi mavzusining To

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


@dp.message(F.message_thread_id == TARGET_TOPIC_ID)
async def handle_ai_topic(message: types.Message):
    if not message.text:
        return

    # Foydalanuvchiga bot yozayotganini ko'rsatish
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing",
        message_thread_id=TARGET_TOPIC_ID,
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Siz guruhdagi aqlli AI yordamchisiz. Berilgan savollarga aniq va xushmuomala javob bering.",
                },
                {"role": "user", "content": message.text},
            ],
        )

        reply_text = response.choices[0].message.content
        await message.reply(reply_text)

    except Exception as e:
        logging.error(f"Xatolik: {e}")


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name___ == "__main__":
    asyncio.run(main())
