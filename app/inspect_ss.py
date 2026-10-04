import pathlib
ss_path = pathlib.Path('d:/weedverso/app/shared_state.py')
text = ss_path.read_text(encoding='utf-8')
lines = [l for l in text.splitlines() if 'def ' in l]
print('\n'.join(lines))
