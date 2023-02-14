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

Qalle's ROM Patcher. Applies BPS/IPS patch to file. IPS decoder has 'EOF'
address (0x454f46) bug.

positional arguments:
  orig_file      Original (unpatched) file to read.
  patch_file     Patch file (.bps/.ips) to read.
  output_file    Patched copy of orig_file to write.

options:
  -h, --help     show this help message and exit
  -v, --verbose  Print more info. (CRC32 checksums are of zlib variety and
                 hexadecimal.)
```

## qromp_enc.py
```
usage: qromp_enc.py [-h] [--bps-min-copy BPS_MIN_COPY]
                    [--ips-max-unchg IPS_MAX_UNCHG]
                    orig_file modified_file patch_file

Qalle's ROM Patch Creator. Creates BPS/IPS patch from differences of two
files. Both encoders are somewhat inefficient; BPS encoder is also slow. BPS
encoder prints progress indicator (100 dots) and time taken.

positional arguments:
  orig_file             Original file to read.
  modified_file         File to read and compare against orig_file. If
                        creating IPS patch, modified_file must be at least as
                        large as orig_file.
  patch_file            Patch file to write (.bps/.ips).

options:
  -h, --help            show this help message and exit
  --bps-min-copy BPS_MIN_COPY
                        (BPS only.) Minimum length of substring to copy from
                        original file. 1-20, default=4. Affects efficiency.
                        Larger=faster.
  --ips-max-unchg IPS_MAX_UNCHG
                        (IPS only.) Maximum length of unchanged substring to
                        store. 0-10, default=1. Affects efficiency.
```

## Other files
* `*.sh`: Linux scripts that test the programs. Warning: they delete files.
* `*.md5`: MD5 hashes of correctly-patched test files.

Test files used by the scripts are not included for legal reasons.
