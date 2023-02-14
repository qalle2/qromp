import argparse, os, struct, sys, time
from zlib import crc32

# actions (types of BPS blocks); note that "source" and "target" here refer to
# encoder's *input* files
BPS_SOURCE_READ = 0
BPS_TARGET_READ = 1
BPS_SOURCE_COPY = 2
BPS_TARGET_COPY = 3  # unused atm

# number of dots in BPS progress indicator
BPS_PROGRESS_DOT_COUNT = 100

# minimum length of IPS RLE blocks (this is a good value when --ips-max-unchg
# is 1 or 2)
IPS_MIN_RLE_LEN = 9

IPS_MAX_BLK_LEN = 0xffff

def get_file_ext(path):
    return os.path.splitext(path)[1].lower()  # e.g. "/FILE.EXT" -> ".ext"

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's ROM Patch Creator. Creates BPS/IPS patch from "
        "differences of two files. Both encoders are somewhat inefficient; "
        "BPS encoder is also slow. BPS encoder prints progress indicator "
        f"({BPS_PROGRESS_DOT_COUNT} dots)."
    )

    parser.add_argument(
        "--bps-min-copy", type=int, default=4,
        help="(BPS only.) Minimum length of substring to copy from original "
        "file. 1-20, default=4. Affects efficiency. Larger=faster."
    )
    parser.add_argument(
        "--ips-max-unchg", type=int, default=1,
        help="(IPS only.) Maximum length of unchanged substring to store. "
        "0-10, default=1. Affects efficiency."
    )

    parser.add_argument(
        "orig_file", help="Original file to read."
    )
    parser.add_argument(
        "modified_file",
        help="File to read and compare against orig_file. If creating IPS "
        "patch, modified_file must be at least as large as orig_file."
    )
    parser.add_argument(
        "patch_file", help="Patch file to write (.bps/.ips)."
    )

    args = parser.parse_args()

    if not 1 <= args.bps_min_copy <= 20:
        sys.exit("Invalid '--bps-min-copy' value.")
    if not 0 <= args.ips_max_unchg <= 10:
        sys.exit("Invalid '--ips-max-unchg' value.")
    if get_file_ext(args.patch_file) not in (".bps", ".ips"):
        sys.exit("Unsupported patch file format.")

    if not os.path.isfile(args.orig_file):
        sys.exit("Original file not found.")
    if not os.path.isfile(args.modified_file):
        sys.exit("Modified file not found.")
    if os.path.exists(args.patch_file):
        sys.exit("Output file already exists.")

    return args

# -----------------------------------------------------------------------------

def bps_encode_int(n):
    # convert a nonnegative integer into BPS format; return bytes;
    # final byte has MSB set, all other bytes have MSB clear;
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

def bps_encode_signed(n):
    # encode a signed BPS integer
    return bps_encode_int((abs(n) << 1) | (1 if n < 0 else 0))

def bps_block_start(length, action):
    # encode start of block
    return bps_encode_int(((length - 1) << 2) | action)

def find_longest_prefix(str1, str2):
    # return length of longest prefix of str1 that occurs anywhere in str2
    # using binary search

    minLen = 0  # lower limit found
    maxLen = min(len(str1), len(str2))  # upper limit found

    while True:
        if minLen == maxLen:
            return minLen
        avgLen = (minLen + maxLen + 1) // 2
        if str1[:avgLen] in str2:
            minLen = avgLen
        else:
            maxLen = avgLen - 1

def bps_find_substrings(str1, str2, minCopyLen):
    # find substrings in str1 that occur anywhere in str2;
    # generate (start_in_str1, length);
    # e.g. "abcd", "cxab" -> (0, 2), (2, 1)
    # almost all the time is spent here (almost 4 min for largest test file)

    pos1 = 0  # position in str1
    dotsPrinted = 0

    while pos1 < len(str1):
        # print progress indicator
        dotsSoFar = pos1 * BPS_PROGRESS_DOT_COUNT // len(str1)
        if dotsSoFar > dotsPrinted:
            print((dotsSoFar - dotsPrinted) * ".", end="", flush=True)
            dotsPrinted = dotsSoFar
        # speed up by checking for minimum length first
        if len(str1) - pos1 >= minCopyLen \
        and str1[pos1:pos1+minCopyLen] in str2:
            prefixLen = find_longest_prefix(str1[pos1:], str2)
            yield (pos1, prefixLen)
            pos1 += prefixLen
        else:
            pos1 += 1

    print((BPS_PROGRESS_DOT_COUNT - dotsPrinted) * ".")

