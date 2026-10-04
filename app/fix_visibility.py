import pathlib
import re

html_path = pathlib.Path('d:/weedverso/app/index.html')
html = html_path.read_text(encoding='utf-8')

# Find where we set el.ccDescChart.style.display = 'none' and add hiding for its parent
js_to_add = "if(el.ccDescChart && el.ccDescChart.parentNode) el.ccDescChart.parentNode.style.display = 'none';"
html = html.replace("if(el.ccDescChart) el.ccDescChart.style.display = 'none';", js_to_add)

# Bump versions again
html = re.sub(r'v9\.\d+</span>', 'v9.10</span>', html)
html_path.write_text(html, encoding='utf-8')

sw_path = pathlib.Path('d:/weedverso/app/sw.js')
sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(r'weedverso-v\d+', 'weedverso-v21', sw)
sw_path.write_text(sw, encoding='utf-8')

print('Fixed chartShell visibility and bumped to v21')
