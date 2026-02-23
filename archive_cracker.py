import argparse
import itertools
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
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

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global result holder (set once by the winning thread)
# ---------------------------------------------------------------------------
_found_lock = threading.Lock()
found_password = None

# ---------------------------------------------------------------------------
# Charset / mask presets
# ---------------------------------------------------------------------------
CHARSETS = {
    'tiny':  'abc123',
    'basic': 'abcdefghijklmnopqrstuvwxyz0123456789',
    'full':  'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*',
    'keys':  'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?',
    'leet':  'abcdefghijklmnopqrstuvwxyz01234567894e3i1o05sz',
}

MASK_CHARSETS = {
    '?l': 'abcdefghijklmnopqrstuvwxyz',
    '?u': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    '?d': '0123456789',
    '?s': '!@#$%^&*()_+-=[]{}|;:,.<>?',
    '?a': ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
           '0123456789!@#$%^&*()_+-=[]{}|;:,.<>?'),
}

LEET_REPLACE = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 'z': '2'}

# hashcat mode IDs for supported formats
HASHCAT_MODES = {
    'zip': '13600',
    'rar': '13000',
    '7z':  '11600',
}


# ---------------------------------------------------------------------------
# Password generation helpers
# ---------------------------------------------------------------------------

def generate_mask_passwords(mask):
    """Yield passwords from a hashcat-style mask such as ``?l?l?d?d``."""
    positions = []
    i = 0
    while i < len(mask):
        token = mask[i:i + 2]
        if token in MASK_CHARSETS:
            positions.append(MASK_CHARSETS[token])
            i += 2
        else:
            positions.append(mask[i])
            i += 1
    return (''.join(combo) for combo in itertools.product(*positions))


def apply_pattern_mods(base_pwd, leet=False, pre='', app=''):
    """Return *base_pwd* with optional prepend, append, and leetspeak transforms."""
    pwd = base_pwd
    if leet:
        pwd = ''.join(LEET_REPLACE.get(c.lower(), c) for c in pwd)
    return pre + pwd + app


# ---------------------------------------------------------------------------
# Core extraction attempt
# ---------------------------------------------------------------------------

def try_password(archive_path, password, output_dir, format_type):
    """Try *password* against *archive_path*. Returns ``True`` on success."""
    global found_password
    try:
        if format_type == 'zip':
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(path=output_dir, pwd=password.encode('utf-8'))
        elif format_type == 'rar':
            if not RAR_AVAILABLE:
                return False
            with rarfile.RarFile(archive_path) as rf:
                rf.extractall(path=output_dir, pwd=password)
        elif format_type == '7z':
            if not SEVENZ_AVAILABLE:
                return False
            with py7zr.SevenZipFile(archive_path, password=password, mode='r') as szf:
                szf.extractall(path=output_dir)
        elif format_type in ('tar', 'gz', 'bz2', 'xz', 'patool'):
            if not PATOOL_AVAILABLE:
                return False
            patoolib.extract_archive(archive_path, outdir=output_dir, password=password)
        else:
            return False

        with _found_lock:
            found_password = password
        return True

    except (RuntimeError, zipfile.BadZipFile, ValueError, KeyError, OSError):
        return False
    except Exception:  # noqa: BLE001 - catch-all so one bad attempt never kills a thread
        return False


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def get_format(archive_path):
    """Return a short format tag based on the file extension."""
    ext = os.path.splitext(archive_path)[1].lower()
    mapping = {
        '.zip': 'zip', '.rar': 'rar', '.7z': '7z',
        '.tar': 'tar', '.tgz': 'tar', '.gz':  'gz',
        '.bz2': 'bz2', '.xz':  'xz',
    }
    return mapping.get(ext, 'patool')


# ---------------------------------------------------------------------------
# Attack modes – CPU
# ---------------------------------------------------------------------------

def dict_attack(archive_path, wordlist_path, output_dir, threads,
                format_type, pre='', app='', leet=False):
    """Dictionary attack: try every word in *wordlist_path*."""
    global found_password

    try:
        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as fh:
            passwords = [line.strip() for line in fh if line.strip()]
    except OSError as exc:
        log.error('[-] Cannot read wordlist: %s', exc)
        return

    total = len(passwords)
    start_time = time.time()
    counter = [0]
    counter_lock = threading.Lock()
    mods = '+leet' if leet else ''
    log.info('[+] Dict attack: %d words %s pre=%r app=%r', total, mods, pre, app)

    def worker(start_idx):
        for i in range(start_idx, total, threads):
            if found_password:
                return
            pwd = apply_pattern_mods(passwords[i], leet, pre, app)
            with counter_lock:
                counter[0] += 1
                current = counter[0]
            if try_password(archive_path, pwd, output_dir, format_type):
                elapsed = time.time() - start_time
                log.info('\n[+] FOUND: %r  (base: %s) | %d attempts | %.1fs',
                         pwd, passwords[i], current, elapsed)
                return
            if current % 500 == 0:
                rate = current / max(time.time() - start_time, 1)
                print(f'Dict: {current}/{total} | {rate:.0f}/s | {pwd}',
                      end='\r', flush=True)

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(worker, t) for t in range(threads)]
        for fut in futures:
            fut.result()


