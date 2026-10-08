#include "PcapHeader.h"

namespace marauder {
namespace {

void writeLittleEndian16(uint16_t value, uint8_t* output) {
  output[0] = static_cast<uint8_t>(value);
  output[1] = static_cast<uint8_t>(value >> 8);
}

void writeLittleEndian32(uint32_t value, uint8_t* output) {
  output[0] = static_cast<uint8_t>(value);
  output[1] = static_cast<uint8_t>(value >> 8);
  output[2] = static_cast<uint8_t>(value >> 16);
  output[3] = static_cast<uint8_t>(value >> 24);
}

void writeLittleEndian64(uint64_t value, uint8_t* output) {
  writeLittleEndian32(static_cast<uint32_t>(value), output);
  writeLittleEndian32(static_cast<uint32_t>(value >> 32), output + 4);
}

// Copy `length` bytes and pad the tail out to the next 32-bit boundary, which
// is what every variable-length pcapng field needs.
size_t writePadded(const char* data, size_t length, uint8_t* output) {
  size_t padded = pad4(length);
  for (size_t i = 0; i < padded; i++) {
    output[i] = (i < length) ? static_cast<uint8_t>(data[i]) : 0u;
  }
  return padded;
}

// One option is code (uint16) + length (uint16) + value padded to 4 bytes.
size_t writeOption(uint16_t code, const char* value, size_t value_length,
                   uint8_t* output) {
  writeLittleEndian16(code, output);
  writeLittleEndian16(static_cast<uint16_t>(value_length), output + 2);
  return 4 + writePadded(value, value_length, output + 4);
}

constexpr size_t kOptionHeaderSize = 4;
constexpr size_t kEndOfOptSize = 4;

// One string option plus the end-of-options marker.
size_t optionListSize(size_t comment_length) {
  size_t size = kEndOfOptSize;
  if (comment_length > 0) {
    size += kOptionHeaderSize + pad4(comment_length);
  }
  return size;
}

void writeOptionList(uint8_t* output, const char* comment,
                     size_t comment_length) {
  size_t off = 0;
  if (comment && comment_length > 0) {
    off += writeOption(kOptComment, comment, comment_length, output);
  }
  writeLittleEndian16(kOptEndOfOpt, output + off);
  writeLittleEndian16(0, output + off + 2);
}

constexpr char kUserAppl[] = "ESP32 Marauder";
constexpr size_t kUserApplLen = sizeof(kUserAppl) - 1;

}  // namespace

void makePcapGlobalHeader(uint32_t snapshot_length,
                          uint8_t output[kPcapGlobalHeaderSize]) {
  writeLittleEndian32(0xa1b2c3d4, output);
  writeLittleEndian16(2, output + 4);
  writeLittleEndian16(4, output + 6);
  writeLittleEndian32(0, output + 8);
  writeLittleEndian32(0, output + 12);
  writeLittleEndian32(snapshot_length, output + 16);
  writeLittleEndian16(kLinkTypeIeee80211, output + 20);
  output[22] = 0;
  output[23] = 0;
}

// --- Section Header Block ---------------------------------------------------

size_t sectionHeaderBlockSize() {
  // type(4) + length(4) + magic(4) + major(2) + minor(2) + sectionLength(8)
  // + shb_userappl option + endofopt(4) + length(4)
  size_t appl = kOptionHeaderSize + pad4(kUserApplLen);
  return 12 + 4 + 2 + 2 + 8 + appl + kEndOfOptSize + 4;
}

size_t makeSectionHeaderBlock(uint8_t* output, size_t capacity) {
  const size_t total = sectionHeaderBlockSize();
  if (capacity < total) return 0;

  uint8_t* body = output + 8;
  writeLittleEndian32(0x1A2B3C4D, body);  // byte-order magic
  writeLittleEndian16(1, body + 4);       // major version
  writeLittleEndian16(0, body + 6);       // minor version
  writeLittleEndian64(0xFFFFFFFFFFFFFFFFull, body + 8);  // section length: unknown
  writeOption(kOptShbUserAppl, kUserAppl, kUserApplLen, body + 16);

  writeLittleEndian32(kBlockSectionHeader, output);
  writeLittleEndian32(static_cast<uint32_t>(total), output + 4);
  writeLittleEndian16(kOptEndOfOpt, body + 16 + kOptionHeaderSize + pad4(kUserApplLen));
  writeLittleEndian16(0, body + 16 + kOptionHeaderSize + pad4(kUserApplLen) + 2);
  writeLittleEndian32(static_cast<uint32_t>(total), output + total - 4);
  return total;
}

// --- Interface Description Block -------------------------------------------

size_t interfaceDescriptionBlockSize() {
  // type(4) + length(4) + linkType(2) + reserved(2) + snapLen(4) + options + length(4)
  // No if_tsresol option: the pcapng default of 6 already means microseconds,
  // which matches the classic pcap timestamps byte for byte.
  return 12 + 4 + optionListSize(0) + 4;
}

size_t makeInterfaceDescriptionBlock(uint8_t* output, size_t capacity,
                                     uint32_t snapshot_length) {
  const size_t total = interfaceDescriptionBlockSize();
  if (capacity < total) return 0;

  uint8_t* body = output + 8;
  writeLittleEndian16(kLinkTypeIeee80211, body);
  writeLittleEndian16(0, body + 2);  // reserved
  writeLittleEndian32(snapshot_length, body + 4);

  writeLittleEndian32(kBlockInterfaceDesc, output);
  writeLittleEndian32(static_cast<uint32_t>(total), output + 4);
  writeLittleEndian16(kOptEndOfOpt, body + 8);
  writeLittleEndian16(0, body + 10);
  writeLittleEndian32(static_cast<uint32_t>(total), output + total - 4);
  return total;
}

// --- Enhanced Packet Block --------------------------------------------------

size_t packetBlockSize(uint32_t captured_len, size_t comment_length) {
  // type(4) + length(4) + iface(4) + tsHigh(4) + tsLow(4) + capLen(4) +
  // origLen(4) + padded data + options + length(4)
  return 8 + 4 + 4 + 4 + 4 + 4 + pad4(captured_len) +
         optionListSize(comment_length) + 4;
}

size_t packetBlockFooterSize(size_t comment_length) {
  return optionListSize(comment_length) + 4;
}

size_t makePacketBlockHeader(uint8_t* output, size_t capacity,
                             uint64_t timestamp_us, uint32_t captured_len,
                             const char* comment, size_t comment_length) {
  // Only the fixed leading fields are written here; the caller streams the
  // payload and then the footer. So the capacity check is on those bytes, not
  // on the whole block.
  if (capacity < kPacketBlockHeaderSize) return 0;

  uint8_t* body = output + 8;
  writeLittleEndian32(0, body);                                   // interface id
  writeLittleEndian32(static_cast<uint32_t>(timestamp_us >> 32), body + 4);
  writeLittleEndian32(static_cast<uint32_t>(timestamp_us), body + 8);
  writeLittleEndian32(captured_len, body + 12);
  writeLittleEndian32(captured_len, body + 16);  // original length == captured

  writeLittleEndian32(kBlockEnhancedPacket, output);
  writeLittleEndian32(static_cast<uint32_t>(
      packetBlockSize(captured_len, comment_length)), output + 4);

  (void)comment;
  // Return the total so the caller can repeat it after the options.
  return packetBlockSize(captured_len, comment_length);
}

size_t makePacketBlockFooter(uint8_t* output, size_t capacity, size_t total,
                             const char* comment, size_t comment_length) {
  const size_t tail = packetBlockFooterSize(comment_length);
  if (capacity < tail) return 0;
  if (total < tail) return 0;

  uint8_t* body = output + total - tail;
  writeOptionList(body, comment, comment_length);
  writeLittleEndian32(static_cast<uint32_t>(total), output + total - 4);
  return tail;
}

}  // namespace marauder