import asyncio
import logging
import os
import tempfile

import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from google import genai


# =========================
# ENV VARIABLES
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

TARGET_TOPIC_ID = 143

MODEL = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = """
Siz PVZ administratorlari uchun AI yordamchisiz.

Foydalanuvchiga o'zbek tilida tushunarli, qisqa va amaliy javob bering.

Agar foydalanuvchi:
- rasm yuborsa — rasmdagi ma'lumotni tahlil qiling;
- voice yuborsa — gapni tushunib, savolga javob bering;
- video yuborsa — videodagi holatni tahlil qiling;
- video note yuborsa — uni ham video sifatida tahlil qiling.

PVZ, Uzum Market, kompyuter, printer, scanner, terminal,
OPS va boshqa administratorlik masalalarida imkon qadar
amaliy yechim bering.

Agar ma'lumot yetarli bo'lmasa, aniq nimani yuborish kerakligini ayting.

Javobni o'zbek tilida bering.
"""


# =========================
# BOT
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

gemini = genai.Client(api_key=GEMINI_API_KEY)


# =========================
# TOPIC FILTER
# =========================

def allowed_message(message: types.Message) -> bool:

    # Private chatda ishlaydi
    if message.chat.type == "private":
        return True

    # Group / supergroup
    if message.chat.type in ["group", "supergroup"]:

        # Faqat 143-topic
        if message.message_thread_id != TARGET_TOPIC_ID:
            return False

        return True

    return False


# =========================
# GEMINI TEXT
# =========================

async def ask_gemini_text(text: str):

    def request():

        response = gemini.models.generate_content(
            model=MODEL,
            contents=text,
            config={
                "system_instruction": SYSTEM_PROMPT
            }
        )

        return response.text

    return await asyncio.to_thread(request)


# =========================
# GEMINI IMAGE
# =========================

async def ask_gemini_image(image_bytes: bytes, mime_type: str, prompt: str):

    def request():

        response = gemini.models.generate_content(
            model=MODEL,
            contents=[
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_bytes
                    }
                },
                prompt
            ],
            config={
                "system_instruction": SYSTEM_PROMPT
            }
        )

        return response.text

    return await asyncio.to_thread(request)


# =========================
# GEMINI FILE
# =========================

async def ask_gemini_file(file_path: str, prompt: str):

    def upload_and_request():

        # Gemini Files API'ga yuklash
        uploaded_file = gemini.files.upload(
            file=file_path
        )

        # Fayl tayyor bo'lishini kutish
        for _ in range(60):

            current_file = gemini.files.get(
                name=uploaded_file.name
            )

            # Video/audio processing tugagan bo'lsa
            if getattr(current_file, "state", None):

                state_name = getattr(
                    current_file.state,
                    "name",
                    str(current_file.state)
                )

                if state_name in ["ACTIVE", "STATE_ACTIVE"]:
                    uploaded_file = current_file
                    break

                if state_name in ["FAILED", "STATE_FAILED"]:
                    raise Exception("Gemini faylni qayta ishlay olmadi.")

            import time
            time.sleep(2)

        response = gemini.models.generate_content(
            model=MODEL,
            contents=[
                uploaded_file,
                prompt
            ],
            config={
                "system_instruction": SYSTEM_PROMPT
            }
        )

        return response.text

    return await asyncio.to_thread(upload_and_request)


# =========================
# TELEGRAM FILE DOWNLOAD
# =========================

async def download_telegram_file(file_id: str, suffix: str):

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    temp_file.close()

    await bot.download(
        file_id,
        destination=temp_file.name
    )

    return temp_file.name


# =========================
# TEXT
# =========================

