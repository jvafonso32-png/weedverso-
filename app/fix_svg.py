import pathlib, re
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')

# Fix SVG namespace and animation
html = html.replace('<svg class="ft-chart-svg"', '<svg class="ft-chart-svg" xmlns="http://www.w3.org/2000/svg"')
html = html.replace('style="animation: popIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; transform-origin: bottom;"', '')

# Bump versions again
html = re.sub(r'v9\.\d+</span>', 'v9.9</span>', html)
pathlib.Path('d:/weedverso/app/index.html').write_text(html, encoding='utf-8')

sw_path = pathlib.Path('d:/weedverso/app/sw.js')
sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(r'weedverso-v\d+', 'weedverso-v20', sw)
sw_path.write_text(sw, encoding='utf-8')

print('Fixed SVG paths and bumped to v20')
