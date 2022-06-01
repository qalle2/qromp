import argparse, os, struct, sys
from zlib import crc32

BPS_SOURCE_READ = 0
BPS_TARGET_READ = 1
BPS_SOURCE_COPY = 2
BPS_TARGET_COPY = 3
IPS_MIN_RLE_LEN = 6

def error(msg):
    sys.exit(f"Error: {msg}")

def get_ext(path):
    return os.path.splitext(path)[1].lower()  # e.g. "/FILE.EXT" -> ".ext"

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's ROM Patch Creator. Creates a BPS/IPS patch from the differences of "
        "two files. Note: the BPS encoder is inefficient."
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print more info."
    )

    parser.add_argument(
        "orig_file", help="The original file to read."
    )
    parser.add_argument(
        "modified_file", help="The file to read and compare against orig_file."
    )
    parser.add_argument(
        "patch_file", help="The patch file to write (.bps/.ips)."
    )

    args = parser.parse_args()

    if get_ext(args.patch_file) not in (".bps", ".ips"):
        error("unsupported patch file format")

    if not os.path.isfile(args.orig_file):
        error("original file not found")
    if not os.path.isfile(args.modified_file):
        error("modified file not found")
    if os.path.exists(args.patch_file):
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

def generate_blocks(data1, data2, maxLen=None):
    # generate (start, length) of blocks that differ; maxLen = maximum length

    start = None  # start position of current block

    for (pos, (byte1, byte2)) in enumerate(zip(data1, data2)):
        if start is None and byte1 != byte2:
            # start a block
            start = pos
        elif start is not None and byte1 == byte2:
            # end a block
            yield (start, pos - start)
            start = None
        elif start is not None and maxLen is not None and pos - start == maxLen:
            # end a block and start a new one
            yield (start, pos - start)
            start = pos

    if start is not None:
        # end the last block
        yield (start, len(data1) - start)

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
    for (start, length) in generate_blocks(data1, data2):
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
            f"{srcRdByteCnt}/{trgRdByteCnt} bytes in {srcRdBlkCnt}/{trgRdBlkCnt} blocks of type "
            "SourceRead/TargetRead"
        )

    # footer except patch CRC (source/target file CRC)
    yield struct.pack("<2L", crc32(data1), crc32(data2))

# -------------------------------------------------------------------------------------------------

def ips_encode_int(n, byteCnt):
    # encode an IPS integer (unsigned, most significant byte first)
    assert n < 0x100 ** byteCnt
    return bytes((n >> s) & 0xff for s in range((byteCnt - 1) * 8, -8, -8))

def ips_enc_generate_subblocks(data1, data2):
    # split blocks that differ into RLE and non-RLE subblocks; generate (start, length, is_RLE)

    for (blkStart, blkLen) in generate_blocks(data1, data2, 0xffff):
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
            f"{rleByteCnt}/{nonRleByteCnt} bytes in {rleBlockCnt}/{nonRleBlockCnt} blocks of "
            "type RLE/non-RLE"
        )

# -------------------------------------------------------------------------------------------------

def main():
    args = parse_args()

    try:
        with open(args.orig_file, "rb") as inHnd1, \
        open(args.modified_file, "rb") as inHnd2, \
        open(args.patch_file, "wb") as patchHnd:
            patchHnd.seek(0)
            if get_ext(args.patch_file) == ".bps":
                patchCrc = 0
                for bytes_ in bps_create(inHnd1, inHnd2, args):
                    patchHnd.write(bytes_)
                    patchCrc = crc32(bytes_, patchCrc)
                patchHnd.write(struct.pack("<L", patchCrc))
            else:
                for bytes_ in ips_create(inHnd1, inHnd2, args):
                    patchHnd.write(bytes_)
    except OSError:
        error("could not read the input files or write the output file")

main()