def advanced_brute_attack(archive_path, mode_params, output_dir, threads, format_type):
    """Brute-force attack driven by mask, pattern, or charset + length range."""
    global found_password

    start_time = time.time()
    counter = [0]
    counter_lock = threading.Lock()

    def worker(gen):
        for pwd in gen:
            if found_password:
                return
            full_pwd = apply_pattern_mods(
                pwd, mode_params['leet'], mode_params['pre'], mode_params['app']
            )
            with counter_lock:
                counter[0] += 1
                current = counter[0]
            if try_password(archive_path, full_pwd, output_dir, format_type):
                elapsed = time.time() - start_time
                log.info('\n[+] FOUND: %r | %d attempts | %.1fs',
                         full_pwd, current, elapsed)
                return
            if current % 1000 == 0:
                rate = current / max(time.time() - start_time, 1)
                print(f'Brute: {full_pwd} | Att: {current:,} | {rate:.0f}/s',
                      end='\r', flush=True)

    log.info('[+] Advanced brute-force starting...')
    gens = []

    if mode_params['mask']:
        gens.append(generate_mask_passwords(mode_params['mask']))
    elif mode_params['pattern']:
        expanded = mode_params['pattern'].replace('?', '?a')
        gens.append(generate_mask_passwords(expanded))
    else:
        charset = CHARSETS.get(mode_params['charset'], mode_params['charset'])
        for length in range(mode_params['minlen'], mode_params['maxlen'] + 1):
            gens.append(
                (''.join(combo) for combo in itertools.product(charset, repeat=length))
            )

    with ThreadPoolExecutor(max_workers=threads) as executor:
        for gen in gens:
            if found_password:
                break
            executor.submit(worker, gen).result()


# ---------------------------------------------------------------------------
# Attack mode – GPU (hashcat backend)
# ---------------------------------------------------------------------------

