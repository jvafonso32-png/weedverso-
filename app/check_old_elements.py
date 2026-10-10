import pathlib, re

html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')

elements = ['el.hist', 'el.foodStmt', 'el.ccHistory', 'el.last5Stmt', 'el.goalStmt', 'el.routineChart']

for el_name in elements:
    matches = [m.start() for m in re.finditer(re.escape(el_name), html)]
    print(f"{el_name}: {len(matches)} occurrences")
    for m in matches[:3]:
        print(" ", html[m:m+100])
