import pathlib
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
idx = html.find('id="investFormBox"')
print(html[idx-100:idx+900].encode('utf-8'))
