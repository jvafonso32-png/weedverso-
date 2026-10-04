import pathlib
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
idx = html.find('function showPage')
print(html[idx:idx+500].encode('utf-8'))
