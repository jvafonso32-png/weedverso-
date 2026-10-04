import pathlib
bot_path = pathlib.Path('d:/weedverso/app/telegram_bot.py')
text = bot_path.read_text(encoding='utf-8')
idx = text.find('def _route_message_impl')
print(text[idx:idx+900].encode('utf-8'))