def bps_create(handle1, handle2, minCopyLen):
    # create a BPS patch from the difference of two files;
    # generate patch data except for patch CRC at the end;
    # note: doesn't use the BPS_TARGET_COPY action at all

    handle1.seek(0)
    data1 = handle1.read()
    handle2.seek(0)
    data2 = handle2.read()

    # header (id, source/target file size, metadata size)
    yield b"BPS1" + b"".join(
        bps_encode_int(n) for n in (len(data1), len(data2), 0)
    )

    # find identical substrings: [(start_in_data2, length), ...]
    data2Substrs = list(
        s for s in bps_find_substrings(data2, data1, minCopyLen)
    )

    # create patch data
    data2Pos = 0  # data2 read position
    srcOffset = 0  # used by BPS_SOURCE_COPY
    for (start, length) in data2Substrs:
        if start > data2Pos:
            # differing data since previous identical substring
            yield bps_block_start(start - data2Pos, BPS_TARGET_READ)
            yield data2[data2Pos:start]
        # identical substring
        data1Pos = data1.index(data2[start:start+length])
        if data1Pos == start:
            yield bps_block_start(length, BPS_SOURCE_READ)
        else:
            yield bps_block_start(length, BPS_SOURCE_COPY)
            yield bps_encode_signed(data1Pos - srcOffset)
            srcOffset = data1Pos + length
        data2Pos = start + length

    if len(data2) > data2Pos:
        # differing data after final identical substring
        yield bps_block_start(len(data2) - data2Pos, BPS_TARGET_READ)
        yield data2[data2Pos:]

    # footer except patch CRC (source/target file CRC)
    yield struct.pack("<2L", crc32(data1), crc32(data2))

# -----------------------------------------------------------------------------

def ips_get_blocks(data1, data2):
    # generate (start, length) of blocks that differ

    start = -1  # start position of current block (-1 = none)

    for (pos, (byte1, byte2)) in enumerate(zip(data1, data2)):
        if start == -1 and byte1 != byte2:
            # start a block
            start = pos
        elif start != -1 and byte1 == byte2:
            # end a block
            yield (start, pos - start)
            start = -1
        elif start != -1 and pos - start == IPS_MAX_BLK_LEN:
            # end a block and start a new one
            yield (start, pos - start)
            start = pos

    if start != -1:
        # end the last block shared by both files
        yield (start, len(data1) - start)

    # data after end of first file, if any
    for start in range(len(data1), len(data2), IPS_MAX_BLK_LEN):
        yield (start, min(len(data2) - start, IPS_MAX_BLK_LEN))

def ips_get_optimized_blocks(data1, data2, maxGap):
    # generate (start, length) of blocks that differ, with some blocks merged;
    # maxGap: maximum number of unchanged bytes between two merged blocks

    blockBuf = []  # blocks not generated yet
    for (start, length) in ips_get_blocks(data1, data2):
        blockBuf.append((start, length))
        # if gap between last two blocks is too large
        # or the whole buffer is too large...
        if len(blockBuf) >= 2 and (
            blockBuf[-1][0] - sum(blockBuf[-2]) > maxGap
            or sum(blockBuf[-1]) - blockBuf[0][0] > IPS_MAX_BLK_LEN
        ):
            # ...output all but the last block as one and delete from buffer
            yield (blockBuf[0][0], sum(blockBuf[-2]) - blockBuf[0][0])
            blockBuf = blockBuf[-1:]

    if blockBuf:
        # output remaining blocks
        yield (blockBuf[0][0], sum(blockBuf[-1]) - blockBuf[0][0])

