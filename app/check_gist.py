import pathlib
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
idx = html.find("fetch('https://api.github.com")
print(html[idx-300:idx+300].encode('utf-8'))
