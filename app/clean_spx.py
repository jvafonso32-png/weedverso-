import pathlib, re
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
match = re.search(r'<div class="spx".*?<div id="accountFlowLegend"[^>]*></div>\s*</div>', html, re.DOTALL)
if match:
    new_html = html.replace(match.group(0), '<div id="accountFlowLegend"></div>')
    pathlib.Path('d:/weedverso/app/index.html').write_text(new_html, encoding='utf-8')
    print('Replaced spx')
else:
    print('Not found spx block')
