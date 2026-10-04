import pathlib
bot_path = pathlib.Path('d:/weedverso/app/telegram_bot.py')
text = bot_path.read_text(encoding='utf-8')
idx = text.find('build_balance_summary')
if idx == -1:
    idx = text.find('Saldos')
print(text[idx:idx+800].encode('utf-8'))
