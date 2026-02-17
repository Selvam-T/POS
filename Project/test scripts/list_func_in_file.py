import pathlib
current_dir = pathlib.Path(__file__).resolve().parent
# provide file path of file to list functions
cancel_file_path = current_dir.parent / 'modules' / 'payment' / 'payment_panel.py'

print(cancel_file_path)
for i,line in enumerate(cancel_file_path.read_text().splitlines(),1):
    stripped=line.lstrip()
    if stripped.startswith('def '):
        print(f"{i}: {line.strip()}")
