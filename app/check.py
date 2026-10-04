import pathlib
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
idx = html.find('id="accountFlowLegend"')
print('Found at', idx)
start = max(0, idx - 200)
end = min(len(html), idx + 200)
print(html[start:end])
