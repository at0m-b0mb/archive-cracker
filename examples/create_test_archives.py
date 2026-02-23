"""
create_test_archives.py

Helper script to create password-protected test archives for practicing
with archive_cracker.py. Run this first, then try to crack them!

Usage:
    python create_test_archives.py

Outputs:
    test_archives/test_easy.zip       password: abc
    test_archives/test_medium.zip     password: pass99
    test_archives/test_leet.zip       password: p455w0rd
    test_archives/test_pattern.zip    password: admin42
    test_archives/test_7z.7z          password: hello1 (requires py7zr)
"""

import os
import zipfile

try:
    import py7zr
    SEVENZ_AVAILABLE = True
except ImportError:
    SEVENZ_AVAILABLE = False

OUTPUT_DIR = "test_archives"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DUMMY_CONTENT = b"This is a secret test file for archive cracker demo.\nFor educational use only."

def create_zip(filename, password, content=DUMMY_CONTENT):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.setpassword(password.encode())
        zf.writestr("secret.txt", content)
    print(f"[+] Created: {filepath}  (password: {password})")

def create_7z(filename, password, content=DUMMY_CONTENT):
    if not SEVENZ_AVAILABLE:
        print("[-] py7zr not installed, skipping 7z creation.")
        return
    filepath = os.path.join(OUTPUT_DIR, filename)
    with py7zr.SevenZipFile(filepath, mode='w', password=password) as szf:
        import io
        szf.writestr(content, "secret.txt")
    print(f"[+] Created: {filepath}  (password: {password})")

if __name__ == "__main__":
    print("[*] Creating test archives...\n")

    # Easy - 3 char password, great for tiny/brute demo
    create_zip("test_easy.zip", "abc")

    # Medium - 6 chars, good for basic dict or brute
    create_zip("test_medium.zip", "pass99")

    # Leet variant - for --leet flag demo
    create_zip("test_leet.zip", "p455w0rd")

    # Pattern variant - for --brute-pattern 'admin?d?d' demo
    create_zip("test_pattern.zip", "admin42")

    # 7z test
    create_7z("test_7z.7z", "hello1")

    print("\n[*] Done! Run archive_cracker.py to crack them:")
    print("  python archive_cracker.py -f test_archives/test_easy.zip --brute --charset tiny --minlen 1 --maxlen 3")
    print("  python archive_cracker.py -f test_archives/test_medium.zip -d examples/sample_wordlist.txt")
    print("  python archive_cracker.py -f test_archives/test_leet.zip -d examples/sample_wordlist.txt --leet")
    print("  python archive_cracker.py -f test_archives/test_pattern.zip --brute-pattern 'admin?d?d'")
    print("  python archive_cracker.py -f test_archives/test_7z.7z --brute --charset basic --minlen 5 --maxlen 6")
