import argparse, os, struct, sys, time
from zlib import crc32

# enumerate actions (types of BPS blocks); note that "source" and "target" here
# refer to encoder's *input* files
(SOURCE_READ, TARGET_READ, SOURCE_COPY, TARGET_COPY) = range(4)

def parse_args():
    # parse command line arguments

    parser = argparse.ArgumentParser(
        description="Qalle's BPS Patch Creator. Creates a BPS patch from "
        "the differences of two files. Slow."
    )

    parser.add_argument(
        "--min-copy-len", type=int, default=4,
        help="Minimum length of substrings to copy from original or patched "
        "file. 1-32, default=4. A larger value is usually faster but less "
        "efficient and requires more memory."
    )
    parser.add_argument(
        "--metadata", type=str, default="",
        help="Metadata to save in the patch file, in ASCII. Default=none."
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

    if not 1 <= args.min_copy_len <= 32:
        sys.exit("Invalid '--min-copy-len' value.")
    if not args.metadata.isascii():
        sys.exit("Metadata is not ASCII.")

    if not os.path.isfile(args.orig_file):
        sys.exit("Original file not found.")
    if not os.path.isfile(args.modified_file):
        sys.exit("Modified file not found.")
    if os.path.exists(args.patch_file):
        sys.exit("Output file already exists.")

    return args

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

def encode_signed_int(n):
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

def create_bps(handle1, handle2, args):
    # create a BPS patch from the difference of two files;
    # generate patch data except for the patch CRC at the end;
    # the encoder doesn't take advantage of TARGET_COPY blocks being able to
    # extend past the end of the patched file;
    # see https://gist.github.com/khadiwala/32550f44efcc36a5b6a470ff2d4c9c22

    handle1.seek(0)
    data1 = handle1.read()
    handle2.seek(0)
    data2 = handle2.read()

    # header (id, original file size, patched file size, metadata size)
    yield b"BPS1"
    yield b"".join(
        encode_int(n) for n in (len(data1), len(data2), len(args.metadata))
    )

    # metadata
    if args.metadata:
        yield args.metadata.encode("ascii")

    # unique minimum-length substrings in original/patched file;
    # these speed up the encoder a lot but also take a lot of memory;
    # for the patched file, the set must be built incrementally because the
    # decoder can't read data it has not yet written
    data1MinSubstrs = frozenset(
        data1[i:i+args.min_copy_len]
        for i in range(0, len(data1) - args.min_copy_len + 1, 1)
    )
    data2MinSubstrs = set()

    data2Pos = 0       # position in data2
    prevData2Pos = 0   # previous position in data2
    trgReadStart = -1  # start of TARGET_READ in data2 (-1 = none)
    srcCopyOffset = 0  # SOURCE_COPY's position in data1
    trgCopyOffset = 0  # TARGET_COPY's position in data2

    while data2Pos < len(data2):
        # add minimum-length substrings that the decoder has become aware of
        # on the previous round
        data2MinSubstrs.update(
            data2[i:i+args.min_copy_len] for i in range(
                max(prevData2Pos - args.min_copy_len + 1, 0),
                max(data2Pos - args.min_copy_len + 1, 0),
            )
        )
        prevData2Pos = data2Pos

        # find longest prefix of data2 in data1 and data2 (so far);
        # optimize for speed by checking minimum length first
        if data2[data2Pos:data2Pos+args.min_copy_len] in data1MinSubstrs:
            data1CopyLen = find_longest_prefix(data2[data2Pos:], data1)
        else:
            data1CopyLen = 0
        if data2[data2Pos:data2Pos+args.min_copy_len] in data2MinSubstrs:
            data2CopyLen \
            = find_longest_prefix(data2[data2Pos:], data2[:data2Pos])
        else:
            data2CopyLen = 0

        # choose action
        if data1CopyLen >= max(data2CopyLen, args.min_copy_len):
            if data1[data2Pos:data2Pos+data1CopyLen] \
            == data2[data2Pos:data2Pos+data1CopyLen]:
                action = SOURCE_READ
            else:
                action = SOURCE_COPY
        elif data2CopyLen >= args.min_copy_len:
            action = TARGET_COPY
        else:
            action = TARGET_READ

        # end a TARGET_READ block before any other block
        if action != TARGET_READ and trgReadStart != -1:
            # tell decoder to copy from patch file
            yield block_start(data2Pos - trgReadStart, TARGET_READ)
            yield data2[trgReadStart:data2Pos]
            trgReadStart = -1

        if action == SOURCE_READ:
            # tell decoder to copy from current position in data1
            yield block_start(data1CopyLen, SOURCE_READ)
            data2Pos += data1CopyLen
        elif action == SOURCE_COPY:
            # tell decoder to copy from specified position in data1
            copyPos = data1.index(data2[data2Pos:data2Pos+data1CopyLen])
            yield block_start(data1CopyLen, SOURCE_COPY)
            yield encode_signed_int(copyPos - srcCopyOffset)
            srcCopyOffset = copyPos + data1CopyLen
            data2Pos += data1CopyLen
        elif action == TARGET_COPY:
            # tell decoder to copy from specified position in data2
            copyPos \
            = data2[:data2Pos].index(data2[data2Pos:data2Pos+data2CopyLen])
            yield block_start(data2CopyLen, TARGET_COPY)
            yield encode_signed_int(copyPos - trgCopyOffset)
            trgCopyOffset = copyPos + data2CopyLen
            data2Pos += data2CopyLen
        else:
            # TARGET_READ; start a new block if necessary
            if trgReadStart == -1:
                trgReadStart = data2Pos
            data2Pos += 1

    # end final TARGET_READ block
    if trgReadStart != -1:
        yield block_start(len(data2) - trgReadStart, TARGET_READ)
        yield data2[trgReadStart:]

    # footer except for patch CRC (source/target file CRC)
    yield struct.pack("<2L", crc32(data1), crc32(data2))

def main():
    startTime = time.time()
    args = parse_args()

    # create patch data
    try:
        with open(args.orig_file, "rb") as handle1, \
        open(args.modified_file, "rb") as handle2:
            patch = bytearray()
            for chunk in create_bps(handle1, handle2, args):
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
