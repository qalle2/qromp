import argparse, os, struct, sys
from zlib import crc32

def error(msg):
    sys.exit(f"Error: {msg}")

def warn(msg):
    print("Warning:", msg, file=sys.stderr)

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
        error("out of memory reading patch file")
    if len(data) < n:
        error("unexpected end of patch file")
    return data

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's ROM Patcher. Applies a BPS/IPS patch to a file. Note: the IPS "
        "decoder has the 'EOF' address (0x454f46) bug."
    )

    parser.add_argument(
        "-i", "--input-crc", type=str,
        help="Expected CRC32 checksum (zlib variety) of orig_file. 8 hexadecimal digits."
    )
    parser.add_argument(
        "-o", "--output-crc", type=str,
        help="Expected CRC32 checksum (zlib variety) of output_file. 8 hexadecimal digits."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print more info."
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

    try:
        for crc in (args.input_crc, args.output_crc):
            if crc is not None and not 0 <= int(crc, 16) <= 0xffff_ffff:
                raise ValueError
    except ValueError:
        error("invalid CRC32 specified")

    if get_ext(args.patch_file) not in (".bps", ".ips"):
        error("unsupported patch file format")

    if not os.path.isfile(args.orig_file):
        error("original file not found")
    if not os.path.isfile(args.patch_file):
        error("patch file not found")
    if os.path.exists(args.output_file):
        error("output file already exists")

    return args

# -------------------------------------------------------------------------------------------------

def bps_read_int(hnd):
    # read an unsigned BPS integer starting from current file position
    # final byte has MSB set, all other bytes have MSB clear
    # e.g. b"\x12\x34\x89" = (0x12<<0) + ((0x34+1)<<7) + ((0x09+1)<<14) = 0x29a92
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
    # decode blocks from BPS file (slices from input file, patch file or previous output)

    patchSize = get_file_size(patchHnd)

    dstData = bytearray()  # output data
    srcOffset = 0  # read offset in srcData (used by "SourceCopy" action)
    dstOffset = 0  # read offset in dstData (used by "TargetCopy" action)

    # statistics
    srcReadBlkCnt = trgReadBlkCnt = srcCopyBlkCnt = trgCopyBlkCnt = 0
    srcReadByteCnt = trgReadByteCnt = srcCopyByteCnt = trgCopyByteCnt = 0

    while patchHnd.tell() < patchSize - 3 * 4:
        lengthAndAction = bps_read_int(patchHnd)
        (length, action) = ((lengthAndAction >> 2) + 1, lengthAndAction & 3)

        if action == 0:
            # "SourceRead" - copy from same address in source
            if len(dstData) + length > len(srcData):
                error("SourceRead: tried to read from invalid position in input data")
            dstData.extend(srcData[len(dstData):len(dstData)+length])
            srcReadBlkCnt += 1
            srcReadByteCnt += length
        elif action == 1:
            # "TargetRead" - copy from patch
            dstData.extend(read_bytes(length, patchHnd))
            trgReadBlkCnt += 1
            trgReadByteCnt += length
        elif action == 2:
            # "SourceCopy" - copy from any address in source
            srcOffset += bps_decode_signed(bps_read_int(patchHnd))
            if srcOffset < 0 or srcOffset + length > len(srcData):
                error("SourceCopy: tried to read from invalid position in input data")
            dstData.extend(srcData[srcOffset:srcOffset+length])
            srcOffset += length
            srcCopyBlkCnt += 1
            srcCopyByteCnt += length
        else:
            # "TargetCopy" - copy from any address in target
            dstOffset += bps_decode_signed(bps_read_int(patchHnd))
            if not 0 <= dstOffset < len(dstData):
                error("TargetCopy: tried to read from invalid position in output data")
            # can't copy all in one go because newly-added bytes may also be read
            for i in range(length):
                dstData.append(dstData[dstOffset])
                dstOffset += 1
            trgCopyBlkCnt += 1
            trgCopyByteCnt += length

    if verbose:
        print(
            f"{srcReadByteCnt}/{trgReadByteCnt}/{srcCopyByteCnt}/{trgCopyByteCnt} bytes in "
            f"{srcReadBlkCnt}/{trgReadBlkCnt}/{srcCopyBlkCnt}/{trgCopyBlkCnt} blocks of type "
            "SourceRead/TargetRead/SourceCopy/TargetCopy"
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
        error("not a BPS file")
    if id_[3:] != b"1":
        warn("possibly unsupported version of BPS")

    # header - file sizes
    hdrSrcSize = bps_read_int(patchHnd)
    hdrDstSize = bps_read_int(patchHnd)
    if args.verbose:
        print(f"expected file sizes: input={hdrSrcSize}, output={hdrDstSize}")
    if hdrSrcSize != len(srcData):
        warn(f"input file size should be {hdrSrcSize}")

    # header - metadata
    metadataSize = bps_read_int(patchHnd)
    if metadataSize:
        metadata = read_bytes(metadataSize, patchHnd)
        if args.verbose:
            print("metadata:", metadata.decode("ascii", errors="replace"))
    elif args.verbose:
        print("no metadata")

    # create output data by repeatedly appending data
    dstData = bps_decode_blocks(srcData, patchHnd, args.verbose)

    # validate output size
    if hdrDstSize != len(dstData):
        warn(f"output file size should be {hdrDstSize}")

    # validate CRCs from footer
    footer = read_bytes(3 * 4, patchHnd)
    expectedCrcs = tuple(struct.unpack("<L", footer[i:i+4])[0] for i in (0, 4, 8))
    if args.verbose:
        print("expected CRCs: input={:08x}, output={:08x}, patch={:08x}".format(*expectedCrcs))
    if expectedCrcs[0] != crc32(srcData):
        warn("input file CRC mismatch")
    if expectedCrcs[1] != crc32(dstData):
        warn("output file CRC mismatch")
    if expectedCrcs[2] != patchCrc:
        warn("patch file CRC mismatch")

    return dstData

# -------------------------------------------------------------------------------------------------

def ips_decode_int(bytes_):
    # decode an IPS integer (unsigned, most significant byte first)
    return sum(b << (8 * i) for (i, b) in enumerate(bytes_[::-1]))

def ips_generate_blocks(hnd):
    # read IPS file starting from after header
    # generate each block as (offset, length, is_RLE, data); for RLE blocks, data is one byte

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
                warn("RLE block has less than three bytes; suboptimal encoding or corrupt patch?")
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

    if args.input_crc is not None and int(args.input_crc, 16) != crc32(data):
        warn(f"input file CRC mismatch")

    patchHnd.seek(0)

    if read_bytes(5, patchHnd) != b"PATCH":
        error("not an IPS file")

    rleBlockCnt = nonRleBlockCnt = rleByteCnt = nonRleByteCnt = 0  # statistics

    for (offset, length, isRle, blockData) in ips_generate_blocks(patchHnd):
        if offset > len(data):
            error("tried to write past end of data")
        data[offset:offset+length] = length * blockData if isRle else blockData
        if isRle:
            rleBlockCnt += 1
            rleByteCnt += length
        else:
            nonRleBlockCnt += 1
            nonRleByteCnt += length

    if args.verbose:
        print(
            f"{rleByteCnt}/{nonRleByteCnt}/{rleByteCnt+nonRleByteCnt} bytes "
            f"in {rleBlockCnt}/{nonRleBlockCnt}/{rleBlockCnt+nonRleBlockCnt} blocks "
            "of type RLE/non-RLE/any"
        )

    if args.output_crc is not None and int(args.output_crc, 16) != crc32(data):
        warn(f"output file CRC mismatch")

    return data

# -------------------------------------------------------------------------------------------------

def main():
    args = parse_args()

    # create patched data
    try:
        with open(args.orig_file, "rb") as origHnd, open(args.patch_file, "rb") as patchHnd:
            if get_ext(args.patch_file) == ".bps":
                patchedData = bps_apply(origHnd, patchHnd, args)
            else:
                patchedData = ips_apply(origHnd, patchHnd, args)
    except OSError:
        error("error reading input files")

    # write patched data
    try:
        with open(args.output_file, "wb") as handle:
            handle.seek(0)
            handle.write(patchedData)
    except OSError:
        error("error writing output file")

main()
