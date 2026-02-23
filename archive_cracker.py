import argparse
import os
import sys
import time
import threading
import re
import itertools
from concurrent.futures import ThreadPoolExecutor
import zipfile
import tarfile
try:
    import rarfile
    RAR_AVAILABLE = True
except ImportError:
    rarfile = None
    RAR_AVAILABLE = False
try:
    import py7zr
    SEVENZ_AVAILABLE = True
except ImportError:
    py7zr = None
    SEVENZ_AVAILABLE = False
try:
    import patoolib
    PATOOL_AVAILABLE = True
except ImportError:
    patoolib = None
    PATOOL_AVAILABLE = False

# Globals
found_lock = threading.Lock()
found_password = None

# Charset presets
CHARSETS = {
    'tiny': 'abc123',
    'basic': 'abcdefghijklmnopqrstuvwxyz0123456789',
    'full': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*',
    'keys': 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?',
    'leet': 'abcdefghijklmnopqrstuvwxyz01234567894e3i1o05sz'
}

MASK_CHARSETS = {
    '?l': 'abcdefghijklmnopqrstuvwxyz',
    '?u': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    '?d': '0123456789',
    '?s': '!@#$%^&*()_+-=[]{}|;:,.<>?',
    '?a': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?'  # all
}

LEET_REPLACE = {'a':'4', 'e':'3', 'i':'1', 'o':'0', 's':'5', 'z':'2'}

def generate_mask_passwords(mask):
    """Generate passwords from mask like ?l?l?d."""
    positions = []
    for char in mask:
        found_mask = False
        for m, cs in MASK_CHARSETS.items():
            if mask.startswith(m): # This is a bit simplified, but for a single char iteration
                pass
        # Correcting logic for multi-char mask keys
    # Simplified mask generator for the script
    i = 0
    while i < len(mask):
        if mask[i:i+2] in MASK_CHARSETS:
            positions.append(MASK_CHARSETS[mask[i:i+2]])
            i += 2
        else:
            positions.append(mask[i])
            i += 1
    return (''.join(combo) for combo in itertools.product(*positions))

def apply_pattern_mods(base_pwd, leet=False, pre='', app=''):
    """Apply prepend/append/leetspeak."""
    pwd = base_pwd
    if leet:
        pwd = ''.join(LEET_REPLACE.get(c.lower(), c) for c in pwd)
    return pre + pwd + app

def try_password(archive_path, password, output_dir, format_type):
    global found_password
    pwd_bytes = password.encode('utf-8')
    try:
        if format_type == 'zip':
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(path=output_dir, pwd=pwd_bytes)
        elif format_type == 'rar' and RAR_AVAILABLE:
            with rarfile.RarFile(archive_path) as rf:
                rf.extractall(path=output_dir, pwd=password)
        elif format_type == '7z' and SEVENZ_AVAILABLE:
            with py7zr.SevenZipFile(archive_path, password=password, mode='r') as szf:
                szf.extractall(path=output_dir)
        elif format_type in ['tar', 'gz', 'bz2', 'xz', 'patool']:
            if PATOOL_AVAILABLE:
                patoolib.extract_archive(archive_path, outdir=output_dir, password=password)
            else:
                return False
        else:
            return False
        with found_lock:
            found_password = password
        return True
    except:
        return False

def get_format(archive_path):
    ext = os.path.splitext(archive_path)[1].lower()
    mapping = {
        '.zip': 'zip', '.rar': 'rar', '.7z': '7z',
        '.tar': 'tar', '.tgz': 'tar', '.gz': 'gz',
        '.bz2': 'bz2', '.xz': 'xz'
    }
    return mapping.get(ext, 'patool')

