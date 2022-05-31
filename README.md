# Qalle's ROM Patcher / Qalle's ROM Patch Creator
Apply a BPS/IPS patch to a binary file or create a BPS/IPS patch file from the differences of two binary files.

## qromp.py
```
usage: qromp.py [-h] [-i INPUT_CRC] [-o OUTPUT_CRC] [-v] orig_file patch_file output_file

Qalle's ROM Patcher. Applies a BPS/IPS patch to a file. Note: the IPS decoder has the 'EOF'
address (0x454f46) bug.

positional arguments:
  orig_file             The original, unpatched file to read.
  patch_file            The patch file (.bps/.ips) to read.
  output_file           Patched copy of orig_file to write.

options:
  -h, --help            show this help message and exit
  -i INPUT_CRC, --input-crc INPUT_CRC
                        Expected CRC32 checksum (zlib variety) of orig_file. 8 hexadecimal digits.
  -o OUTPUT_CRC, --output-crc OUTPUT_CRC
                        Expected CRC32 checksum (zlib variety) of output_file. 8 hexadecimal
                        digits.
  -v, --verbose         Print more info.
```

## qromp_enc.py
```
usage: qromp_enc.py [-h] [-v] orig_file modified_file patch_file

Qalle's ROM Patch Creator. Creates a BPS/IPS patch from the differences of two files. Note: the
BPS encoder is inefficient.

positional arguments:
  orig_file      The original file to read.
  modified_file  The file to read and compare against orig_file.
  patch_file     The patch file to write (.bps/.ips).

options:
  -h, --help     show this help message and exit
  -v, --verbose  Print more info.
```

Note: for legal reasons, no bytes from the original file will be saved to the patch file, even if it would make the patch smaller.
