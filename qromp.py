import argparse, os, struct, sys
from zlib import crc32

BPS_SOURCE_READ = 0
BPS_TARGET_READ = 1
BPS_SOURCE_COPY = 2
BPS_TARGET_COPY = 3
IPS_MIN_RLE_LEN = 6

def error(msg):
    sys.exit(f"Error: {msg}")

def warn(msg):
    print("Warning:", msg, file=sys.stderr)

def get_ext(path):
    return os.path.splitext(path)[1].lower()  # e.g. "/FILE.EXT" -> ".ext"

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's ROM Patcher. Applies a BPS/IPS patch to a file or creates a BPS/IPS "
        "patch from the differences of two files. Notes: the BPS encoder is inefficient; the IPS "
        "decoder has the 'EOF' address (0x454f46) bug."
    )

    parser.add_argument(
        "-m", "--mode", type=str, choices=("a", "c"), default="a",
        help="What to do. 'a' (the default): apply a patch file to another file. 'c': create a "
        "patch file."
    )
    parser.add_argument(
        "-i", "--input-crc", type=str,
        help="Expected CRC32 checksum (zlib variety) of input_file1. 8 hexadecimal digits. "
        "Only used when applying an IPS patch."
    )
    parser.add_argument(
        "-o", "--output-crc", type=str,
        help="Expected CRC32 checksum (zlib variety) of output_file. 8 hexadecimal digits. "
        "Only used when applying an IPS patch."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print more info."
    )

    parser.add_argument(
        "input_file1", help="The original, unpatched file to read."
    )
    parser.add_argument(
        "input_file2",
        help="The second file to read. In 'apply patch' mode, the patch file (.bps/.ips). In "
        "'create patch' mode, the file to compare against input_file1."
    )
    parser.add_argument(
        "output_file",
        help="The file to write. In 'apply patch' mode, the patched copy of input_file1. In "
        "'create patch' mode, the patch file (.bps/.ips)."
    )

    args = parser.parse_args()

    try:
        for crc in (args.input_crc, args.output_crc):
            if crc is not None and not 0 <= int(crc, 16) <= 0xffff_ffff:
                raise ValueError
    except ValueError:
        error("invalid CRC32 specified")

    if args.mode == "a" and get_ext(args.input_file2) not in (".bps", ".ips") \
    or args.mode == "c" and get_ext(args.output_file) not in (".bps", ".ips"):
        error("unsupported patch format")

    if not os.path.isfile(args.input_file1):
        error("input file 1 not found")
    if not os.path.isfile(args.input_file2):
        error("input file 2 not found")
    if os.path.exists(args.output_file):
        error("output file already exists")

    return args

def get_file_size(hnd):
    # get file size without disturbing file handle position
    return os.stat(hnd.fileno()).st_size

def read_bytes(n, hnd):
    # return n bytes from handle or exit on EOF
    data = hnd.read(n)
    if len(data) < n:
        error("unexpected end of patch file")
    return data

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
        actionAddr = patchHnd.tell()
        lengthAndAction = bps_read_int(patchHnd)
        (length, action) = ((lengthAndAction >> 2) + 1, lengthAndAction & 3)

        if action == BPS_SOURCE_READ:
            # copy from same address in source
            if len(dstData) + length > len(srcData):
                error("tried to read from invalid position in input data")
            dstData.extend(srcData[len(dstData):len(dstData)+length])
            srcReadBlkCnt += 1
            srcReadByteCnt += length
        elif action == BPS_TARGET_READ:
            # copy from patch
            dstData.extend(read_bytes(length, patchHnd))
            trgReadBlkCnt += 1
            trgReadByteCnt += length
        elif action == BPS_SOURCE_COPY:
            # copy from any address in source
            srcOffset += bps_decode_signed(bps_read_int(patchHnd))
            if srcOffset < 0 or srcOffset + length > len(srcData):
                error("tried to read from invalid position in input data")
            dstData.extend(srcData[srcOffset:srcOffset+length])
            srcOffset += length
            srcCopyBlkCnt += 1
            srcCopyByteCnt += length
        else:
            # "TargetCopy" (copy from any address in target)
            # note: can't copy all in one go because newly-added bytes may also be read
            dstOffset += bps_decode_signed(bps_read_int(patchHnd))
            if dstOffset < 0 or dstOffset >= len(dstData):
                error("tried to read from invalid position in output data")
            for i in range(length):
                dstData.append(dstData[dstOffset])
                dstOffset += 1
            trgCopyBlkCnt += 1
            trgCopyByteCnt += length

    if verbose:
        print(
            f"{srcReadByteCnt}/{trgReadByteCnt}/{srcCopyByteCnt}/{trgCopyByteCnt}/"
            f"{srcReadByteCnt+trgReadByteCnt+srcCopyByteCnt+trgCopyByteCnt} bytes "
            f"in {srcReadBlkCnt}/{trgReadBlkCnt}/{srcCopyBlkCnt}/{trgCopyBlkCnt}/"
            f"{srcReadBlkCnt+trgReadBlkCnt+srcCopyBlkCnt+trgCopyBlkCnt} blocks "
            "of type SourceRead/TargetRead/SourceCopy/TargetCopy/any"
        )

    return dstData

