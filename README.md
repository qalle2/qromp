# Qalle's ROM Patcher / Qalle's ROM Patch Creator
Apply a BPS/IPS patch to a binary file or create a BPS/IPS patch file from the
differences of two binary files.

Table of contents:
* [qromp.py](#qromppy)
* [qromp_enc.py](#qromp_encpy)
* [Other files](#other-files)

## qromp.py
```
usage: qromp.py [-h] [-v] orig_file patch_file output_file

Qalle's ROM Patcher. Applies a BPS/IPS patch to a file. Note: the IPS decoder
has the 'EOF' address (0x454f46) bug.

positional arguments:
  orig_file      The original, unpatched file to read.
  patch_file     The patch file (.bps/.ips) to read.
  output_file    Patched copy of orig_file to write.

options:
  -h, --help     show this help message and exit
  -v, --verbose  Print more info. (CRC32 checksums are of zlib variety and
                 hexadecimal.)
```

## qromp_enc.py
```
usage: qromp_enc.py [-h] [--ips-max-unchg IPS_MAX_UNCHG]
                    orig_file modified_file patch_file

Qalle's ROM Patch Creator. Creates a BPS/IPS patch from the differences of two
files. Notes: does not support creating a BPS patch from input files of
different size; both encoders are somewhat inefficient; the BPS encoder is
also slow.

positional arguments:
  orig_file             The original file to read.
  modified_file         The file to read and compare against orig_file. If
                        creating an IPS, must be at least as large as
                        orig_file. If creating a BPS, must be the size as
                        orig_file.
  patch_file            The patch file to write (.bps/.ips).

options:
  -h, --help            show this help message and exit
  --ips-max-unchg IPS_MAX_UNCHG
                        (IPS only.) Maximum length of unchanged substring to
                        store. 0-10, default=1. Larger values may be more
                        efficient.
```

## Other files
* `*.sh`: Linux scripts that test the programs. Warning: they delete files.
* `*.md5`: MD5 hashes of correctly-patched test files.

Test files used by the scripts are not included for legal reasons.
