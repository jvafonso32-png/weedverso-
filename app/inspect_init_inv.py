import pathlib
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
idx = html.find('function initInvestBindings()')
print(html[idx:idx+1500].encode('utf-8'))
