import os
import glob

static_dir = r"c:\Users\asmit\Desktop\labhOffset\static"
html_files = glob.glob(os.path.join(static_dir, "*.html"))

target_str = """        Settings
      </a>"""

replacement_str = """        Settings
      </a>
      <a href="backups.html" class="menu-item">
        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24" style="margin-right: 12px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
        System Backups
      </a>"""

for file_path in html_files:
    if os.path.basename(file_path) in ["index.html", "backups.html", "login.html"]:
        continue
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if target_str in content and "backups.html" not in content:
        new_content = content.replace(target_str, replacement_str)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {os.path.basename(file_path)}")
