import os, glob, json, sys

history_dir = os.path.expandvars(r'%APPDATA%\Code\User\History')
static_dir = r'c:\Users\asmit\Desktop\labhOffset\static'
restored = []

print("Searching in:", history_dir)

for e in glob.glob(os.path.join(history_dir, '*', 'entries.json')):
    try:
        data = json.load(open(e, 'r', encoding='utf-8'))
        res = data.get('resource', '')
        if 'labhOffset' in res and 'static' in res and res.endswith('.html'):
            print("Found HTML resource:", res)
            entries = data.get('entries', [])
            hash_dir = os.path.dirname(e)
            
            valid = []
            for b in entries:
                b_path = os.path.join(hash_dir, b['id'])
                if os.path.exists(b_path) and os.path.getsize(b_path) > 0:
                    valid.append((b_path, os.path.getmtime(b_path)))
            
            if valid:
                latest = max(valid, key=lambda x: x[1])[0]
                filename = os.path.basename(res)
                restored.append((filename, latest))
                print(f"-> Best backup for {filename}: {latest}")
    except Exception as ex:
        pass

for name, backup in restored:
    dest = os.path.join(static_dir, name)
    try:
        content = open(backup, 'r', encoding='utf-8').read()
        open(dest, 'w', encoding='utf-8').write(content)
        print(f"Restored {name}!")
    except Exception as ex:
        print(f"Failed to restore {name}: {ex}")