def bps_apply(inHnd1, patchHnd, outHnd, args):
    # apply BPS patch from patchHnd to inHnd1, write patched data to outHnd
    # see https://gist.github.com/khadiwala/32550f44efcc36a5b6a470ff2d4c9c22

    inHnd1.seek(0)
    srcData = inHnd1.read()

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
            print("metadata in hexadecimal:", metadata.hex())
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

    outHnd.seek(0)
    outHnd.write(dstData)

# -------------------------------------------------------------------------------------------------

def bps_encode_int(n):
    # convert a nonnegative integer into BPS format; return bytes
    encoded = bytearray()
    while True:
        if n <= 0x7f:
            encoded.append(n | 0x80)
            break
        encoded.append(n & 0x7f)
        n = (n >> 7) - 1
    return bytes(encoded)

def bps_enc_generate_blocks(data1, data2):
    # generate (start, length) of blocks that differ

    start = None  # start position of current block

    for (pos, (byte1, byte2)) in enumerate(zip(data1, data2)):
        if start is None and byte1 != byte2:
            # start a block
            start = pos
        elif start is not None and byte1 == byte2:
            # end a block
            yield (start, pos - start)
            start = None

    if start is not None:
        # end the last block
        yield (start, len(data1) - start)

def bps_create(inHnd1, inHnd2, args):
    # create a BPS patch from the difference of inHnd1 and inHnd2, generate data to write

    inHnd1.seek(0)
    data1 = inHnd1.read()

    inHnd2.seek(0)
    data2 = inHnd2.read()
    if len(data2) != len(data1):
        error("creating a BPS patch from files of different size is not supported")

    # header (id, source/target file size, metadata size)
    yield b"BPS1" + b"".join(bps_encode_int(n) for n in (len(data1), len(data2), 0))

    srcRdBlkCnt = srcRdByteCnt = trgRdBlkCnt = trgRdByteCnt = 0  # statistics

    # create patch data (TODO: make this more size-efficient)
    nextPos = 0  # next position to encode
    for (start, length) in bps_enc_generate_blocks(data1, data2):
        if start > nextPos:
            # unchanged bytes since the last block that differs
            subblkLen = start - nextPos
            yield bps_encode_int(((subblkLen - 1) << 2) | BPS_SOURCE_READ)
            srcRdBlkCnt += 1
            srcRdByteCnt += subblkLen
        # a block that differs
        yield bps_encode_int(((length - 1) << 2) | BPS_TARGET_READ) + data2[start:start+length]
        nextPos = start + length
        trgRdBlkCnt += 1
        trgRdByteCnt += length
    if len(data1) > nextPos:
        # unchanged bytes after the last block that differs
        subblkLen = len(data1) - nextPos
        yield bps_encode_int(((subblkLen - 1) << 2) | BPS_SOURCE_READ)
        srcRdBlkCnt += 1
        srcRdByteCnt += subblkLen

    if args.verbose:
        print(
            f"{srcRdByteCnt}/{trgRdByteCnt}/{srcRdByteCnt+trgRdByteCnt} bytes "
            f"in {srcRdBlkCnt}/{trgRdBlkCnt}/{srcRdBlkCnt+trgRdBlkCnt} blocks "
            "of type SourceRead/TargetRead/any"
        )

    # footer except patch CRC (source/target file CRC)
    yield struct.pack("<2L", crc32(data1), crc32(data2))

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

def ips_apply(inHnd1, patchHnd, outHnd, args):
    # apply IPS patch from patchHnd to inHnd1, write patched data to outHnd
    # see https://zerosoft.zophar.net/ips.php
    # note: the patch is allowed to append data to the end of the file

    inHnd1.seek(0)
    dataToPatch = inHnd1.read()

    if args.input_crc is not None and int(args.input_crc, 16) != crc32(dataToPatch):
        warn(f"input file CRC mismatch")

    dataToPatch = bytearray(dataToPatch)
    patchHnd.seek(0)

    if read_bytes(5, patchHnd) != b"PATCH":
        error("not an IPS file")

    rleBlockCnt = 0
    nonRleBlockCnt = 0
    rleByteCnt = 0
    nonRleByteCnt = 0
    for (offset, length, isRle, data) in ips_generate_blocks(patchHnd):
        if offset > len(dataToPatch):
            error("tried to write past end of output file")
        dataToPatch[offset:offset+length] = length * data if isRle else data
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

    if args.output_crc is not None and int(args.output_crc, 16) != crc32(dataToPatch):
        warn(f"output file CRC mismatch")

    outHnd.seek(0)
    outHnd.write(dataToPatch)

# -------------------------------------------------------------------------------------------------