@dp.message()
async def handle_message(message: types.Message):

    if not allowed_message(message):
        return

    # =====================
    # TEXT
    # =====================

    if message.text:

        await bot.send_chat_action(
            message.chat.id,
            "typing"
        )

        try:

            answer = await ask_gemini_text(
                message.text
            )

            await message.reply(answer)

        except Exception as e:

            logging.exception("Text AI error")

            await message.reply(
                f"❌ Xatolik:\n{e}"
            )

        return

    # =====================
    # PHOTO
    # =====================

    if message.photo:

        await bot.send_chat_action(
            message.chat.id,
            "upload_photo"
        )

        try:

            photo = message.photo[-1]

            file = await bot.get_file(
                photo.file_id
            )

            image_bytes = await bot.download_file(
                file.file_path
            )

            data = image_bytes.read()

            prompt = (
                message.caption
                if message.caption
                else
                "Rasmni tahlil qiling. "
                "Rasmda nima borligini va muammo bo'lsa "
                "uni qanday hal qilish mumkinligini tushuntiring."
            )

            answer = await ask_gemini_image(
                data,
                "image/jpeg",
                prompt
            )

            await message.reply(answer)

        except Exception as e:

            logging.exception("Photo AI error")

            await message.reply(
                f"❌ Rasmni tahlil qilishda xatolik:\n{e}"
            )

        return

    # =====================
    # VOICE
    # =====================

    if message.voice:

        await bot.send_chat_action(
            message.chat.id,
            "typing"
        )

        file_path = None

        try:

            file_path = await download_telegram_file(
                message.voice.file_id,
                ".ogg"
            )

            prompt = (
                "Bu Telegram voice xabarini tinglab, "
                "unda nima aytilganini tushuning va "
                "foydalanuvchining savoliga o'zbek tilida javob bering."
            )

            answer = await ask_gemini_file(
                file_path,
                prompt
            )

            await message.reply(answer)

        except Exception as e:

            logging.exception("Voice AI error")

            await message.reply(
                f"❌ Voice xabarni tahlil qilishda xatolik:\n{e}"
            )

        finally:

            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        return

    # =====================
    # VIDEO
    # =====================

    if message.video:

        await bot.send_chat_action(
            message.chat.id,
            "upload_video"
        )

        file_path = None

        try:

            file_path = await download_telegram_file(
                message.video.file_id,
                ".mp4"
            )

            prompt = (
                message.caption
                if message.caption
                else
                "Ushbu videoni batafsil tahlil qiling. "
                "Videoda nima sodir bo'layotganini tushuntiring "
                "va agar muammo ko'rsatilgan bo'lsa, "
                "uni hal qilish yo'lini ayting."
            )

            answer = await ask_gemini_file(
                file_path,
                prompt
            )
            await message.reply(answer)

        except Exception as e:

            logging.exception("Video AI error")

            await message.reply(
                f"❌ Videoni tahlil qilishda xatolik:\n{e}"
            )

        finally:

            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        return

    # =====================
    # VIDEO NOTE
    # =====================

    if message.video_note:

        await bot.send_chat_action(
            message.chat.id,
            "upload_video"
        )

        file_path = None

        try:

            file_path = await download_telegram_file(
                message.video_note.file_id,
                ".mp4"
            )

            prompt = (
                "Bu Telegram video note. "
                "Videoni ko'rib, undagi holatni tushuning. "
                "Agar foydalanuvchi muammoni ko'rsatayotgan bo'lsa, "
                "muammoni aniqlab, amaliy yechim bering."
            )

            answer = await ask_gemini_file(
                file_path,
                prompt
            )

            await message.reply(answer)

        except Exception as e:

            logging.exception("Video note AI error")

            await message.reply(
                f"❌ Video note'ni tahlil qilishda xatolik:\n{e}"
            )

        finally:

            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        return


# =========================
# RENDER HEALTH CHECK
# =========================

async def handle_ping(request):

    return web.Response(
        text="AI Helper 2.0 active"
    )


# =========================
# MAIN
# =========================

async def main():

    logging.basicConfig(
        level=logging.INFO
    )

    app = web.Application()

    app.router.add_get(
        "/",
        handle_ping
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(
        os.getenv("PORT", 10000)
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    logging.info(
        "AI Helper 2.0 ishga tushdi!"
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