def ips_get_subblocks(data1, data2, maxUnchanged):
    # split blocks that differ into RLE and non-RLE subblocks;
    # generate (start, length, is_RLE)

    for (blkStart, blkLen) in ips_get_optimized_blocks(
        data1, data2, maxUnchanged
    ):
        block = data2[blkStart:blkStart+blkLen]

        # split block into RLE/non-RLE subblocks;
        # e.g. ABBCCCCDDDDDEF -> ABB, 4*C, 5*D, EF
        subStart = 0  # start position of subblock within block

        for subPos in range(1, blkLen):
            # if this byte differs from the previous one...
            if block[subPos] != block[subPos-1]:
                # output 0-2 subblocks (non-RLE, RLE, both in that order, or
                # neither); the RLE part is the sequence of identical bytes at
                # the end of the substring
                nonRleLen = len(
                    block[subStart:subPos].rstrip(block[subPos-1:subPos])
                )
                rleLen = subPos - subStart - nonRleLen
                # don't create short RLE blocks
                if rleLen < IPS_MIN_RLE_LEN:
                    nonRleLen += rleLen
                    rleLen = 0
                else:
                    if nonRleLen:
                        yield (blkStart + subStart, nonRleLen, False)
                    yield (blkStart + subStart + nonRleLen, rleLen, True)
                    subStart = subPos

        # same for the last byte in block
        nonRleLen = len(block[subStart:].rstrip(block[-1:]))
        rleLen = blkLen - subStart - nonRleLen
        if rleLen < IPS_MIN_RLE_LEN:
            nonRleLen += rleLen
            rleLen = 0
        if nonRleLen:
            yield (blkStart + subStart, nonRleLen, False)
        if rleLen:
            yield (blkStart + subStart + nonRleLen, rleLen, True)

def ips_encode_int(n, byteCnt):
    # encode an IPS integer (unsigned, most significant byte first)
    return bytes((n >> s) & 0xff for s in range((byteCnt - 1) * 8, -8, -8))

def ips_create(handle1, handle2, args):
    # create an IPS patch from the differences of handle1 and handle2;
    # generate patch data; note: has the "EOF" address (0x454f46) bug

    handle1.seek(0)
    origData = handle1.read()
    if len(origData) > 2 ** 24:
        sys.exit(
            "Creating an IPS patch from files larger than 16 MiB is not "
            "supported."
        )

    handle2.seek(0)
    newData = handle2.read()

    yield b"PATCH"  # file format id

    for (start, length, isRle) in ips_get_subblocks(origData, newData, args):
        yield ips_encode_int(start, 3)
        if isRle:
            yield ips_encode_int(0, 2)
            yield ips_encode_int(length, 2)
            yield newData[start:start+1]
        else:
            yield ips_encode_int(length, 2)
            yield newData[start:start+length]

    yield b"EOF"

# -----------------------------------------------------------------------------

def main():
    startTime = time.time()
    args = parse_args()

    # create patch data
    patch = bytearray()
    try:
        with open(args.orig_file, "rb") as handle1, \
        open(args.modified_file, "rb") as handle2:
            if get_file_ext(args.patch_file) == ".bps":
                for bytes_ in bps_create(handle1, handle2, args.bps_min_copy):
                    patch.extend(bytes_)
                patch.extend(struct.pack("<L", crc32(patch)))
            else:
                if handle1.seek(0, 2) > handle2.seek(0, 2):
                    sys.exit(
                        "Second input file must be at least as large as first."
                    )
                for bytes_ in ips_create(handle1, handle2, args.ips_max_unchg):
                    patch.extend(bytes_)
    except OSError:
        sys.exit("Error reading input files.")

    # write patch data
    try:
        with open(args.patch_file, "wb") as handle:
            handle.seek(0)
            handle.write(patch)
    except OSError:
        sys.exit("Error writing output file.")

    print("Time:", format(time.time() - startTime, ".1f"), "s")

main()
