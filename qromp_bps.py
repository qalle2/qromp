import argparse, os, struct, sys
from zlib import crc32

# enumerate BPS actions (types of blocks);
# note that "source" and "target" here refer to *encoder*'s input files
(SOURCE_READ, TARGET_READ, SOURCE_COPY, TARGET_COPY) = range(4)

ACTION_DESCRIPTIONS = {
    SOURCE_READ: "SourceRead",
    TARGET_READ: "TargetRead",
    SOURCE_COPY: "SourceCopy",
    TARGET_COPY: "TargetCopy",
}

# maximum unsigned integer to read from BPS file
# (you may want to increase this in the future)
MAX_UINT = 2 ** 64

FOOTER_SIZE = 3 * 4

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's BPS Patcher. Applies a BPS patch to a file."
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
        "patch_file", help="Patch file (.bps) to read."
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
    try:
        data = handle.read(n)
    except MemoryError:
        sys.exit("Out of memory. (Corrupt patch file?)")
    if len(data) < n:
        sys.exit("Unexpected end of patch file.")
    return data

def read_bps_int(handle):
    # read an unsigned BPS integer starting from current file position;
    # final byte has MSB set, all other bytes have MSB clear;
    # e.g. b"\x12\x34\x89" = (0x12<<0) + ((0x34+1)<<7) + ((0x09+1)<<14)
    # = 0x29a92
    decoded = shift = 0
    while True:
        byte = read_bytes(1, handle)[0]
        decoded += (byte & 0x7f) << shift
        if decoded > MAX_UINT:
            sys.exit("BPS integer too large. (Corrupt patch?)")
        elif byte & 0x80:
            break
        shift += 7
        decoded += 1 << shift
    return decoded

def read_signed_bps_int(handle):
    # read a signed BPS integer
    n = read_bps_int(handle)
    return (-1 if n & 1 else 1) * (n >> 1)

def decode_blocks(srcData, patchHnd, verbose):
    # decode blocks from BPS file (slices from input file, patch file or
    # previous output)

    # get patch size without disturbing file handle position
    patchSize = os.stat(patchHnd.fileno()).st_size

    dstData = bytearray()  # output data
    srcOffset = 0  # read offset in srcData (used by SOURCE_COPY)
    dstOffset = 0  # read offset in dstData (used by TARGET_COPY)

    if verbose:
        print(
            "Address in patch file / patched file size before action / "
            "action / address to copy from / bytes to output:"
        )
        # statistics by action
        blkCnts = 4 * [0]
        blkByteCnts = 4 * [0]

    while patchHnd.tell() < patchSize - FOOTER_SIZE:
        # for statistics
        origPatchPos = patchHnd.tell()
        origDstSize = len(dstData)

        # get length and type of block
        lengthAndAction = read_bps_int(patchHnd)
        length = (lengthAndAction >> 2) + 1
        action = lengthAndAction & 3

        if action == SOURCE_READ:
            # copy from same address in original file
            if len(dstData) + length > len(srcData):
                sys.exit("SourceRead: invalid read position.")
            dstData.extend(srcData[len(dstData):len(dstData)+length])
        elif action == TARGET_READ:
            # copy from current address in patch
            dstData.extend(read_bytes(length, patchHnd))
        elif action == SOURCE_COPY:
            # copy from any address in original file
            srcOffset += read_signed_bps_int(patchHnd)
            if srcOffset < 0 or srcOffset + length > len(srcData):
                sys.exit("SourceCopy: invalid read position.")
            dstData.extend(srcData[srcOffset:srcOffset+length])
            srcOffset += length
        else:
            # TARGET_COPY - copy from any address in patched file
            dstOffset += read_signed_bps_int(patchHnd)
            if not 0 <= dstOffset < len(dstData):
                sys.exit("TargetCopy: invalid read position.")
            # can't copy all in one go because newly-added bytes may also be
            # read; this algorithm keeps doubling the chunk size as long as
            # necessary
            origDstOffset = dstOffset
            finalDstOffset = dstOffset + length
            while dstOffset < finalDstOffset:
                chunkSize = min(
                    finalDstOffset - dstOffset, len(dstData) - origDstOffset
                )
                dstData.extend(dstData[origDstOffset:origDstOffset+chunkSize])
                dstOffset += chunkSize

        if verbose:
            srcAddr = (
                origDstSize,               # SOURCE_READ
                patchHnd.tell() - length,  # TARGET_READ
                srcOffset - length,        # SOURCE_COPY
                dstOffset - length,        # TARGET_COPY
            )[action]
            print(
                f"{origPatchPos:10} {origDstSize:10} "
                f"{ACTION_DESCRIPTIONS[action]} {srcAddr:10} {length:10}"
            )
            blkCnts[action] += 1
            blkByteCnts[action] += length

    if verbose:
        print("Blocks by type:")
        for action in range(4):
            print(
                f"- {blkByteCnts[action]} bytes output by {blkCnts[action]} "
                f"{ACTION_DESCRIPTIONS[action]} blocks"
            )

    return dstData

