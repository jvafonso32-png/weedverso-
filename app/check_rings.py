import pathlib, re
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
for m in re.finditer('ringCanvas', html):
    print(m.start(), html[max(0, m.start()-100):min(len(html), m.start()+50)])
