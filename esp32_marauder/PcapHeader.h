#pragma once

#include <stddef.h>
#include <stdint.h>

namespace marauder {

constexpr size_t kPcapGlobalHeaderSize = 24;

void makePcapGlobalHeader(uint32_t snapshot_length,
                          uint8_t output[kPcapGlobalHeaderSize]);

// ---------------------------------------------------------------------------
// pcapng support.
//
// A capture is a flat sequence of blocks. Every block is laid out as
//
//   Block Type        uint32
//   Block Total Length uint32   (covers the whole block, both length fields)
//   Body              variable
//   Block Total Length uint32   (repeated verbatim)
//
// and every variable-length field is padded to a 32-bit boundary.
// ---------------------------------------------------------------------------

constexpr uint32_t kBlockSectionHeader  = 0x0A0D0D0A;
constexpr uint32_t kBlockInterfaceDesc  = 0x00000001;
constexpr uint32_t kBlockEnhancedPacket = 0x00000006;

// DLT_IEEE802_11. Same link type the classic pcap header above already writes,
// so downstream tooling decodes the frames identically either way.
constexpr uint16_t kLinkTypeIeee80211 = 105;

// Option codes used below.
constexpr uint16_t kOptEndOfOpt   = 0;
constexpr uint16_t kOptComment    = 1;
constexpr uint16_t kOptShbUserAppl = 4;

// Round `n` up to the next 32-bit boundary, as pcapng requires for every
// variable-length field.
constexpr size_t pad4(size_t n) { return (n + 3u) & ~static_cast<size_t>(3u); }

// Byte size of each block kind.
size_t sectionHeaderBlockSize();
size_t interfaceDescriptionBlockSize();
size_t packetBlockSize(uint32_t captured_len, size_t comment_len);

// Bytes makePacketBlockHeader writes before the payload:
//   type(4) + length(4) + iface(4) + tsHigh(4) + tsLow(4) + capLen(4) + origLen(4)
constexpr size_t kPacketBlockHeaderSize = 28;

// Bytes makePacketBlockFooter writes: the option list plus the repeated length.
size_t packetBlockFooterSize(size_t comment_len);

// Longest comment we will attach to a packet. pcapng itself has no limit, but
// this has to fit in a fixed stack buffer on a device with ~240 KB of free RAM,
// and a longer string crowds out captured frames in the write buffer.
constexpr size_t kMaxPacketComment = 96;

// Each returns the number of bytes written, or 0 if `capacity` is too small.
// Nothing is retained; the caller owns `output`.
size_t makeSectionHeaderBlock(uint8_t* output, size_t capacity);
size_t makeInterfaceDescriptionBlock(uint8_t* output, size_t capacity,
                                     uint32_t snapshot_length);

// The Enhanced Packet Block is emitted in two halves because the captured
// bytes live in the middle of the block and Buffer streams them from its own
// buffer. makePacketBlockHeader writes everything up to the payload and
// returns the *total* block size; the caller writes captured_len bytes plus
// pad4(captured_len) - captured_len padding bytes; then
// makePacketBlockFooter writes the options and the trailing length.
//
// Pass comment_length 0 (and comment may be null) to emit no comment.
size_t makePacketBlockHeader(uint8_t* output, size_t capacity,
                             uint64_t timestamp_us, uint32_t captured_len,
                             const char* comment, size_t comment_length);
size_t makePacketBlockFooter(uint8_t* output, size_t capacity, size_t total,
                             const char* comment, size_t comment_length);

}  // namespace marauder