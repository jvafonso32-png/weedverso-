import pathlib, re
html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')
# Remove any remaining filter attribute
html = re.sub(r'filter="url\(#glow-[^"]+"\)', '', html)
# Remove the <filter> definition
html = re.sub(r'<filter id="glow-[^>]+>.*?</filter>', '', html, flags=re.DOTALL)
pathlib.Path('d:/weedverso/app/index.html').write_text(html, encoding='utf-8')
print('Removed filter tags')
