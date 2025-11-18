"""Quick fix for import errors in auth.py"""
import sys

# Read auth.py
with open('auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the oauth import - comment it out since OAuth is in app.py
content = content.replace(
    'import oauth  # your OAuth client configured in src/oauth.py (keep as-is)',
    '# import oauth  # OAuth is handled in app.py, not needed here'
)

# Save
with open('auth.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed auth.py imports")
