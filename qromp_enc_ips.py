import argparse, os, sys

MAX_BLK_LEN = 0xffff  # maximum length of any block

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's IPS Patch Creator. Creates an IPS patch from the "
        "differences of two files. Somewhat inefficient."
    )

    parser.add_argument(
        "--min-rle-len", type=int, default=9,
        help="Minimum length of blocks to encode as RLE. 1-16, default=9. "
        "Affects efficiency."
    )
    parser.add_argument(
        "--max-unchg-len", type=int, default=1,
        help="Maximum length of unchanged substring to store. 0-16, "
        "default=1. Affects efficiency."
    )

    parser.add_argument(
        "orig_file", help="Original file to read."
    )
    parser.add_argument(
        "modified_file",
        help="File to read and compare against orig_file. Must be at least as "
        "large as orig_file."
    )
    parser.add_argument(
        "patch_file", help="Patch file to write (.ips)."
    )

    args = parser.parse_args()

    if not 1 <= args.min_rle_len <= 16:
        sys.exit("Invalid '--min-rle-len' value.")
    if not 0 <= args.max_unchg_len <= 16:
        sys.exit("Invalid '--max-unchg-len' value.")

    if not os.path.isfile(args.orig_file):
        sys.exit("Original file not found.")
    if not os.path.isfile(args.modified_file):
        sys.exit("Modified file not found.")
    if os.path.exists(args.patch_file):
        sys.exit("Output file already exists.")

    return args

def get_blocks(data1, data2):
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
        elif start != -1 and pos - start == MAX_BLK_LEN:
            # end a block and start a new one
            yield (start, pos - start)
            start = pos

    if start != -1:
        # end the last block shared by both files
        yield (start, len(data1) - start)

    # data after end of first file, if any
    for start in range(len(data1), len(data2), MAX_BLK_LEN):
        yield (start, min(len(data2) - start, MAX_BLK_LEN))

def get_optimized_blocks(data1, data2, args):
    # generate (start, length) of blocks that differ, with some blocks merged

    blockBuf = []  # blocks not generated yet
    for (start, length) in get_blocks(data1, data2):
        blockBuf.append((start, length))
        # if gap between last two blocks is too large
        # or the whole buffer is too large...
        if len(blockBuf) >= 2 and (
            blockBuf[-1][0] - sum(blockBuf[-2]) > args.max_unchg_len
            or sum(blockBuf[-1]) - blockBuf[0][0] > MAX_BLK_LEN
        ):
            # ...output all but the last block as one and delete from buffer
            yield (blockBuf[0][0], sum(blockBuf[-2]) - blockBuf[0][0])
            blockBuf = blockBuf[-1:]

    if blockBuf:
        # output remaining blocks
        yield (blockBuf[0][0], sum(blockBuf[-1]) - blockBuf[0][0])

def get_subblocks(data1, data2, args):
    # split blocks that differ into RLE and non-RLE subblocks;
    # generate (start, length, is_RLE)

    for (blkStart, blkLen) in get_optimized_blocks(data1, data2, args):
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
                if rleLen < args.min_rle_len:
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
        if rleLen < args.min_rle_len:
            nonRleLen += rleLen
            rleLen = 0
        if nonRleLen:
            yield (blkStart + subStart, nonRleLen, False)
        if rleLen:
            yield (blkStart + subStart + nonRleLen, rleLen, True)

def encode_int(n, byteCnt):
    # encode an IPS integer (unsigned, most significant byte first)
    return bytes((n >> s) & 0xff for s in range((byteCnt - 1) * 8, -8, -8))

def create_ips(handle1, handle2, args):
    # create an IPS patch from the differences of handle1 and handle2;
    # generate patch data; note: has the "EOF" address (0x454f46) bug;
    # see "ips-spec.txt" for file format specs

    handle1.seek(0)
    origData = handle1.read()
    handle2.seek(0)
    newData = handle2.read()

    yield b"PATCH"  # file format id

    for (start, length, isRle) in get_subblocks(origData, newData, args):
        yield encode_int(start, 3)
        if isRle:
            yield encode_int(0, 2)
            yield encode_int(length, 2)
            yield newData[start:start+1]
        else:
            yield encode_int(length, 2)
            yield newData[start:start+length]

    yield b"EOF"

def main():
    args = parse_args()

    # create patch data
    patch = bytearray()
    try:
        with open(args.orig_file, "rb") as handle1, \
        open(args.modified_file, "rb") as handle2:
            if max(handle1.seek(0, 2), handle2.seek(0, 2)) > 2 ** 24:
                sys.exit("Input files must not be larger than 16 MiB.")
            if handle1.seek(0, 2) > handle2.seek(0, 2):
                sys.exit(
                    "Second input file must not be smaller than first one."
                )
            for bytes_ in create_ips(handle1, handle2, args):
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

main()
