import argparse, os, struct, sys
from zlib import crc32

# actions (types of BPS blocks); note that "source" and "target" here refer to
# *encoder*'s input files
BPS_SOURCE_READ = 0
BPS_TARGET_READ = 1
BPS_SOURCE_COPY = 2
BPS_TARGET_COPY = 3

def get_ext(path):
    return os.path.splitext(path)[1].lower()  # e.g. "/FILE.EXT" -> ".ext"

def get_file_size(hnd):
    # get file size without disturbing file handle position
    return os.stat(hnd.fileno()).st_size

def read_bytes(n, hnd):
    # return n bytes from handle or exit on EOF
    try:
        data = hnd.read(n)
    except MemoryError:
        sys.exit("Out of memory. (Corrupt patch file?)")
    if len(data) < n:
        sys.exit("Unexpected end of patch file.")
    return data

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's ROM Patcher. Applies a BPS/IPS patch to a file. "
        "Note: the IPS decoder has the 'EOF' address (0x454f46) bug."
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print more info. (CRC32 checksums are of zlib variety and "
        "hexadecimal.)"
    )

    parser.add_argument(
        "orig_file", help="The original, unpatched file to read."
    )
    parser.add_argument(
        "patch_file", help="The patch file (.bps/.ips) to read."
    )
    parser.add_argument(
        "output_file", help="Patched copy of orig_file to write."
    )

    args = parser.parse_args()

    if get_ext(args.patch_file) not in (".bps", ".ips"):
        sys.exit("Unsupported patch file format.")

    if not os.path.isfile(args.orig_file):
        sys.exit("Original file not found.")
    if not os.path.isfile(args.patch_file):
        sys.exit("Patch file not found.")
    if os.path.exists(args.output_file):
        sys.exit("Output file already exists.")

    return args

# -----------------------------------------------------------------------------

def bps_read_int(hnd):
    # read an unsigned BPS integer starting from current file position
    # final byte has MSB set, all other bytes have MSB clear
    # e.g. b"\x12\x34\x89" = (0x12<<0) + ((0x34+1)<<7) + ((0x09+1)<<14)
    # = 0x29a92
    decoded = 0
    shift = 0
    while True:
        byte = read_bytes(1, hnd)[0]
        decoded += (byte & 0x7f) << shift
        if byte & 0x80:
            break
        shift += 7
        decoded += 1 << shift
    return decoded

def bps_decode_signed(n):
    # decode a signed BPS integer
    return (-1 if n & 1 else 1) * (n >> 1)

def bps_decode_blocks(srcData, patchHnd, verbose):
    # decode blocks from BPS file (slices from input file, patch file or
    # previous output)

    patchSize = get_file_size(patchHnd)

    dstData = bytearray()  # output data
    srcOffset = 0  # read offset in srcData (used by "SourceCopy" action)
    dstOffset = 0  # read offset in dstData (used by "TargetCopy" action)

    # statistics (source/target read/copy block/byte count)
    srcRdBlks = trgRdBlks = srcCpBlks = trgCpBlks = 0
    srcRdBytes = trgRdBytes = srcCpBytes = trgCpBytes = 0

    while patchHnd.tell() < patchSize - 3 * 4:
        # get length and type of block
        lengthAndAction = bps_read_int(patchHnd)
        length = (lengthAndAction >> 2) + 1
        action = lengthAndAction & 3

        if action == BPS_SOURCE_READ:
            # copy from same address in original file
            if len(dstData) + length > len(srcData):
                sys.exit(
                    "SourceRead: tried to read from invalid position in input "
                    "data."
                )
            dstData.extend(srcData[len(dstData):len(dstData)+length])
            srcRdBlks += 1
            srcRdBytes += length
        elif action == BPS_TARGET_READ:
            # copy from current address in patch
            dstData.extend(read_bytes(length, patchHnd))
            trgRdBlks += 1
            trgRdBytes += length
        elif action == BPS_SOURCE_COPY:
            # copy from any address in original file
            srcOffset += bps_decode_signed(bps_read_int(patchHnd))
            if srcOffset < 0 or srcOffset + length > len(srcData):
                sys.exit(
                    "SourceCopy: tried to read from invalid position in input "
                    "data."
                )
            dstData.extend(srcData[srcOffset:srcOffset+length])
            srcOffset += length
            srcCpBlks += 1
            srcCpBytes += length
        else:
            # BPS_TARGET_COPY - copy from any address in patched file
            dstOffset += bps_decode_signed(bps_read_int(patchHnd))
            if not 0 <= dstOffset < len(dstData):
                sys.exit(
                    "TargetCopy: tried to read from invalid position in "
                    "output data."
                )
            # can't copy all in one go because newly-added bytes may also be
            # read
            for i in range(length):
                dstData.append(dstData[dstOffset])
                dstOffset += 1
            trgCpBlks += 1
            trgCpBytes += length

    if verbose:
        print(
            f"{srcRdBytes}/{trgRdBytes}/{srcCpBytes}/{trgCpBytes} bytes in "
            f"{srcRdBlks}/{trgRdBlks}/{srcCpBlks}/{trgCpBlks} blocks of type "
            "SourceRead/TargetRead/SourceCopy/TargetCopy."
        )

    return dstData

