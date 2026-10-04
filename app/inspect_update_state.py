import pathlib
bot_path = pathlib.Path('d:/weedverso/app/telegram_bot.py')
text = bot_path.read_text(encoding='utf-8')
idx = text.find('def update_state')
if idx == -1:
    idx = text.find('save_state')
print(text[idx:idx+600].encode('utf-8'))