def dict_attack(archive_path, wordlist_path, output_dir, threads, format_type, pre='', app='', leet=False):
    global found_password
    try:
        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            passwords = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f\"[-] Error reading wordlist: {e}\")
        return

    total = len(passwords)
    start_time = time.time()
    attempts = [0]
    
    def worker(start_idx):
        for i in range(start_idx, total, threads):
            if found_password: return
            pwd = apply_pattern_mods(passwords[i], leet, pre, app)
            attempts[0] += 1
            if try_password(archive_path, pwd, output_dir, format_type):
                print(f\"\
[+] FOUND: '{pwd}' (base: {passwords[i]}) | {attempts[0]} att | {time.time()-start_time:.1f}s\")
                return
            if attempts[0] % 500 == 0:
                rate = attempts[0] / max(time.time() - start_time, 1)
                print(f\"Dict: {attempts[0]}/{total} | Rate: {rate:.0f}/s | Current: {pwd}\", end='\\r')
    
    print(f\"[+] Dict attack: {total} words {'+leet' if leet else ''} {pre}+pwd+{app}\")
    with ThreadPoolExecutor(max_workers=threads) as executor:
        for t in range(threads):
            executor.submit(worker, t)

def advanced_brute_attack(archive_path, mode_params, output_dir, threads, format_type):
    global found_password
    start_time = time.time()
    attempts = [0]
    
    def worker(gen):
        for pwd in gen:
            if found_password: return
            full_pwd = apply_pattern_mods(pwd, mode_params['leet'], mode_params['pre'], mode_params['app'])
            attempts[0] += 1
            if try_password(archive_path, full_pwd, output_dir, format_type):
                print(f\"\
[+] FOUND: '{full_pwd}' | {attempts[0]} att | {time.time()-start_time:.1f}s\")
                return
            if attempts[0] % 1000 == 0:
                rate = attempts[0] / max(time.time() - start_time, 1)
                print(f\"Brute: {full_pwd} | Att: {attempts[0]:,} | Rate: {rate:.0f}/s\", end='\\r')
    
    print(\"[+] Advanced brute starting...\")
    gens = []
    
    if mode_params['mask']:
        gens.append(generate_mask_passwords(mode_params['mask']))
    elif mode_params['pattern']:
        pattern = mode_params['pattern'].replace('?', '?a')
        gens.append(generate_mask_passwords(pattern))
    else:
        charset = CHARSETS.get(mode_params['charset'], mode_params['charset'])
        for length in range(mode_params['minlen'], mode_params['maxlen'] + 1):
            gens.append((''.join(combo) for combo in itertools.product(charset, repeat=length)))
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        for gen in gens:
            executor.submit(worker, gen)
            if found_password: break

def main():
    parser = argparse.ArgumentParser(description=\"Advanced Ethical Archive Cracker\")
    parser.add_argument('-f', '--file', required=True, help=\"Protected archive path\")
    parser.add_argument('-d', '--dict', help=\"Wordlist file\")
    parser.add_argument('--brute', action='store_true', help=\"Enable classic brute-force\")
    parser.add_argument('--brute-mask', help=\"Mask: ?l?l?d?d\")
    parser.add_argument('--brute-pattern', help=\"Pattern: pass?d?!\")
    parser.add_argument('--charset', default='basic', help=\"tiny/basic/full/keys or custom string\")
    parser.add_argument('--minlen', type=int, default=1)
    parser.add_argument('--maxlen', type=int, default=4)
    parser.add_argument('--pre', default='', help=\"Prepend string\")
    parser.add_argument('--app', default='', help=\"Append string\")
    parser.add_argument('--leet', action='store_true', help=\"Leetspeak variants\")
    parser.add_argument('-t', '--threads', type=int, default=8)
    parser.add_argument('-o', '--output', default='./extracted')
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(\"[-] File missing!\")
        return 1
    
    format_type = get_format(args.file)
    print(f\"[+] Target: {format_type} | Output: {args.output} | Threads: {args.threads}\")
    
    if format_type == 'rar' and not RAR_AVAILABLE:
        print(\"[-] Dependency missing: pip install rarfile (requires unrar binary)\")
        return 1
    if format_type == '7z' and not SEVENZ_AVAILABLE:
        print(\"[-] Dependency missing: pip install py7zr\")
        return 1
    
    os.makedirs(args.output, exist_ok=True)
    
    mode_params = {
        'pre': args.pre, 'app': args.app, 'leet': args.leet,
        'charset': args.charset, 'minlen': args.minlen, 'maxlen': args.maxlen,
        'mask': args.brute_mask, 'pattern': args.brute_pattern
    }
    
    try:
        if args.dict:
            dict_attack(args.file, args.dict, args.output, args.threads, format_type, args.pre, args.app, args.leet)
        elif args.brute_mask or args.brute_pattern or args.brute:
            advanced_brute_attack(args.file, mode_params, args.output, args.threads, format_type)
        else:
            print(\"[-] No attack mode specified. Use --dict, --brute, --brute-mask, or --brute-pattern.\")
            return 1
    except KeyboardInterrupt:
        print(\"\
[!] Stopped by user.\")
        return 0
    
    if not found_password:
        print(\"\
[-] Password not found.\")
    return 0

if __name__ == \"__main__\":
    sys.exit(main())
