import pathlib
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
idx = html.find('function save(')
print(html[idx:idx+400].encode('utf-8'))