def bps_apply(origHnd, patchHnd, args):
    # apply BPS patch from patchHnd to origHnd, return patched data
    # see https://gist.github.com/khadiwala/32550f44efcc36a5b6a470ff2d4c9c22

    origHnd.seek(0)
    srcData = origHnd.read()

    # get CRC of patch (except for CRC at the end) for later use
    patchHnd.seek(0)
    patchCrc = crc32(patchHnd.read(get_file_size(patchHnd) - 4))

    patchHnd.seek(0)

    # header - file format id
    id_ = read_bytes(4, patchHnd)
    if id_[:3] != b"BPS":
        sys.exit("Not a BPS file.")
    if id_[3:] != b"1":
        print(
            "Warning: possibly unsupported version of BPS file.",
            file=sys.stderr
        )

    # header - file sizes
    hdrSrcSize = bps_read_int(patchHnd)
    hdrDstSize = bps_read_int(patchHnd)
    if args.verbose:
        print(f"Expected file sizes: input={hdrSrcSize}, output={hdrDstSize}.")
    if hdrSrcSize != len(srcData):
        print(
            f"Warning: input file size should be {hdrSrcSize}.",
            file=sys.stderr
        )

    # header - metadata
    metadataSize = bps_read_int(patchHnd)
    if metadataSize:
        metadata = read_bytes(metadataSize, patchHnd)
        if args.verbose:
            print("Metadata:", metadata.decode("ascii", errors="replace"))
    elif args.verbose:
        print("No metadata.")

    # create output data by repeatedly appending data
    dstData = bps_decode_blocks(srcData, patchHnd, args.verbose)

    # validate output size
    if hdrDstSize != len(dstData):
        print(
            f"Warning: output file size should be {hdrDstSize}.",
            file=sys.stderr
        )

    # validate CRCs from footer
    footer = read_bytes(3 * 4, patchHnd)
    expectedCrcs = tuple(
        struct.unpack("<L", footer[i:i+4])[0] for i in (0, 4, 8)
    )
    if args.verbose:
        print(
            "Expected CRC32s: input={:08x}, output={:08x}, patch={:08x}."
            .format(*expectedCrcs)
        )
    if expectedCrcs[0] != crc32(srcData):
        print("Warning: input file CRC mismatch.", file=sys.stderr)
    if expectedCrcs[1] != crc32(dstData):
        print("Warning: output file CRC mismatch.", file=sys.stderr)
    if expectedCrcs[2] != patchCrc:
        print("Warning: patch file CRC mismatch.", file=sys.stderr)

    return dstData

# -----------------------------------------------------------------------------

def ips_decode_int(bytes_):
    # decode an IPS integer (unsigned, most significant byte first)
    return sum(b << (8 * i) for (i, b) in enumerate(bytes_[::-1]))

def ips_generate_blocks(hnd):
    # read IPS file starting from after header
    # generate each block as (offset, length, is_RLE, data); for RLE blocks,
    # data is one byte

    while True:
        blockPos = hnd.tell()
        offset = ips_decode_int(read_bytes(3, hnd))
        if offset == 0x454f46:  # "EOF"
            break
        length = ips_decode_int(read_bytes(2, hnd))
        if length == 0:
            # RLE
            length = ips_decode_int(read_bytes(2, hnd))
            if length < 3:
                print(
                    "Warning: RLE block has less than 3 bytes; patch may be "
                    "corrupt.", file=sys.stderr
                )
            yield (offset, length, True, read_bytes(1, hnd))
        else:
            # non-RLE
            yield (offset, length, False, read_bytes(length, hnd))

def ips_apply(origHnd, patchHnd, args):
    # apply IPS patch from patchHnd to origHnd, return patched data
    # see https://zerosoft.zophar.net/ips.php
    # note: the patch is allowed to append data to the end of the file

    origHnd.seek(0)
    data = bytearray(origHnd.read())

    if args.verbose:
        print(f"CRC32 of input file: {crc32(data):08x}.")

    patchHnd.seek(0)

    if read_bytes(5, patchHnd) != b"PATCH":
        sys.exit("Not an IPS file.")

    rleBlockCnt = nonRleBlockCnt = rleByteCnt = nonRleByteCnt = 0  # statistics

    for (offset, length, isRle, blockData) in ips_generate_blocks(patchHnd):
        if offset > len(data):
            sys.exit("Tried to write past end of data.")
        data[offset:offset+length] = length * blockData if isRle else blockData
        if isRle:
            rleBlockCnt += 1
            rleByteCnt += length
        else:
            nonRleBlockCnt += 1
            nonRleByteCnt += length

    if args.verbose:
        print(
            f"{rleByteCnt}/{nonRleByteCnt} bytes "
            f"in {rleBlockCnt}/{nonRleBlockCnt} "
            "blocks of type RLE/non-RLE."
        )
        print(f"CRC32 of output file: {crc32(data):08x}.")

    return data

# -----------------------------------------------------------------------------

def main():
    args = parse_args()

    # create patched data
    try:
        with open(args.orig_file, "rb") as origHnd, \
        open(args.patch_file, "rb") as patchHnd:
            if get_ext(args.patch_file) == ".bps":
                patchedData = bps_apply(origHnd, patchHnd, args)
            else:
                patchedData = ips_apply(origHnd, patchHnd, args)
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
