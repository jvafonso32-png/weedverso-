import os
import threading
import time

from api_server import run_server
from env_loader import load_env_file


def main():
    load_env_file()
    api_thread = threading.Thread(target=run_server, daemon=True, name="weedverso-api")
    api_thread.start()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        from telegram_bot import run_bot

        bot_thread = threading.Thread(target=run_bot, daemon=True, name="weedverso-bot")
        bot_thread.start()
        print("Bot Telegram habilitado.")
    else:
        print("TELEGRAM_BOT_TOKEN nao definido. API web ativa sem bot.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando Weedverso.")


if __name__ == "__main__":
    main()
