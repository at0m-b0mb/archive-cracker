# Archive Cracker

![Python](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20Mac-lightgrey)
![Purpose](https://img.shields.io/badge/purpose-Ethical%20Hacking-red)

An advanced multi-format **archive password cracker** for educational and ethical hacking purposes. Built for cybersecurity coursework covering ZIP attacks, dictionary attacks, and brute-force techniques.

> **Disclaimer:** This tool is strictly for educational use and authorized security testing. Only use on archives you own or have explicit permission to test. Unauthorized use is illegal.

---

## Features

- **Multi-format support**: ZIP, RAR, 7Z, TAR, TAR.GZ, TAR.BZ2, TAR.XZ + patool fallback
- **Dictionary attack**: Load any wordlist (e.g. rockyou.txt)
- **Pure brute-force**: Custom charset and length range
- **Mask attack**: Hashcat-style masks (`?l?l?d?d` = aabb00)
- **Pattern attack**: Known partial passwords (`pass?d?d` = pass12)
- **Leetspeak**: Auto-generates leet variants (a=4, e=3, i=1, o=0, s=5, z=2)
- **Prepend / Append**: Add known prefixes/suffixes to every candidate
- **Multi-threading**: Configurable thread count for speed
- **GPU acceleration** *(optional)*: `--gpu` flag delegates to `hashcat` for GPU-powered cracking
- **Progress tracking**: Live rate (attempts/sec), current candidate, elapsed time
- **Verbose mode**: `--verbose` / `-v` for debug-level output
- **Graceful exit**: Ctrl+C stops cleanly, reports last tried password
- **Auto-extract**: Extracts archive to output dir on success

---

## Supported Formats

| Format       | Extension(s)          | Library           | Notes                        |
|--------------|-----------------------|-------------------|------------------------------|
| ZIP          | `.zip`                | `zipfile` (stdlib)| Full AES/ZipCrypto support   |
| RAR          | `.rar`                | `rarfile`         | Requires `unrar` binary      |
| 7-Zip        | `.7z`                 | `py7zr`           | AES-256 encryption           |
| TAR          | `.tar`, `.tgz`        | `tarfile` (stdlib)| GNU extension passwords      |
| GZIP TAR     | `.tar.gz`, `.tgz`     | `tarfile` (stdlib)| Compressed + password        |
| BZIP2 TAR    | `.tar.bz2`            | `tarfile` (stdlib)| Compressed + password        |
| XZ TAR       | `.tar.xz`             | `tarfile` (stdlib)| LZMA + password              |
| Others (CAB) | Various               | `patool`          | Requires CLI helpers         |

---

## Installation

### 1. Clone the repo
```bash
git clone https://github.com/at0m-b0mb/archive-cracker.git
cd archive-cracker
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Install system dependencies (Kali/Debian)
```bash
# For RAR support
sudo apt install unrar

# For patool extended format support
sudo apt install p7zip-full bzip2 xz-utils
```

---

## Usage

```
python archive_cracker.py -f <archive> [OPTIONS]
```

### Arguments

| Argument          | Description                                          | Default      |
|-------------------|------------------------------------------------------|--------------|
| `-f, --file`      | Path to the password-protected archive (required)    | -            |
| `-d, --dict`      | Path to wordlist file for dictionary attack          | -            |
| `--brute`         | Enable classic charset brute-force                   | -            |
| `--brute-mask`    | Hashcat-style mask e.g. `?l?l?d?d`                  | -            |
| `--brute-pattern` | Known pattern e.g. `admin?d?d`                       | -            |
| `--charset`       | Charset preset: `tiny/basic/full/keys` or custom str | `basic`      |
| `--minlen`        | Minimum password length for brute-force              | `1`          |
| `--maxlen`        | Maximum password length for brute-force              | `4`          |
| `--pre`           | String to prepend to every candidate                 | `''`         |
| `--app`           | String to append to every candidate                  | `''`         |
| `--leet`          | Apply leetspeak substitutions (a=4, e=3...)          | `False`      |
| `-t, --threads`   | Number of threads                                    | `8`          |
| `-o, --output`    | Directory to extract to on success                   | `./extracted`|
| `--gpu`           | GPU acceleration via `hashcat` (ZIP/RAR/7z only)    | `False`      |
| `-v, --verbose`   | Enable verbose/debug output                          | `False`      |

---

## Mask Charset Reference

| Mask Token | Characters Matched                        |
|------------|-------------------------------------------|
| `?l`       | Lowercase letters `a-z`                   |
| `?u`       | Uppercase letters `A-Z`                   |
| `?d`       | Digits `0-9`                              |
| `?s`       | Special chars `!@#$%^&*()_+-=[]{}...`     |
| `?a`       | All of the above combined                 |

---

## Examples

### Dictionary attack on a ZIP file
```bash
python archive_cracker.py -f secret.zip -d /usr/share/wordlists/rockyou.txt -t 16
```

### Dictionary attack with leet substitutions + append year
```bash
python archive_cracker.py -f secret.zip -d wordlist.txt --leet --app 2024
```

### Brute-force a 7Z (4-char alphanumeric)
```bash
python archive_cracker.py -f vault.7z --brute --charset basic --minlen 4 --maxlen 4 -t 8
```

### Mask attack (2 lowercase + 2 digits pattern)
```bash
python archive_cracker.py -f data.rar --brute-mask '?l?l?d?d' -t 16
```

### Pattern attack (know it starts with 'admin')
```bash
python archive_cracker.py -f backup.zip --brute-pattern 'admin?d?d' -o ./out
```

### Prepend + Append (know format is user_PASS_2024)
```bash
python archive_cracker.py -f file.7z --brute --charset basic --minlen 4 --maxlen 6 --pre user_ --app _2024
```

### Full charset brute on RAR
```bash
python archive_cracker.py -f archive.rar --brute --charset full --minlen 1 --maxlen 5 -t 16 -o ./results
```

### GPU-accelerated dictionary attack (requires hashcat)
```bash
python archive_cracker.py -f secret.zip -d rockyou.txt --gpu
```

### GPU-accelerated mask attack
```bash
python archive_cracker.py -f data.rar --brute-mask '?l?l?d?d' --gpu
```

---

## GPU Acceleration

Pass `--gpu` to delegate the cracking job to [hashcat](https://hashcat.net/hashcat/), which can use your GPU for dramatically higher attempt rates.

**Requirements:**
- `hashcat` installed and available in your `PATH`
- Supported archive formats: ZIP, RAR, 7z

**How it works:**  
`archive_cracker.py` builds the appropriate `hashcat` command (mode, attack type, wordlist / mask) and launches it as a subprocess. When hashcat finds the password it is reported back and printed. If hashcat is not found in `PATH` the tool exits with an error; in that case use the CPU-based `--brute` / `--dict` modes instead.

```bash
# Kali / Debian
sudo apt install hashcat

# macOS
brew install hashcat
```

---

## Charset Presets

| Preset  | Characters Included                              |
|---------|--------------------------------------------------|
| `tiny`  | `abc123`                                         |
| `basic` | `a-z` + `0-9`                                    |
| `full`  | `a-z` + `A-Z` + `0-9` + `!@#$%^&*`              |
| `keys`  | `full` + `()_+-=[]{}\|;:,.<>?`                   |

You can also pass a custom charset string directly: `--charset abc123!`

---

## Project Structure

```
archive-cracker/
├── archive_cracker.py    # Main script
├── requirements.txt      # Python dependencies
├── examples/
│   ├── create_test_zip.py     # Script to create test archives
│   ├── sample_wordlist.txt    # Small sample wordlist
│   └── usage_examples.sh      # Shell command examples
├── .gitignore
├── LICENSE
└── README.md
```

---

## How It Works

1. **Format detection** – Identifies archive type from file extension.
2. **Candidate generation** – Creates password candidates via wordlist, mask, pattern, or charset.
3. **Password application** – Attempts extraction using the appropriate library per format.
4. **Threading** – Splits candidates across N threads for parallel testing.
5. **Success** – On match, extracts to output directory and reports the password.

---

## Educational Notes (for class)

- **ZIP crypto weakness**: Traditional ZipCrypto is weak; AES-256 ZIP is stronger but both are crackable with GPU tools like hashcat.
- **Dictionary attacks** are far more effective than pure brute-force in real scenarios.
- **Masks** reduce the search space dramatically when partial password info is known (e.g. length, structure).
- **Leetspeak** targets users who think substituting letters for numbers increases security.
- **Entropy** is the key metric: a 12-char random password has ~72 bits of entropy vs ~19 bits for `pass1234`.

---

## Dependencies

```
rarfile
py7zr
patool
```

Install via:
```bash
pip install rarfile py7zr patool
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Author

Made for ethical hacking and cybersecurity coursework.
**Use responsibly. Always get permission before testing.**
