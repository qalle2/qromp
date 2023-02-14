import argparse, os, struct, sys
from zlib import crc32

# enumerate BPS actions (types of blocks);
# note that "source" and "target" here refer to *encoder*'s input files
(
    BPS_SOURCE_READ,
    BPS_TARGET_READ,
    BPS_SOURCE_COPY,
    BPS_TARGET_COPY,
) = range(4)

# descriptions of BPS actions; value: (name, source_file)
BPS_DESCRIPTIONS = {
    BPS_SOURCE_READ: ("SourceRead", "original"),
    BPS_TARGET_READ: ("TargetRead", "patch"),
    BPS_SOURCE_COPY: ("SourceCopy", "original"),
    BPS_TARGET_COPY: ("TargetCopy", "patched"),
}

# maximum unsigned integer to read from BPS file
# (you may want to increase this in the future)
BPS_MAX_UINT = 2 ** 64

def get_file_ext(path):
    return os.path.splitext(path)[1].lower()  # e.g. "/FILE.EXT" -> ".ext"

def read_bytes(n, handle):
    # return n bytes from handle
    try:
        data = handle.read(n)
    except MemoryError:
        sys.exit("Out of memory. (Corrupt patch file?)")
    if len(data) < n:
        sys.exit("Unexpected end of patch file.")
    return data

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's ROM Patcher. Applies BPS/IPS patch to file. IPS "
        "decoder has 'EOF' address (0x454f46) bug."
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
        "patch_file", help="Patch file (.bps/.ips) to read."
    )
    parser.add_argument(
        "output_file", help="Patched copy of orig_file to write."
    )

    args = parser.parse_args()

    if get_file_ext(args.patch_file) not in (".bps", ".ips"):
        sys.exit("Unsupported patch file format.")

    if not os.path.isfile(args.orig_file):
        sys.exit("Original file not found.")
    if not os.path.isfile(args.patch_file):
        sys.exit("Patch file not found.")
    if os.path.exists(args.output_file):
        sys.exit("Output file already exists.")

    return args

# -----------------------------------------------------------------------------

def bps_read_int(handle):
    # read an unsigned BPS integer starting from current file position;
    # final byte has MSB set, all other bytes have MSB clear;
    # e.g. b"\x12\x34\x89" = (0x12<<0) + ((0x34+1)<<7) + ((0x09+1)<<14)
    # = 0x29a92
    decoded = shift = 0
    while True:
        byte = read_bytes(1, handle)[0]
        decoded += (byte & 0x7f) << shift
        if decoded > BPS_MAX_UINT:
            sys.exit("BPS integer too large. (Corrupt patch?)")
        elif byte & 0x80:
            break
        shift += 7
        decoded += 1 << shift
    return decoded

def bps_read_signed_int(handle):
    # read a signed BPS integer
    n = bps_read_int(handle)
    return (-1 if n & 1 else 1) * (n >> 1)

def bps_decode_blocks(srcData, patchHnd, verbose):
    # decode blocks from BPS file (slices from input file, patch file or
    # previous output)

    # get patch size without disturbing file handle position
    patchSize = os.stat(patchHnd.fileno()).st_size

    dstData = bytearray()  # output data
    srcOffset = 0  # read offset in srcData (used by BPS_SOURCE_COPY)
    dstOffset = 0  # read offset in dstData (used by BPS_TARGET_COPY)

    if verbose:
        print(
            "Address in patch file / patched file size before action / "
            "action / file to copy from / address to copy from / "
            "bytes to output:"
        )
        # statistics by action
        blkCnts = 4 * [0]
        blkByteCnts = 4 * [0]

    while patchHnd.tell() < patchSize - 3 * 4:
        # for statistics
        origPatchPos = patchHnd.tell()
        origDstSize = len(dstData)

        # get length and type of block
        lengthAndAction = bps_read_int(patchHnd)
        length = (lengthAndAction >> 2) + 1
        action = lengthAndAction & 3

        if action == BPS_SOURCE_READ:
            # copy from same address in original file
            if len(dstData) + length > len(srcData):
                sys.exit(
                    "SourceRead: tried to read from invalid position in "
                    "original file."
                )
            dstData.extend(srcData[len(dstData):len(dstData)+length])
        elif action == BPS_TARGET_READ:
            # copy from current address in patch
            dstData.extend(read_bytes(length, patchHnd))
        elif action == BPS_SOURCE_COPY:
            # copy from any address in original file
            srcOffset += bps_read_signed_int(patchHnd)
            if srcOffset < 0 or srcOffset + length > len(srcData):
                sys.exit(
                    "SourceCopy: tried to read from invalid position in "
                    "original file."
                )
            dstData.extend(srcData[srcOffset:srcOffset+length])
            srcOffset += length
        else:
            # BPS_TARGET_COPY - copy from any address in patched file
            dstOffset += bps_read_signed_int(patchHnd)
            if not 0 <= dstOffset < len(dstData):
                sys.exit(
                    "TargetCopy: tried to read from invalid position in "
                    "patched file."
                )
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
            (actName, srcFile) = BPS_DESCRIPTIONS[action]
            srcAddr = (
                origDstSize,               # BPS_SOURCE_READ
                patchHnd.tell() - length,  # BPS_TARGET_READ
                srcOffset - length,        # BPS_SOURCE_COPY
                dstOffset - length,        # BPS_TARGET_COPY
            )[action]
            print(
                f"{origPatchPos:10} {origDstSize:10} {actName} {srcFile:10} "
                f"{srcAddr:10} {length:10}"
            )
            blkCnts[action] += 1
            blkByteCnts[action] += length

    if verbose:
        print("Blocks by type:")
        for action in range(4):
            print(
                f"- {blkByteCnts[action]} bytes output by {blkCnts[action]} "
                f"{BPS_DESCRIPTIONS[action][0]} blocks"
            )

    return dstData