def apply_bps(origHnd, patchHnd, verbose):
    # apply BPS patch from patchHnd to origHnd, return patched data;
    # see https://gist.github.com/khadiwala/32550f44efcc36a5b6a470ff2d4c9c22

    origHnd.seek(0)
    srcData = origHnd.read()

    # get CRC of patch (except for CRC at the end) for later use
    patchSize = patchHnd.seek(0, 2)
    patchHnd.seek(0)
    patchCrc = crc32(patchHnd.read(patchSize - 4))
    patchHnd.seek(0)

    # header - file format id
    id_ = read_bytes(4, patchHnd)
    if id_[:3] != b"BPS":
        sys.exit("Not a BPS patch.")
    if id_[3:] != b"1":
        print(
            "Warning: possibly unsupported version of BPS file.",
            file=sys.stderr
        )

    # header - file sizes
    hdrSrcSize = read_bps_int(patchHnd)
    hdrDstSize = read_bps_int(patchHnd)
    if verbose:
        print(
            f"Expected file sizes: original={hdrSrcSize}, "
            f"patched={hdrDstSize}."
        )
    if hdrSrcSize != len(srcData):
        print(
            f"Warning: original file size should be {hdrSrcSize}.",
            file=sys.stderr
        )

    # header - metadata
    metadataSize = read_bps_int(patchHnd)
    if metadataSize:
        metadata = read_bytes(metadataSize, patchHnd)
        if verbose:
            print("Metadata:", metadata.decode("ascii", errors="replace"))
    elif verbose:
        print("No metadata.")

    # create output data by repeatedly appending data
    dstData = decode_blocks(srcData, patchHnd, verbose)

    # validate output size
    if hdrDstSize != len(dstData):
        print(
            f"Warning: patched file size should be {hdrDstSize}.",
            file=sys.stderr
        )

    # validate CRCs from footer
    footer = read_bytes(FOOTER_SIZE, patchHnd)
    expectedCrcs = tuple(
        struct.unpack("<L", footer[i:i+4])[0] for i in (0, 4, 8)
    )
    if verbose:
        print(
            "Expected CRC32s: input={:08x}, output={:08x}, patch={:08x}."
            .format(*expectedCrcs)
        )
    if expectedCrcs[0] != crc32(srcData):
        print("Warning: original file CRC mismatch.", file=sys.stderr)
    if expectedCrcs[1] != crc32(dstData):
        print("Warning: patched file CRC mismatch.", file=sys.stderr)
    if expectedCrcs[2] != patchCrc:
        print("Warning: patch file CRC mismatch.", file=sys.stderr)

    return dstData

def main():
    args = parse_args()

    # create patched data
    try:
        with open(args.orig_file, "rb") as origHnd, \
        open(args.patch_file, "rb") as patchHnd:
            patchedData = apply_bps(origHnd, patchHnd, args.verbose)
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
