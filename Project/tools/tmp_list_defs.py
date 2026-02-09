import pathlib
path=pathlib.Path('main.py')
for i,line in enumerate(path.read_text().splitlines(),1):
    stripped=line.lstrip()
    if stripped.startswith('def '):
        print(f"{i}: {line.strip()}")
