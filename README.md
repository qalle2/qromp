# Qalle's ROM Patcher / Qalle's ROM Patch Creator
Apply a BPS/IPS patch to a binary file or create a BPS/IPS patch file from the
differences of two binary files.

Table of contents:
* [qromp_bps.py](#qromp_bpspy)
* [qromp_ips.py](#qromp_ipspy)
* [qromp_enc_bps.py](#qromp_enc_bpspy)
* [qromp_enc_ips.py](#qromp_enc_ipspy)
* [Other files](#other-files)

## qromp_bps.py
```
usage: qromp_bps.py [-h] [-v] orig_file patch_file output_file

Qalle's BPS Patcher. Applies a BPS patch to a file.

positional arguments:
  orig_file      Original (unpatched) file to read.
  patch_file     Patch file (.bps) to read.
  output_file    Patched copy of orig_file to write.

options:
  -h, --help     show this help message and exit
  -v, --verbose  Print more info. (CRC32 checksums are of zlib variety and
                 hexadecimal.)
```

## qromp_ips.py
```
usage: qromp_ips.py [-h] [-v] orig_file patch_file output_file

Qalle's IPS Patcher. Applies an IPS patch to a file. Has the 'EOF' address
(0x454f46) bug.

positional arguments:
  orig_file      Original (unpatched) file to read.
  patch_file     Patch file (.ips) to read.
  output_file    Patched copy of orig_file to write.

options:
  -h, --help     show this help message and exit
  -v, --verbose  Print more info. (CRC32 checksums are of zlib variety and
                 hexadecimal.)
```

## qromp_enc_bps.py
```
usage: qromp_enc_bps.py [-h] [--min-copy MIN_COPY]
                        orig_file modified_file patch_file

Qalle's BPS Patch Creator. Creates a BPS patch from differences of two files.
Inefficient and slow. Prints a progress indicator (100 dots).

positional arguments:
  orig_file            Original file to read.
  modified_file        File to read and compare against orig_file.
  patch_file           Patch file to write (.bps).

options:
  -h, --help           show this help message and exit
  --min-copy MIN_COPY  Minimum length of substring to copy from original file.
                       1-20, default=4. Affects efficiency. Larger=faster.
```

## qromp_enc_ips.py
```
usage: qromp_enc_ips.py [-h] [--max-unchg MAX_UNCHG]
                        orig_file modified_file patch_file

Qalle's IPS Patch Creator. Creates an IPS patch from the differences of two
files. Somewhat inefficient.

positional arguments:
  orig_file             Original file to read.
  modified_file         File to read and compare against orig_file. Must be at
                        least as large as orig_file.
  patch_file            Patch file to write (.ips).

options:
  -h, --help            show this help message and exit
  --max-unchg MAX_UNCHG
                        Maximum length of unchanged substring to store. 0-10,
                        default=1. Affects efficiency.
```

## Other files
* `*.sh`: Linux scripts that test the programs. Warning: they delete files.
* `*.md5`: MD5 hashes of correctly-patched test files.

Test files used by the scripts are not included for legal reasons.
