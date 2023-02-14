import argparse, os, struct, sys, time
from zlib import crc32

# actions (types of BPS blocks); note that "source" and "target" here refer to
# encoder's *input* files
SOURCE_READ = 0
TARGET_READ = 1
SOURCE_COPY = 2
TARGET_COPY = 3  # unused atm

# number of dots in BPS progress indicator
PROGRESS_DOT_COUNT = 100

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's BPS Patch Creator. Creates a BPS patch from "
        "the differences of two files. Inefficient and slow. Prints a "
        f"progress indicator ({PROGRESS_DOT_COUNT} dots)."
    )

    parser.add_argument(
        "--min-copy", type=int, default=4,
        help="Minimum length of substring to copy from original file. 1-20, "
        "default=4. Affects efficiency. Larger=faster."
    )

    parser.add_argument(
        "orig_file", help="Original file to read."
    )
    parser.add_argument(
        "modified_file", help="File to read and compare against orig_file."
    )
    parser.add_argument(
        "patch_file", help="Patch file to write (.bps)."
    )

    args = parser.parse_args()

    if not 1 <= args.min_copy <= 20:
        sys.exit("Invalid '--min-copy' value.")

    if not os.path.isfile(args.orig_file):
        sys.exit("Original file not found.")
    if not os.path.isfile(args.modified_file):
        sys.exit("Modified file not found.")
    if os.path.exists(args.patch_file):
        sys.exit("Output file already exists.")

    return args

# -----------------------------------------------------------------------------

def encode_int(n):
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

def encode_signed(n):
    # encode a signed BPS integer
    return encode_int((abs(n) << 1) | (1 if n < 0 else 0))

def block_start(length, action):
    # encode start of block
    return encode_int(((length - 1) << 2) | action)

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

def find_substrings(str1, str2, minCopyLen):
    # find substrings in str1 that occur anywhere in str2;
    # generate (start_in_str1, length);
    # e.g. "abcd", "cxab" -> (0, 2), (2, 1)
    # almost all the time is spent here (almost 4 min for largest test file)

    pos1 = 0  # position in str1
    dotsPrinted = 0

    while pos1 < len(str1):
        # print progress indicator
        dotsSoFar = pos1 * PROGRESS_DOT_COUNT // len(str1)
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

    print((PROGRESS_DOT_COUNT - dotsPrinted) * ".")

def create_bps(handle1, handle2, minCopyLen):
    # create a BPS patch from the difference of two files;
    # generate patch data except for patch CRC at the end;
    # note: doesn't use the TARGET_COPY action at all

    handle1.seek(0)
    data1 = handle1.read()
    handle2.seek(0)
    data2 = handle2.read()

    # header (id, source/target file size, metadata size)
    yield b"BPS1" + b"".join(
        encode_int(n) for n in (len(data1), len(data2), 0)
    )

    # find identical substrings: [(start_in_data2, length), ...]
    data2Substrs = list(s for s in find_substrings(data2, data1, minCopyLen))

    # create patch data
    data2Pos = 0  # data2 read position
    srcOffset = 0  # used by SOURCE_COPY
    for (start, length) in data2Substrs:
        if start > data2Pos:
            # differing data since previous identical substring
            yield block_start(start - data2Pos, TARGET_READ)
            yield data2[data2Pos:start]
        # identical substring
        data1Pos = data1.index(data2[start:start+length])
        if data1Pos == start:
            yield block_start(length, SOURCE_READ)
        else:
            yield block_start(length, SOURCE_COPY)
            yield encode_signed(data1Pos - srcOffset)
            srcOffset = data1Pos + length
        data2Pos = start + length

    if len(data2) > data2Pos:
        # differing data after final identical substring
        yield block_start(len(data2) - data2Pos, TARGET_READ)
        yield data2[data2Pos:]

    # footer except patch CRC (source/target file CRC)
    yield struct.pack("<2L", crc32(data1), crc32(data2))

# -----------------------------------------------------------------------------

def main():
    startTime = time.time()
    args = parse_args()

    # create patch data
    patch = bytearray()
    try:
        with open(args.orig_file, "rb") as handle1, \
        open(args.modified_file, "rb") as handle2:
            for bytes_ in create_bps(handle1, handle2, args.min_copy):
                patch.extend(bytes_)
            patch.extend(struct.pack("<L", crc32(patch)))
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
