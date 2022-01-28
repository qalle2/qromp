# Qalle's ROM Patcher
```
usage: qromp.py [-h] [-m {a,c}] [-i INPUT_CRC] [-o OUTPUT_CRC] [-v]
                input_file1 input_file2 output_file

Qalle's ROM Patcher. Applies a BPS/IPS patch to a file or creates a BPS/IPS patch from the
differences of two files. Notes: the BPS encoder is inefficient; the IPS decoder has the 'EOF'
address (0x454f46) bug.

positional arguments:
  input_file1           The original, unpatched file to read.
  input_file2           The second file to read. In 'apply patch' mode, the patch file
                        (.bps/.ips). In 'create patch' mode, the file to compare against
                        input_file1.
  output_file           The file to write. In 'apply patch' mode, the patched copy of input_file1.
                        In 'create patch' mode, the patch file (.bps/.ips).

optional arguments:
  -h, --help            show this help message and exit
  -m {a,c}, --mode {a,c}
                        What to do. 'a' (the default): apply a patch file to another file. 'c':
                        create a patch file.
  -i INPUT_CRC, --input-crc INPUT_CRC
                        Expected CRC32 checksum (zlib variety) of input_file1. 8 hexadecimal
                        digits. Only used when applying an IPS patch.
  -o OUTPUT_CRC, --output-crc OUTPUT_CRC
                        Expected CRC32 checksum (zlib variety) of output_file. 8 hexadecimal
                        digits. Only used when applying an IPS patch.
  -v, --verbose         Print more info.
```
