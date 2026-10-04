import pathlib
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')

html = html.replace("document.getElementById('spxSplit')?.parentNode?.parentNode", "null")
html = html.replace('filter="url(#glow-${fillGradientId})"', '')
html = html.replace('style="stroke-dasharray: ${pathLength}; stroke-dashoffset: ${pathLength}; animation: svgDraw 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;"', 'style="animation: popIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; transform-origin: bottom;"')

pathlib.Path('d:/weedverso/app/index.html').write_text(html, encoding='utf-8')
print('Fixed!')