def bps_apply(origHnd, patchHnd, verbose):
    # apply BPS patch from patchHnd to origHnd, return patched data
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
        sys.exit("Not a BPS file.")
    if id_[3:] != b"1":
        print(
            "Warning: possibly unsupported version of BPS file.",
            file=sys.stderr
        )

    # header - file sizes
    hdrSrcSize = bps_read_int(patchHnd)
    hdrDstSize = bps_read_int(patchHnd)
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
    metadataSize = bps_read_int(patchHnd)
    if metadataSize:
        metadata = read_bytes(metadataSize, patchHnd)
        if verbose:
            print("Metadata:", metadata.decode("ascii", errors="replace"))
    elif verbose:
        print("No metadata.")

    # create output data by repeatedly appending data
    dstData = bps_decode_blocks(srcData, patchHnd, verbose)

    # validate output size
    if hdrDstSize != len(dstData):
        print(
            f"Warning: patched file size should be {hdrDstSize}.",
            file=sys.stderr
        )

    # validate CRCs from footer
    footer = read_bytes(3 * 4, patchHnd)
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

# -----------------------------------------------------------------------------

def ips_decode_int(bytes_):
    # decode an IPS integer (unsigned, most significant byte first)
    return sum(b << (8 * i) for (i, b) in enumerate(bytes_[::-1]))

def ips_generate_blocks(handle):
    # read IPS file starting from after header
    # generate each block as (patch_pos, offset, length, is_RLE, data);
    # for RLE blocks, data is one byte

    while True:
        patchPos = handle.tell()
        offset = ips_decode_int(read_bytes(3, handle))

        if offset == 0x454f46:  # "EOF"
            break

        length = ips_decode_int(read_bytes(2, handle))
        if length == 0:
            # RLE
            length = ips_decode_int(read_bytes(2, handle))
            yield (patchPos, offset, length, True, read_bytes(1, handle))
        else:
            # non-RLE
            yield (patchPos, offset, length, False, read_bytes(length, handle))

def ips_apply(origHnd, patchHnd, verbose):
    # apply IPS patch from patchHnd to origHnd, return patched data
    # see https://zerosoft.zophar.net/ips.php
    # note: the patch is allowed to append data to the end of the file

    origHnd.seek(0)
    data = bytearray(origHnd.read())

    if verbose:
        print(f"CRC32 of input file: {crc32(data):08x}.")

    patchHnd.seek(0)

    if read_bytes(5, patchHnd) != b"PATCH":
        sys.exit("Not an IPS file.")

    if verbose:
        print(
            "Address in patch file / address in original file / block type / "
            "bytes to output:"
        )
        # statistics by block type
        blkCnts = 2 * [0]
        blkByteCnts = 2 * [0]

    for (patchPos, offset, length, isRle, blockData) \
    in ips_generate_blocks(patchHnd):
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

# -----------------------------------------------------------------------------

def main():
    args = parse_args()

    # create patched data
    try:
        with open(args.orig_file, "rb") as origHnd, \
        open(args.patch_file, "rb") as patchHnd:
            if get_file_ext(args.patch_file) == ".bps":
                patchedData = bps_apply(origHnd, patchHnd, args.verbose)
            else:
                patchedData = ips_apply(origHnd, patchHnd, args.verbose)
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
