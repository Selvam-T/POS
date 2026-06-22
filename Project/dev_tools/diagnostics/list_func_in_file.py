import pathlib
project_root = pathlib.Path(__file__).resolve().parents[2]
# provide file path of file to list functions
cancel_file_path = project_root / 'modules' / 'sales' / 'view_hold.py'

print(cancel_file_path)
for i,line in enumerate(cancel_file_path.read_text().splitlines(),1):
    stripped=line.lstrip()
    if stripped.startswith('def '):
        print(f"{i}: {line.strip()}")
