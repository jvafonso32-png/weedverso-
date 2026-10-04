import pathlib
bot_path = pathlib.Path('d:/weedverso/app/telegram_bot.py')
text = bot_path.read_text(encoding='utf-8')
lines = text.splitlines()
print('\n'.join(lines[981:1010]))
