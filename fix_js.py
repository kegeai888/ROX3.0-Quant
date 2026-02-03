
import os

file_path = '/Users/mac/Documents/trae_projects/word/app/static/js/main.js'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for trailing backtick or garbage
    content = content.strip()
    
    if content.endswith('`'):
        print("Found trailing backtick. Removing...")
        content = content[:-1].strip()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed.")
    else:
        print("No trailing backtick found.")
        # Check end of file
        print(f"Last 20 chars: {repr(content[-20:])}")

except Exception as e:
    print(f"Error: {e}")
