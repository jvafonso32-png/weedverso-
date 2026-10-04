import pathlib
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
idx = html.find('function renderHero()')
print(html[idx+800:idx+1600].encode('utf-8'))
