import os
import asyncio
import threading
import aiofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import FOLDER_PATH, BOT_TOKEN
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command

# === Bot va Dispatcher ===
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

WATCHED_FILE = os.path.join(FOLDER_PATH, "chiqmadi.txt")
user_chat_id = None  # Foydalanuvchi chat_id ni /start orqali olamiz
sent_report_lines = set()  # 24 soatlik hisobot uchun unikal yozuvlar to‘plami

# === /start buyrug‘i ===
@dp.message(Command("start"))
async def start_command(message: Message):
    global user_chat_id
    user_chat_id = message.chat.id
    await message.answer("👋 Salom! Bot ishga tushdi. Sizga avtomatik xabarlar yuboriladi.")

# === /status buyrug‘i ===
@dp.message(Command("status"))
async def status_command(message: Message):
    if not os.path.exists(FOLDER_PATH):
        await message.answer("❗ FOLDER_PATH mavjud emas.")
        return

    files = os.listdir(FOLDER_PATH)
    txt_files = [f for f in files if f.endswith(".txt")]

    if not txt_files:
        await message.answer("📂 Hech qanday .txt fayl topilmadi.")
        return

    for f in txt_files:
        path = os.path.join(FOLDER_PATH, f)
        with open(path, "r", encoding="utf-8") as file:
            lines = set(line.strip() for line in file if line.strip())

        if not lines:
            await message.answer(f"<b>{f}</b> bo‘sh.")
        else:
            content = "\n".join(lines)
            max_length = 4000
            for i in range(0, len(content), max_length):
                await message.answer(f"<b>{f}:</b>\n<pre>{content[i:i+max_length]}</pre>")

# === /help buyrug‘i ===
@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = (
        "<b>Buyruqlar:</b>\n"
        "/start - Botni ishga tushirish\n"
        "/status - Fayllar va yozuvlar\n"
        "/help - Yordam"
    )
    await message.answer(help_text)

# === Faylga yozuv qo‘shilganda yuborish (realtime kuzatuv) ===
class KassirHandler(FileSystemEventHandler):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.processed_lines = set()

    def on_modified(self, event):
        if event.is_directory or os.path.normpath(event.src_path) != os.path.normpath(WATCHED_FILE):
            return

        try:
            with open(event.src_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = [line.strip() for line in lines if line.strip() and line.strip() not in self.processed_lines]
            for line in new_lines:
                self.processed_lines.add(line)

            if new_lines and user_chat_id:
                filename = os.path.basename(event.src_path)
                for line in new_lines:
                    msg = f"<b>[{filename}] yangi yozuv:</b>\n{line}"
                    asyncio.run_coroutine_threadsafe(send_message(msg), self.loop)

        except Exception as e:
            print(f"Xatolik: {e}")

# === Xabar yuboruvchi yordamchi funksiyasi ===
async def send_message(text):
    if user_chat_id:
        await bot.send_message(chat_id=user_chat_id, text=text)

# === Watchdog ishga tushiruvchi ===
def start_watchdog(path, loop):
    event_handler = KassirHandler(loop)
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)
    observer.start()
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# === 24 soatlik hisobotni unikal yozuvlar bilan yuborish ===
async def send_daily_report():
    global sent_report_lines
    while True:
        try:
            if os.path.exists(WATCHED_FILE) and user_chat_id:
                async with aiofiles.open(WATCHED_FILE, mode='r', encoding='utf-8') as f:
                    content = await f.readlines()

                # Takror yozuvlarni filterlaymiz
                new_unique_lines = [line.strip() for line in content if line.strip() and line.strip() not in sent_report_lines]

                if new_unique_lines:
                    combined_text = "\n".join(new_unique_lines)
                    max_length = 4000
                    for i in range(0, len(combined_text), max_length):
                        chunk = combined_text[i:i+max_length]
                        await bot.send_message(chat_id=user_chat_id, text=f"📄 <b>24 soatlik hisobot:</b>\n<pre>{chunk}</pre>")

                    # Hisobot yuborilganlarini eslab qolamiz
                    sent_report_lines.update(new_unique_lines)

                    # Faylni bo‘shatamiz
                    async with aiofiles.open(WATCHED_FILE, mode='w', encoding='utf-8') as f:
                        await f.write("")

        except Exception as e:
            if user_chat_id:
                await bot.send_message(chat_id=user_chat_id, text=f"❌ Xatolik yuz berdi:\n<code>{e}</code>")

        await asyncio.sleep(86400)  # Aslida 86400 (24 soat), test uchun 5 soniya

# === Bot ishga tushadigan asosiy funksiya ===
async def main():
    if not os.path.exists(FOLDER_PATH):
        print(f"Papka topilmadi, yaratilyapti: {FOLDER_PATH}")
        os.makedirs(FOLDER_PATH)

    if not os.path.exists(WATCHED_FILE):
        print(f"Fayl topilmadi, yaratilyapti: {WATCHED_FILE}")
        with open(WATCHED_FILE, "w", encoding="utf-8") as f:
            f.write("")

    asyncio.create_task(send_daily_report())

    loop = asyncio.get_event_loop()
    watcher_thread = threading.Thread(target=start_watchdog, args=(FOLDER_PATH, loop), daemon=True)
    watcher_thread.start()

    await dp.start_polling(bot)

# === Dastur ishga tushadi ===
if __name__ == "__main__":
    asyncio.run(main())
