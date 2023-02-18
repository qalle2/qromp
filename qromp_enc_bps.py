import argparse, collections, os, struct, sys, time
from zlib import crc32

# actions (types of BPS blocks); note that "source" and "target" here refer to
# encoder's *input* files
SOURCE_READ = 0
TARGET_READ = 1
SOURCE_COPY = 2
TARGET_COPY = 3

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's BPS Patch Creator. Creates a BPS patch from "
        "the differences of two files. Slow."
    )

    parser.add_argument(
        "--min-copy", type=int, default=4,
        help="Minimum length of substring to copy from original file. 1-20, "
        "default=4. Affects efficiency, memory use and speed."
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

    minLen = 0
    maxLen = min(len(str1), len(str2))

    while minLen < maxLen:
        avgLen = (minLen + maxLen + 1) // 2
        if str1[:avgLen] in str2:
            minLen = avgLen
        else:
            maxLen = avgLen - 1

    return minLen

def create_bps(handle1, handle2, minCopyLen):
    # create a BPS patch from the difference of two files;
    # generate patch data except for patch CRC at the end;
    # the encoder doesn't take advantage of TARGET_COPY blocks being able to
    # extend past the end of the patched file

    handle1.seek(0)
    data1 = handle1.read()
    handle2.seek(0)
    data2 = handle2.read()

    # header (id, source/target file size, metadata size)
    yield b"BPS1"
    yield b"".join(encode_int(n) for n in (len(data1), len(data2), 0))

    # get unique minimum-length substrings in original file
    # (speeds up a lot but also takes a lot of memory)
    data1MinSubstrs = frozenset(
        data1[i:i+minCopyLen] for i in range(0, len(data1) - minCopyLen + 1, 1)
    )

    data2Pos = 0       # position in data2
    trgReadStart = -1  # start of TARGET_READ in data2 (-1 = none)
    srcCopyOffset = 0  # used by SOURCE_COPY
    trgCopyOffset = 0  # used by TARGET_COPY

    while data2Pos < len(data2):
        # find longest prefix of data2 in data1 and data2 (so far);
        # optimize for speed by checking minimum length first
        if data2[data2Pos:data2Pos+minCopyLen] in data1MinSubstrs:
            data1CopyLen = find_longest_prefix(data2[data2Pos:], data1)
        else:
            data1CopyLen = 0
        if data2[data2Pos:data2Pos+minCopyLen] in data2[:data2Pos]:
            data2CopyLen \
            = find_longest_prefix(data2[data2Pos:], data2[:data2Pos])
        else:
            data2CopyLen = 0

        if max(data1CopyLen, data2CopyLen) >= minCopyLen:
            # end ongoing TARGET_READ block if necessary
            if trgReadStart != -1:
                yield block_start(data2Pos - trgReadStart, TARGET_READ)
                yield data2[trgReadStart:data2Pos]
                trgReadStart = -1

            # output a SOURCE_READ, SOURCE_COPY or TARGET_COPY block
            if data1CopyLen >= data2CopyLen:
                if data1[data2Pos:data2Pos+data1CopyLen] \
                == data2[data2Pos:data2Pos+data1CopyLen]:
                    # tell decoder to copy from current position in data1
                    yield block_start(data1CopyLen, SOURCE_READ)
                else:
                    # tell decoder to copy from specified position in data1
                    copyPos \
                    = data1.index(data2[data2Pos:data2Pos+data1CopyLen])
                    yield block_start(data1CopyLen, SOURCE_COPY)
                    yield encode_signed(copyPos - srcCopyOffset)
                    srcCopyOffset = copyPos + data1CopyLen
                data2Pos += data1CopyLen
            else:
                # tell decoder to copy from specified position in data2
                copyPos \
                = data2[:data2Pos].index(data2[data2Pos:data2Pos+data2CopyLen])
                yield block_start(data2CopyLen, TARGET_COPY)
                yield encode_signed(copyPos - trgCopyOffset)
                trgCopyOffset = copyPos + data2CopyLen
                data2Pos += data2CopyLen
        else:
            # start a new TARGET_READ block if necessary
            if trgReadStart == -1:
                trgReadStart = data2Pos
            data2Pos += 1

    # end final TARGET_READ block if necessary
    if trgReadStart != -1:
        yield block_start(len(data2) - trgReadStart, TARGET_READ)
        yield data2[trgReadStart:]

    # footer except for patch CRC (source/target file CRC)
    yield struct.pack("<2L", crc32(data1), crc32(data2))

# -----------------------------------------------------------------------------

def main():
    startTime = time.time()
    args = parse_args()

    # create patch data
    try:
        with open(args.orig_file, "rb") as handle1, \
        open(args.modified_file, "rb") as handle2:
            patch = bytearray()
            for chunk in create_bps(handle1, handle2, args.min_copy):
                patch.extend(chunk)
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
