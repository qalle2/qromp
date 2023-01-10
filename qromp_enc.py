import argparse, os, struct, sys
from zlib import crc32

BPS_SOURCE_READ = 0
BPS_TARGET_READ = 1

def error(msg):
    sys.exit(f"Error: {msg}")

def get_ext(path):
    return os.path.splitext(path)[1].lower()  # e.g. "/FILE.EXT" -> ".ext"

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's ROM Patch Creator. Creates a BPS/IPS patch from "
        "the differences of two files. Notes: does not support files of "
        "different size; the BPS encoder is inefficient."
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print more info."
    )
    parser.add_argument(
        "-u", "--max-unchanged", type=int, default=1,
        help="Maximum number of consecutive unchanged bytes to store. 0-10, "
        "default=1. Other values may reduce patch size."
    )
    parser.add_argument(
        "-r", "--ips-min-rle-length", type=int, default=6,
        help="Only use RLE encoding for at least this many repeats in IPS "
        "patches. 1-10, default=6. Other values may reduce patch size."
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

    if not 0 <= args.max_unchanged <= 10:
        error("invalid '--max-unchanged' value")
    if not 1 <= args.ips_min_rle_length <= 10:
        error("invalid '--ips-min-rle-length' value")
    if get_ext(args.patch_file) not in (".bps", ".ips"):
        error("unsupported patch file format")

    if not os.path.isfile(args.orig_file):
        error("original file not found")
    if not os.path.isfile(args.modified_file):
        error("modified file not found")
    if os.path.exists(args.patch_file):
        error("output file already exists")

    return args

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
        elif start is not None and maxLen is not None \
        and pos - start == maxLen:
            # end a block and start a new one
            yield (start, pos - start)
            start = pos

    if start is not None:
        # end the last block
        yield (start, len(data1) - start)

def generate_optimized_blocks(data1, data2, maxGap, maxLen=None):
    # get ((start, length), ...) of blocks that differ, with some blocks
    # possibly merged;
    # maxGap: maximum number of unchanged bytes between two merged blocks
    # maxLen: maximum length of merged blocks

    blockBuf = []  # blocks not generated yet
    for (start, length) in generate_blocks(data1, data2, maxLen):
        blockBuf.append((start, length))
        # if gap between last two blocks is more than one byte
        # or if the whole buffer is too large...
        if len(blockBuf) >= 2 and (
            blockBuf[-1][0] - sum(blockBuf[-2]) > maxGap
            or (
                maxLen is not None
                and sum(blockBuf[-1]) - blockBuf[0][0] > maxLen
            )
        ):
            # ...output all but the last block as one and delete from buffer
            yield (blockBuf[0][0], sum(blockBuf[-2]) - blockBuf[0][0])
            blockBuf = blockBuf[-1:]

    if blockBuf:
        # output remaining blocks
        yield (blockBuf[0][0], sum(blockBuf[-1]) - blockBuf[0][0])

# -----------------------------------------------------------------------------

def bps_encode_int(n):
    # convert a nonnegative integer into BPS format; return bytes
    # final byte has MSB set, all other bytes have MSB clear
    # e.g. b"\x12\x34\x89" = (0x12<<0) + ((0x34+1)<<7) + ((0x09+1)<<14)
    # = 0x29a92

    encoded = bytearray()
    while True:
        if n <= 0x7f:
            encoded.append(n | 0x80)
            break
        encoded.append(n & 0x7f)
        n = (n >> 7) - 1
    return bytes(encoded)

def bps_create(handle1, handle2, args):
    # create a BPS patch from the differences of handle1 and handle2;
    # generate patch data except for patch CRC at the end;
    # note: inefficient; doesn't use the "SourceCopy" and "TargetCopy" actions
    # at all

    handle1.seek(0)
    data1 = handle1.read()
    handle2.seek(0)
    data2 = handle2.read()

    # header (id, source/target file size, metadata size)
    yield b"BPS1" + b"".join(
        bps_encode_int(n) for n in (len(data1), len(data2), 0)
    )

    srcRdBlkCnt = srcRdByteCnt = trgRdBlkCnt = trgRdByteCnt = 0  # statistics

    #if args.verbose:
    #print("Blocks (type, address in original file, length in original file):")

    # create patch data
    nextPos = 0  # next position to encode
    for (start, length) in generate_optimized_blocks(
        data1, data2, args.max_unchanged
    ):
        if start > nextPos:
            # unchanged bytes since the last block that differs
            unchgdLen = start - nextPos
            yield bps_encode_int(((unchgdLen - 1) << 2) | BPS_SOURCE_READ)
            srcRdBlkCnt += 1
            srcRdByteCnt += unchgdLen
            #if args.verbose:
            #print(f"SourceRead 0x{nextPos:x} {unchgdLen}")
        # a block that differs
        yield bps_encode_int(((length - 1) << 2) | BPS_TARGET_READ)
        yield data2[start:start+length]
        nextPos = start + length
        trgRdBlkCnt += 1
        trgRdByteCnt += length
        #if args.verbose:
        #print(f"TargetRead 0x{start:x} {length}")
    if len(data1) > nextPos:
        # unchanged bytes after the last block that differs
        unchgdLen = len(data1) - nextPos
        yield bps_encode_int(((unchgdLen - 1) << 2) | BPS_SOURCE_READ)
        srcRdBlkCnt += 1
        srcRdByteCnt += unchgdLen
        #if args.verbose:
        #print(f"SourceRead 0x{nextPos:x} {unchgdLen}")

    if args.verbose:
        print(
            f"Total: {srcRdByteCnt}/{trgRdByteCnt} bytes in "
            f"{srcRdBlkCnt}/{trgRdBlkCnt} blocks of type SourceRead/TargetRead"
        )

    # footer except patch CRC (source/target file CRC)
    yield struct.pack("<2L", crc32(data1), crc32(data2))

# -----------------------------------------------------------------------------

def ips_encode_int(n, byteCnt):
    # encode an IPS integer (unsigned, most significant byte first)

    assert n < 0x100 ** byteCnt
    return bytes((n >> s) & 0xff for s in range((byteCnt - 1) * 8, -8, -8))

def ips_generate_subblocks(data1, data2, args):
    # split blocks that differ into RLE and non-RLE subblocks;
    # generate (start, length, is_RLE)

    for (blkStart, blkLen) in generate_optimized_blocks(
        data1, data2, args.max_unchanged, 0xffff
    ):
        block = data2[blkStart:blkStart+blkLen]
        # split block into RLE/non-RLE subblocks; e.g. ABBCCCCDDDDDEF -> ABB,
        # 4*C, 5*D, EF
        # note: subPos has an extra value at the end for wrapping things up
        subStart = 0  # start position of subblock within block
        for subPos in range(blkLen + 1):
            # if this byte differs from the previous one or is the last one...
            if 0 < subPos < blkLen and block[subPos] != block[subPos-1] \
            or subPos == blkLen:
                # output 0-2 subblocks (non-RLE, RLE, both in that order, or
                # neither); the RLE part is the sequence of identical bytes at
                # the end of the substring
                nonRleLen = len(
                    block[subStart:subPos].rstrip(block[subPos-1:subPos])
                )
                rleLen = subPos - subStart - nonRleLen
                if rleLen < args.ips_min_rle_length:
                    nonRleLen += rleLen
                    rleLen = 0
                if rleLen or (nonRleLen and subPos == blkLen):
                    if nonRleLen:
                        yield (blkStart + subStart, nonRleLen, False)
                    if rleLen:
                        yield (blkStart + subStart + nonRleLen, rleLen, True)
                    subStart = subPos

def ips_create(handle1, handle2, args):
    # create an IPS patch from the differences of handle1 and handle2; generate
    # patch data
    # note: has the "EOF" address (0x454f46) bug

    handle1.seek(0)
    origData = handle1.read()
    if len(origData) > 2 ** 24:
        error(
            "creating an IPS patch from files larger than 16 MiB is not "
            "supported"
        )

    handle2.seek(0)
    newData = handle2.read()

    yield b"PATCH"  # file format id

    rleBlockCnt = nonRleBlockCnt = rleByteCnt = nonRleByteCnt = 0  # statistics

    #if args.verbose:
    #print("Blocks (type, address in original file, length in original file):")

    for (start, length, isRle) in ips_generate_subblocks(
        origData, newData, args
    ):
        #if args.verbose:
        #print(("RLE" if isRle else "non-RLE") + f" 0x{start:x} {length}")
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
            f"Total: {rleByteCnt}/{nonRleByteCnt} bytes in "
            f"{rleBlockCnt}/{nonRleBlockCnt} blocks of type RLE/non-RLE"
        )

# -----------------------------------------------------------------------------

def main():
    args = parse_args()

    # create patch data
    try:
        with open(args.orig_file, "rb") as handle1, \
        open(args.modified_file, "rb") as handle2:
            if handle1.seek(0, 2) != handle2.seek(0, 2):
                error("input files of different size are not supported")
            patch = bytearray()
            if get_ext(args.patch_file) == ".bps":
                for bytes_ in bps_create(handle1, handle2, args):
                    patch.extend(bytes_)
                patch.extend(struct.pack("<L", crc32(patch)))
            else:
                for bytes_ in ips_create(handle1, handle2, args):
                    patch.extend(bytes_)
    except OSError:
        error("could not read some of the input files")

    # write patch data
    try:
        with open(args.patch_file, "wb") as handle:
            handle.seek(0)
            handle.write(patch)
            if args.verbose:
                print(f"{handle.tell()} bytes written")
    except OSError:
        error("could not write output file")

main()
