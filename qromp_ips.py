import argparse, os, sys
from zlib import crc32

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's IPS Patcher. Applies an IPS patch to a file. Has "
        "the 'EOF' address (0x454f46) bug."
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print more info. (CRC32 checksums are of zlib variety and "
        "hexadecimal.)"
    )

    parser.add_argument(
        "orig_file", help="Original (unpatched) file to read."
    )
    parser.add_argument(
        "patch_file", help="Patch file (.ips) to read."
    )
    parser.add_argument(
        "output_file", help="Patched copy of orig_file to write."
    )

    args = parser.parse_args()

    if not os.path.isfile(args.orig_file):
        sys.exit("Original file not found.")
    if not os.path.isfile(args.patch_file):
        sys.exit("Patch file not found.")
    if os.path.exists(args.output_file):
        sys.exit("Output file already exists.")

    return args

def read_bytes(n, handle):
    # return n bytes from handle
    data = handle.read(n)
    if len(data) < n:
        sys.exit("Unexpected end of patch file.")
    return data

def decode_int(bytes_):
    # decode an IPS integer (unsigned, most significant byte first)
    return sum(b << (8 * i) for (i, b) in enumerate(bytes_[::-1]))

def get_blocks(handle):
    # read IPS file starting from after header;
    # generate each block as (patch_pos, offset, length, is_RLE, data);
    # for RLE blocks, data is one byte

    while True:
        patchPos = handle.tell()
        offset = decode_int(read_bytes(3, handle))

        if offset == 0x454f46:  # "EOF"
            break

        length = decode_int(read_bytes(2, handle))
        if length == 0:
            # RLE
            length = decode_int(read_bytes(2, handle))
            yield (patchPos, offset, length, True, read_bytes(1, handle))
        else:
            # non-RLE
            yield (patchPos, offset, length, False, read_bytes(length, handle))

def apply_ips(origHnd, patchHnd, verbose):
    # apply IPS patch from patchHnd to origHnd, return patched data;
    # see https://zerosoft.zophar.net/ips.php
    # note: the patch is allowed to append data to the end of the file

    origHnd.seek(0)
    data = bytearray(origHnd.read())

    if verbose:
        print(f"CRC32 of input file: {crc32(data):08x}.")

    patchHnd.seek(0)

    if read_bytes(5, patchHnd) != b"PATCH":
        sys.exit("Not an IPS patch.")

    if verbose:
        print(
            "Address in patch file / address in original file / block type / "
            "bytes to output:"
        )
        # statistics by block type
        blkCnts = 2 * [0]
        blkByteCnts = 2 * [0]

    for (patchPos, offset, length, isRle, blockData) in get_blocks(patchHnd):
        if offset > len(data):
            sys.exit("Tried to write past end of data.")
        data[offset:offset+length] = (length if isRle else 1) * blockData
        if verbose:
            blkCnts[isRle] += 1
            blkByteCnts[isRle] += length
            descr = "RLE" if isRle else "non-RLE"
            print(f"{patchPos:10} {offset:10} {descr:7} {length:10}")

    if verbose:
        eofPos = patchHnd.seek(0, 2) - 3
        print(f"{eofPos:10} {'-':>10} {'EOF':7} {'-':>10}")
        print("Blocks by type:")
        for bt in range(2):
            descr = ("non-RLE", "RLE")[bt]
            print(
                f"- {blkByteCnts[bt]} bytes output by {blkCnts[bt]} {descr} "
                "blocks"
            )
        print(f"CRC32 of output file: {crc32(data):08x}.")

    return data

def main():
    args = parse_args()

    # create patched data
    try:
        with open(args.orig_file, "rb") as origHnd, \
        open(args.patch_file, "rb") as patchHnd:
            patchedData = apply_ips(origHnd, patchHnd, args.verbose)
    except OSError:
        sys.exit("Error reading input files.")

    # write patched data
    try:
        with open(args.output_file, "wb") as handle:
            handle.seek(0)
            handle.write(patchedData)
    except OSError:
        sys.exit("Error writing output file.")

main()