def ips_encode_int(n, byteCnt):
    # encode an IPS integer (unsigned, most significant byte first)
    assert n < 0x100 ** byteCnt
    return bytes((n >> s) & 0xff for s in range((byteCnt - 1) * 8, -8, -8))

def ips_enc_generate_blocks(data1, data2):
    # generate (start, length) of blocks that differ; length <= 0xffff; address may be "EOF"
    # TODO: perhaps handle splits in a more efficient manner?

    start = None  # start position of current block

    for (pos, (byte1, byte2)) in enumerate(zip(data1, data2)):
        if start is None and byte1 != byte2:
            # start a block
            start = pos
        elif start is not None and (byte1 == byte2 or pos - start == 0xffff):
            # end a block
            yield (start, pos - start)
            start = (None if byte1 == byte2 else pos)

    if start is not None:
        # end the last block
        yield (start, len(data1) - start)

def ips_enc_generate_subblocks(data1, data2):
    # split blocks that differ into RLE and non-RLE subblocks; generate (start, length, is_RLE)

    for (blkStart, blkLen) in ips_enc_generate_blocks(data1, data2):
        block = data2[blkStart:blkStart+blkLen]
        # split block into RLE/non-RLE subblocks; e.g. ABBCCCCDDDDDEF -> ABB, 4*C, 5*D, EF
        # note: subPos has an extra value at the end for wrapping things up
        subStart = 0  # start position of subblock within block
        for subPos in range(blkLen + 1):
            # if this byte differs from the previous one or is the last one...
            if 0 < subPos < blkLen and block[subPos] != block[subPos-1] or subPos == blkLen:
                # output 0-2 subblocks (non-RLE, RLE, both in that order, or neither);
                # the RLE part is the sequence of identical bytes at the end of the substring
                nonRleLen = len(block[subStart:subPos].rstrip(block[subPos-1:subPos]))
                rleLen = subPos - subStart - nonRleLen
                if rleLen < IPS_MIN_RLE_LEN:
                    nonRleLen += rleLen
                    rleLen = 0
                if rleLen or (nonRleLen and subPos == blkLen):
                    if nonRleLen:
                        yield (blkStart + subStart, nonRleLen, False)
                    if rleLen:
                        yield (blkStart + subStart + nonRleLen, rleLen, True)
                    subStart = subPos

def ips_create(inHnd1, inHnd2, args):
    # create an IPS patch from the difference of inHnd1 and inHnd2, generate data to write
    # notes:
    # - does not store any unchanged bytes even if doing so would reduce the file size
    # - has the "EOF" address (0x454f46) bug

    inHnd1.seek(0)
    origData = inHnd1.read()
    if len(origData) > 2 ** 24:
        error("creating an IPS patch from files larger than 16 MiB is not supported")

    inHnd2.seek(0)
    newData = inHnd2.read()
    if len(newData) != len(origData):
        error("creating an IPS patch from files of different size is not supported")

    yield b"PATCH"  # file format id

    rleBlockCnt = nonRleBlockCnt = rleByteCnt = nonRleByteCnt = 0  # statistics

    for (start, length, isRle) in ips_enc_generate_subblocks(origData, newData):
        yield ips_encode_int(start, 3)
        if isRle:
            yield ips_encode_int(0, 2)
            yield ips_encode_int(length, 2)
            yield newData[start:start+1]
            rleBlockCnt += 1
            rleByteCnt += length
        else:
            yield ips_encode_int(length, 2)
            yield newData[start:start+length]
            nonRleBlockCnt += 1
            nonRleByteCnt += length

    yield b"EOF"

    if args.verbose:
        print(
            f"{rleByteCnt}/{nonRleByteCnt}/{rleByteCnt+nonRleByteCnt} bytes "
            f"in {rleBlockCnt}/{nonRleBlockCnt}/{rleBlockCnt+nonRleBlockCnt} blocks "
            "of type RLE/non-RLE/any"
        )

# -------------------------------------------------------------------------------------------------

def main():
    args = parse_args()

    try:
        with open(args.input_file1, "rb") as inHnd1, \
        open(args.input_file2, "rb") as inHnd2, \
        open(args.output_file, "wb") as outHnd:
            if args.mode == "a":
                # apply a patch
                if get_ext(args.input_file2) == ".bps":
                    bps_apply(inHnd1, inHnd2, outHnd, args)
                else:
                    ips_apply(inHnd1, inHnd2, outHnd, args)
            else:
                # create a patch
                outHnd.seek(0)
                if get_ext(args.output_file) == ".bps":
                    patchCrc = 0
                    for bytes_ in bps_create(inHnd1, inHnd2, args):
                        outHnd.write(bytes_)
                        patchCrc = crc32(bytes_, patchCrc)
                    outHnd.write(struct.pack("<L", patchCrc))
                else:
                    for bytes_ in ips_create(inHnd1, inHnd2, args):
                        outHnd.write(bytes_)
    except OSError:
        error("could not read the input files or write the output file")

main()