def gpu_attack(archive_path, mode_params, wordlist_path, format_type, verbose=False):
    """
    GPU-accelerated attack via `hashcat`.

    Requires `hashcat` to be installed and available in PATH.
    Supported archive formats: ZIP (mode 13600), RAR (mode 13000), 7z (mode 11600).

    Returns ``True`` if the password was found, ``False`` otherwise.
    """
    global found_password

    if format_type not in HASHCAT_MODES:
        log.error('[-] GPU mode is not supported for format %r.', format_type)
        log.error('    Supported formats: %s', ', '.join(HASHCAT_MODES))
        return False

    hashcat_bin = shutil.which('hashcat')
    if not hashcat_bin:
        log.error('[-] hashcat not found in PATH. Install it to use --gpu.')
        log.error('    Download: https://hashcat.net/hashcat/')
        return False

    mode = HASHCAT_MODES[format_type]

    # Use a temporary potfile so we can read cracked passwords without
    # polluting the user's global hashcat potfile.
    pot_fd, pot_path = tempfile.mkstemp(suffix='.pot')
    os.close(pot_fd)

    try:
        cmd = [
            hashcat_bin,
            '-m', mode,
            archive_path,
            '--potfile-path', pot_path,
            '--quiet',
        ]

        if wordlist_path:
            cmd += ['-a', '0', wordlist_path]
            log.info('[+] GPU dictionary attack via hashcat (mode %s)...', mode)
        elif mode_params.get('mask'):
            cmd += ['-a', '3', mode_params['mask']]
            log.info('[+] GPU mask attack via hashcat (mode %s, mask: %s)...',
                     mode, mode_params['mask'])
        else:
            minlen = mode_params.get('minlen', 1)
            maxlen = mode_params.get('maxlen', 4)
            cmd += [
                '-a', '3', '?a' * maxlen,
                '--increment',
                '--increment-min', str(minlen),
                '--increment-max', str(maxlen),
            ]
            log.info('[+] GPU brute-force via hashcat (mode %s, len %d-%d)...',
                     mode, minlen, maxlen)

        log.debug('[dbg] Running: %s', ' '.join(cmd))

        # In verbose mode let hashcat print to the terminal; otherwise suppress
        # its stdout so our progress messages stay readable.
        stdout = None if verbose else subprocess.DEVNULL
        stderr = None if verbose else subprocess.PIPE
        try:
            result = subprocess.run(cmd, check=False, stdout=stdout, stderr=stderr)
            if result and result.returncode not in (0, 1) and result.stderr:
                log.debug('[dbg] hashcat stderr: %s', result.stderr.decode(errors='replace')[:300])
        except OSError as exc:
            log.error('[-] Failed to launch hashcat: %s', exc)
            return False

        # Parse the potfile for the cracked password
        try:
            with open(pot_path, 'r', encoding='utf-8', errors='ignore') as pf:
                for line in pf:
                    line = line.strip()
                    if ':' in line:
                        password = line.split(':', 1)[-1]
                        log.info('[+] GPU FOUND: %r', password)
                        with _found_lock:
                            found_password = password
                        return True
        except OSError as exc:
            log.error('[-] Could not read hashcat potfile: %s', exc)
            return False

        log.info('[-] hashcat did not find the password.')
        return False

    finally:
        try:
            os.unlink(pot_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Advanced Ethical Archive Password Cracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  %(prog)s -f secret.zip -d rockyou.txt -t 16\n'
            '  %(prog)s -f vault.7z --brute --charset basic --minlen 4 --maxlen 6\n'
            '  %(prog)s -f data.rar --brute-mask "?l?l?d?d" -t 16\n'
            '  %(prog)s -f data.rar --brute-mask "?l?l?d?d" --gpu\n'
        ),
    )

    parser.add_argument('-f', '--file', required=True,
                        help='Path to the password-protected archive')
    parser.add_argument('-d', '--dict', metavar='WORDLIST',
                        help='Wordlist file for dictionary attack')
    parser.add_argument('--brute', action='store_true',
                        help='Enable classic charset brute-force')
    parser.add_argument('--brute-mask', metavar='MASK',
                        help='Hashcat-style mask, e.g. ?l?l?d?d')
    parser.add_argument('--brute-pattern', metavar='PATTERN',
                        help='Known partial pattern, e.g. admin?d?d')
    parser.add_argument('--charset', default='basic', metavar='PRESET',
                        help='Charset preset: tiny/basic/full/keys or custom string (default: basic)')
    parser.add_argument('--minlen', type=int, default=1, metavar='N',
                        help='Minimum password length for brute-force (default: 1)')
    parser.add_argument('--maxlen', type=int, default=4, metavar='N',
                        help='Maximum password length for brute-force (default: 4)')
    parser.add_argument('--pre', default='', metavar='STRING',
                        help='String to prepend to every candidate')
    parser.add_argument('--app', default='', metavar='STRING',
                        help='String to append to every candidate')
    parser.add_argument('--leet', action='store_true',
                        help='Apply leetspeak substitutions (a=4, e=3, i=1, o=0, s=5, z=2)')
    parser.add_argument('-t', '--threads', type=int, default=8, metavar='N',
                        help='Number of CPU threads (default: 8)')
    parser.add_argument('-o', '--output', default='./extracted', metavar='DIR',
                        help='Directory to extract archive into on success (default: ./extracted)')
    parser.add_argument('--gpu', action='store_true',
                        help='Use GPU acceleration via hashcat (requires hashcat in PATH). '
                             'Supported formats: ZIP, RAR, 7z.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose/debug output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # --- Validate inputs -------------------------------------------------------
    if not os.path.isfile(args.file):
        log.error('[-] Archive not found: %s', args.file)
        return 1

    if args.minlen < 1:
        log.error('[-] --minlen must be >= 1')
        return 1

    if args.maxlen < args.minlen:
        log.error('[-] --maxlen must be >= --minlen')
        return 1

    if args.threads < 1:
        log.error('[-] --threads must be >= 1')
        return 1

    format_type = get_format(args.file)

    if format_type == 'rar' and not RAR_AVAILABLE:
        log.error('[-] Missing dependency for RAR: pip install rarfile  '
                  '(also requires: apt install unrar)')
        return 1

    if format_type == '7z' and not SEVENZ_AVAILABLE:
        log.error('[-] Missing dependency for 7z: pip install py7zr')
        return 1

    if not (args.dict or args.brute or args.brute_mask or args.brute_pattern):
        log.error('[-] No attack mode specified. Use --dict, --brute, '
                  '--brute-mask, or --brute-pattern.')
        parser.print_help()
        return 1

    gpu_tag = ' | GPU: hashcat' if args.gpu else ''
    log.info('[+] Target: %s (%s) | Output: %s | Threads: %d%s',
             args.file, format_type.upper(), args.output, args.threads, gpu_tag)

    os.makedirs(args.output, exist_ok=True)

    mode_params = {
        'pre':     args.pre,
        'app':     args.app,
        'leet':    args.leet,
        'charset': args.charset,
        'minlen':  args.minlen,
        'maxlen':  args.maxlen,
        'mask':    args.brute_mask,
        'pattern': args.brute_pattern,
    }

    try:
        if args.gpu:
            wordlist = args.dict if args.dict else None
            gpu_attack(args.file, mode_params, wordlist, format_type, verbose=args.verbose)
        elif args.dict:
            dict_attack(args.file, args.dict, args.output, args.threads,
                        format_type, args.pre, args.app, args.leet)
        else:
            advanced_brute_attack(args.file, mode_params, args.output,
                                  args.threads, format_type)
    except KeyboardInterrupt:
        log.info('\n[!] Interrupted by user.')
        return 0

    if found_password:
        log.info('[+] Password: %r', found_password)
        log.info('[+] Extracted to: %s', args.output)
        return 0

    log.info('[-] Password not found.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
