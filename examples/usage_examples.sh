#!/bin/bash
# =============================================================
# usage_examples.sh
# Archive Cracker - Complete Usage Examples
# Run: chmod +x usage_examples.sh && ./usage_examples.sh
# Or just copy-paste individual commands
# =============================================================

echo "======================================="
echo "  Archive Cracker - Usage Examples"
echo "======================================="

# -------------------------------------------
# STEP 0: Setup - Create test archives first
# -------------------------------------------
echo "[STEP 0] Creating test archives..."
python examples/create_test_archives.py

echo ""
echo "--- DICTIONARY ATTACKS ---"

# -------------------------------------------
# EXAMPLE 1: Basic dictionary attack on ZIP
# -------------------------------------------
echo "[1] Basic dictionary attack on ZIP..."
python archive_cracker.py \
  -f test_archives/test_medium.zip \
  -d examples/sample_wordlist.txt \
  -t 8 \
  -o ./output/dict_zip

# -------------------------------------------
# EXAMPLE 2: Dictionary + leet substitution
# -------------------------------------------
echo "[2] Dictionary with leetspeak on ZIP..."
python archive_cracker.py \
  -f test_archives/test_leet.zip \
  -d examples/sample_wordlist.txt \
  --leet \
  -t 8 \
  -o ./output/leet_zip

# -------------------------------------------
# EXAMPLE 3: Dictionary + append year
# -------------------------------------------
echo "[3] Dictionary with appended year suffix..."
python archive_cracker.py \
  -f test_archives/test_medium.zip \
  -d examples/sample_wordlist.txt \
  --app 2024 \
  -t 8

# -------------------------------------------
# EXAMPLE 4: Dictionary + prepend prefix
# -------------------------------------------
echo "[4] Dictionary with prepend prefix..."
python archive_cracker.py \
  -f test_archives/test_medium.zip \
  -d examples/sample_wordlist.txt \
  --pre "my_" \
  -t 8

echo ""
echo "--- BRUTE-FORCE ATTACKS ---"

# -------------------------------------------
# EXAMPLE 5: Classic brute-force (tiny charset)
# -------------------------------------------
echo "[5] Brute-force with tiny charset (1-3 chars)..."
python archive_cracker.py \
  -f test_archives/test_easy.zip \
  --brute \
  --charset tiny \
  --minlen 1 \
  --maxlen 3 \
  -t 8 \
  -o ./output/brute_easy

# -------------------------------------------
# EXAMPLE 6: Brute-force with basic charset
# -------------------------------------------
echo "[6] Brute-force alphanumeric (4 chars)..."
python archive_cracker.py \
  -f test_archives/test_medium.zip \
  --brute \
  --charset basic \
  --minlen 4 \
  --maxlen 4 \
  -t 16

# -------------------------------------------
# EXAMPLE 7: Brute-force on 7Z archive
# -------------------------------------------
echo "[7] Brute-force 7Z (5-6 chars, basic)..."
python archive_cracker.py \
  -f test_archives/test_7z.7z \
  --brute \
  --charset basic \
  --minlen 5 \
  --maxlen 6 \
  -t 8 \
  -o ./output/brute_7z

echo ""
echo "--- MASK ATTACKS ---"

# -------------------------------------------
# EXAMPLE 8: Mask attack (?l?l?d?d)
# -------------------------------------------
echo "[8] Mask attack: 2 lowercase + 2 digits..."
python archive_cracker.py \
  -f test_archives/test_medium.zip \
  --brute-mask '?l?l?d?d' \
  -t 16 \
  -o ./output/mask_zip

# -------------------------------------------
# EXAMPLE 9: Mask - uppercase + digits
# -------------------------------------------
echo "[9] Mask attack: uppercase + 3 digits..."
python archive_cracker.py \
  -f test_archives/test_medium.zip \
  --brute-mask '?u?u?u?d?d?d' \
  -t 16

# -------------------------------------------
# EXAMPLE 10: Mask - all char types
# -------------------------------------------
echo "[10] Mask attack: any 4 chars (?a?a?a?a)..."
python archive_cracker.py \
  -f test_archives/test_easy.zip \
  --brute-mask '?a?a?a' \
  -t 16

echo ""
echo "--- PATTERN ATTACKS ---"

# -------------------------------------------
# EXAMPLE 11: Pattern attack (know prefix)
# -------------------------------------------
echo "[11] Pattern: admin + 2 digits..."
python archive_cracker.py \
  -f test_archives/test_pattern.zip \
  --brute-pattern 'admin?d?d' \
  -t 8 \
  -o ./output/pattern_zip

# -------------------------------------------
# EXAMPLE 12: Pattern with append
# -------------------------------------------
echo "[12] Pattern + append year..."
python archive_cracker.py \
  -f test_archives/test_pattern.zip \
  --brute-pattern 'user?d?d' \
  --app '!' \
  -t 8

# -------------------------------------------
# EXAMPLE 13: Rockyou wordlist (full attack)
# -------------------------------------------
echo "[13] Full rockyou.txt dictionary attack (Kali)..."
# Uncomment when rockyou.txt is available:
# python archive_cracker.py \
#   -f /path/to/target.zip \
#   -d /usr/share/wordlists/rockyou.txt \
#   -t 16 \
#   -o ./output/rockyou_result

echo ""
echo "All examples complete!"
echo "Check ./output/ for extracted files."
