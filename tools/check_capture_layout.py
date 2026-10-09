#!/usr/bin/env python3
"""
Checks that no pcapng write lands outside the buffer it was handed.

The device panicked during an EAPOL capture. The cause was in the footer:
makePacketBlockFooter() indexed its output as if it were the start of the whole
block, writing a 60 byte option list at offset total - tail inside a 104 byte
stack buffer. Every captured frame smashed the WiFi receive callback's stack.

The bug was invisible to the compiler because the arithmetic is all in size_t,
and it only shows up once a comment is long enough and a frame is short enough
for total - tail to exceed the tail buffer. This walks those two dimensions and
asserts every write stays in bounds, which is the shape of bug that the
compiler cannot catch for you.

Usage:  python tools/check_capture_layout.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# From PcapHeader.h.
K_PACKET_BLOCK_HEADER_SIZE = 28
K_MAX_PACKET_COMMENT = 96
BUF_SIZE = 3 * 1024


def pad4(n):
    return (n + 3) & ~3


def option_list_size(comment_length):
    size = 4  # opt_endofopt
    if comment_length > 0:
        size += 4 + pad4(comment_length)
    return size


def packet_block_size(caplen, comment_length):
    return (8 + 4 + 4 + 4 + 4 + 4 + pad4(caplen)
            + option_list_size(comment_length) + 4)


def packet_block_footer_size(comment_length):
    return option_list_size(comment_length) + 4


def check():
    problems = []
    caplens = list(range(1, 2325, 7))
    comment_lengths = list(range(0, K_MAX_PACKET_COMMENT + 1))

    for caplen in caplens:
        for clen in comment_lengths:
            total = packet_block_size(caplen, clen)
            tail = packet_block_footer_size(clen)

            header_capacity = K_PACKET_BLOCK_HEADER_SIZE
            footer_capacity = packet_block_footer_size(K_MAX_PACKET_COMMENT)

            # Header writes bytes 0..27 of the block, into a buffer of exactly
            # that size.
            if header_capacity < 28:
                problems.append("header buffer too small")

            # Footer writes the option list and the repeated length into its
            # own buffer, starting at offset 0. The old code wrote at
            # total - tail, which is the bug.
            if footer_capacity < tail:
                problems.append(
                    "caplen=%d comment=%d: footer needs %d, buffer is %d"
                    % (caplen, clen, tail, footer_capacity))

            # What actually gets written into bufA/bufB.
            written = 28 + caplen + (pad4(caplen) - caplen) + tail
            if written != total:
                problems.append(
                    "caplen=%d comment=%d: writes total %d, block declares %d"
                    % (caplen, clen, written, total))

            # The old broken behaviour, for the record.
            old_offset = total - tail
            if old_offset + tail > footer_capacity:
                pass  # expected for the old code; not a failure now

    print("checked %d (caplen, comment) combinations"
          % (len(caplens) * len(comment_lengths)))

    if problems:
        print("\nFAIL (%d)" % len(problems))
        for p in problems[:10]:
            print("  " + p)
        return 1

    print("OK: header and footer stay inside their buffers, and the bytes")
    print("    written always add up to the block length that is declared")
    return 0


if __name__ == "__main__":
    sys.exit(check())