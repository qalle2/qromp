# Qalle's ROM Patcher / Qalle's ROM Patch Creator
Apply a BPS/IPS patch to a binary file or create a BPS/IPS patch file from the differences of two binary files.

Table of contents:
* [qromp.py](#qromppy)
* [qromp_enc.py](#qromp_encpy)
* [Other files](#other-files)

## qromp.py
```
usage: qromp.py [-h] [-i INPUT_CRC] [-o OUTPUT_CRC] [-v]
                orig_file patch_file output_file

Qalle's ROM Patcher. Applies a BPS/IPS patch to a file. Note: the IPS decoder
has the 'EOF' address (0x454f46) bug.

positional arguments:
  orig_file             The original, unpatched file to read.
  patch_file            The patch file (.bps/.ips) to read.
  output_file           Patched copy of orig_file to write.

options:
  -h, --help            show this help message and exit
  -i INPUT_CRC, --input-crc INPUT_CRC
                        Expected CRC32 checksum (zlib variety) of orig_file. 8
                        hexadecimal digits.
  -o OUTPUT_CRC, --output-crc OUTPUT_CRC
                        Expected CRC32 checksum (zlib variety) of output_file.
                        8 hexadecimal digits.
  -v, --verbose         Print more info.
```

## qromp_enc.py
```
usage: qromp_enc.py [-h] [-v] [-u MAX_UNCHANGED] [-r IPS_MIN_RLE_LENGTH]
                    orig_file modified_file patch_file

Qalle's ROM Patch Creator. Creates a BPS/IPS patch from the differences of two
files. Notes: does not support files of different size; the BPS encoder is
inefficient.

positional arguments:
  orig_file             The original file to read.
  modified_file         The file to read and compare against orig_file.
  patch_file            The patch file to write (.bps/.ips).

options:
  -h, --help            show this help message and exit
  -v, --verbose         Print more info.
  -u MAX_UNCHANGED, --max-unchanged MAX_UNCHANGED
                        Maximum number of consecutive unchanged bytes to
                        store. 0-10, default=1. Other values may reduce patch
                        size.
  -r IPS_MIN_RLE_LENGTH, --ips-min-rle-length IPS_MIN_RLE_LENGTH
                        Only use RLE encoding for at least this many repeats
                        in IPS patches. 1-10, default=6. Other values may
                        reduce patch size.
```

## Other files
* `patched.md5`: MD5 hashes of correctly-patched test files
