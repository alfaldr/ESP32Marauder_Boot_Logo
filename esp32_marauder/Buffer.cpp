#include "Buffer.h"
#include "PcapHeader.h"
#include "lang_var.h"

Buffer::Buffer(){
  bufA = (uint8_t*)malloc(BUF_SIZE);
  bufB = (uint8_t*)malloc(BUF_SIZE);
}

void Buffer::setPcapng(bool enabled) {
  if (writing) return; // cannot switch format mid-capture
  pcapng = enabled;
}

void Buffer::createFile(const char* name, bool is_pcap, bool is_gpx){
  int i=0;
  String prefix = directory ? String(directory) + "/" : "/";
  if (is_pcap) {
    const char* ext = pcapng ? ".pcapng" : ".pcap";
    do{
      fileName = prefix+String(name)+"_"+(String)i+ext;
      i++;
    } while(fs->exists(fileName));
  }
  else if ((!is_pcap) && (!is_gpx)) {
    do{
      fileName = prefix+String(name)+"_"+(String)i+".log";
      i++;
    } while(fs->exists(fileName));
  }
  else {
    do{
      fileName = prefix+String(name)+"_"+(String)i+".gpx";
      i++;
    } while(fs->exists(fileName));
  }

  Serial.println(fileName);
  
  file = fs->open(fileName, FILE_WRITE);
  file.close();
}

void Buffer::open(bool is_pcap){
  bufSizeA = 0;
  bufSizeB = 0;

  bufSizeB = 0;

  writing = true;

  if (is_pcap) {
    if (pcapng) {
      // Section Header + Interface Description. pcapng has no single global
      // header: every block repeats its own length, and the interface block
      // carries the link type and snap length instead.
      uint8_t block[marauder::sectionHeaderBlockSize()];
      size_t n = marauder::makeSectionHeaderBlock(block, sizeof(block));
      write(block, n);

      uint8_t idb[marauder::interfaceDescriptionBlockSize()];
      n = marauder::makeInterfaceDescriptionBlock(idb, sizeof(idb), SNAP_LEN);
      write(idb, n);
    } else {
      uint8_t header[marauder::kPcapGlobalHeaderSize];
      marauder::makePcapGlobalHeader(SNAP_LEN, header);
      write(header, sizeof(header));
    }
  }
}

String Buffer::getFileName() {
  return this->fileName;
}

void Buffer::setDirectory(const char* path) {
  directory = path;
}

void Buffer::openFile(const char* file_name, fs::FS* fs, bool serial, bool is_pcap, bool is_gpx) {
  bool save_pcap = settings_obj.loadSetting<bool>("SavePCAP");
  if (!save_pcap) {
    this->fs = NULL;
    this->serial = false;
    writing = false;
    return;
  }
  this->fs = fs;
  this->serial = serial;
  if (this->fs) {
    createFile(file_name, is_pcap, is_gpx);
  }
  if (this->fs || this->serial) {
    open(is_pcap);
  } else {
    writing = false;
  }
}

void Buffer::pcapOpen(const char* file_name, fs::FS* fs, bool serial) {
  openFile(file_name, fs, serial, true);
}

void Buffer::logOpen(const char* file_name, fs::FS* fs, bool serial) {
  openFile(file_name, fs, serial, false);
}

void Buffer::gpxOpen(const char* file_name, fs::FS* fs, bool serial) {
  openFile(file_name, fs, serial, false, true);
}

void Buffer::add(const uint8_t* buf, uint32_t len, bool is_pcap, const char* comment, size_t comment_len){
  if (comment == nullptr) comment_len = 0;
  else if (comment_len == 0) comment_len = strlen(comment);
  if (comment_len > marauder::kMaxPacketComment) comment_len = marauder::kMaxPacketComment;

    // Bytes this frame occupies, container header included. The original
    // check only counted the payload, so a frame that just fitted could
    // still write its header past the end of the buffer.
    //
    // packetBlockSize() already covers the payload: it counts pad4(len),
    // not len. Adding len on top therefore counted every frame twice and
    // made the buffer give up earlier than it had to. Classic pcap adds a
    // 16 byte record header on top of the payload; a plain log has none.
    size_t footprint;
    if (is_pcap) {
      footprint = pcapng ? marauder::packetBlockSize(len, comment_len)
                         : 16u + len;
    } else {
      footprint = len;
    }

  if (footprint > BUF_SIZE) { dropped_frames++; return; }

  // Keep filling the active buffer until it can no longer hold a frame, then
  // move to the spare so the main loop always has one contiguous block to
  // flush. Only give up once neither buffer has room.
  if (useA) {
    if (bufSizeA + footprint > BUF_SIZE) {
      if (bufSizeB + footprint > BUF_SIZE) { dropped_frames++; return; }
      useA = false;
    }
  } else {
    if (bufSizeB + footprint > BUF_SIZE) {
      if (bufSizeA + footprint > BUF_SIZE) { dropped_frames++; return; }
      useA = true;
    }
  }

  uint32_t microSeconds = micros(); // e.g. 45200400 => 45s 200ms 400us
  uint32_t seconds = (microSeconds/1000)/1000; // e.g. 45200400/1000/1000 = 45200 / 1000 = 45s

  microSeconds -= seconds*1000*1000; // e.g. 45200400 - 45*1000*1000 = 45200400 - 45000000 = 400us (because we only need the offset)

  if (is_pcap && pcapng) {
    const uint64_t timestamp_us =
        static_cast<uint64_t>(seconds) * 1000000ull + microSeconds;

    uint8_t header[marauder::kPacketBlockHeaderSize];
    size_t total = marauder::makePacketBlockHeader(
        header, sizeof(header), timestamp_us, len, comment, comment_len);
    write(header, sizeof(header));

    write(buf, len);

    // Every variable-length field is padded to a 32-bit boundary.
    const size_t padding = marauder::pad4(len) - len;
    if (padding > 0) {
      uint8_t zeros[3] = {0, 0, 0};
      write(zeros, padding);
    }

    uint8_t footer[marauder::packetBlockFooterSize(marauder::kMaxPacketComment)];
    size_t n = marauder::makePacketBlockFooter(
        footer, sizeof(footer), total, comment, comment_len);
    write(footer, n);
    return;
  }

  if (is_pcap) {
    write(seconds); // ts_sec
    write(microSeconds); // ts_usec
    write(len); // incl_len
    write(len); // orig_len
  }
  
  write(buf, len); // packet payload
}

void Buffer::append(wifi_promiscuous_pkt_t *packet, int len, const char* comment) {
  bool save_packet = settings_obj.loadSetting<bool>(text_table4[7]);
  if (save_packet) {
    add(packet->payload, len, true, comment, 0);
  }
}

void Buffer::append(String log) {
  bool save_packet = settings_obj.loadSetting<bool>(text_table4[7]);
  if (save_packet) {
    add((const uint8_t*)log.c_str(), log.length(), false);
  }
}

void Buffer::write(int32_t n){
  uint8_t buf[4];
  buf[0] = n;
  buf[1] = n >> 8;
  buf[2] = n >> 16;
  buf[3] = n >> 24;
  write(buf,4);
}

void Buffer::write(uint32_t n){
  uint8_t buf[4];
  buf[0] = n;
  buf[1] = n >> 8;
  buf[2] = n >> 16;
  buf[3] = n >> 24;
  write(buf,4);
}

void Buffer::write(uint16_t n){
  uint8_t buf[2];
  buf[0] = n;
  buf[1] = n >> 8;
  write(buf,2);
}

void Buffer::write(const uint8_t* buf, uint32_t len){
  if(!writing) return;
  while(saving) delay(10);
  
  if(useA){
    memcpy(&bufA[bufSizeA], buf, len);
    bufSizeA += len;
  }else{
    memcpy(&bufB[bufSizeB], buf, len);
    bufSizeB += len;
  }
}

void Buffer::saveFs(){
  file = fs->open(fileName, FILE_APPEND);
  if (!file) {
    Serial.println(text02+fileName+"'");
    return;
  }

  if(useA){
    if(bufSizeB > 0){
      file.write(bufB, bufSizeB);
    }
    if(bufSizeA > 0){
      file.write(bufA, bufSizeA);
    }
  } else {
    if(bufSizeA > 0){
      file.write(bufA, bufSizeA);
    }
    if(bufSizeB > 0){
      file.write(bufB, bufSizeB);
    }
  }

  file.close();
}

void Buffer::saveSerial() {
  // Saves to main console UART, user-facing app will ignore these markers
  // Uses / and ] in markers as they are illegal characters for SSIDs
  const char* mark_begin = "[BUF/BEGIN]";
  const size_t mark_begin_len = strlen(mark_begin);
  const char* mark_close = "[BUF/CLOSE]";
  const size_t mark_close_len = strlen(mark_close);

  // Additional buffer and memcpy's so that a single Serial.write() is called
  // This is necessary so that other console output isn't mixed into buffer stream
  uint8_t* buf = (uint8_t*)malloc(mark_begin_len + bufSizeA + bufSizeB + mark_close_len);
  if (!buf) return; // allocation failed; caller still resets the buffer sizes
  uint8_t* it = buf;
  memcpy(it, mark_begin, mark_begin_len);
  it += mark_begin_len;

  if(useA){
    if(bufSizeB > 0){
      memcpy(it, bufB, bufSizeB);
      it += bufSizeB;
    }
    if(bufSizeA > 0){
      memcpy(it, bufA, bufSizeA);
      it += bufSizeA;
    }
  } else {
    if(bufSizeA > 0){
      memcpy(it, bufA, bufSizeA);
      it += bufSizeA;
    }
    if(bufSizeB > 0){
      memcpy(it, bufB, bufSizeB);
      it += bufSizeB;
    }
  }

  memcpy(it, mark_close, mark_close_len);
  it += mark_close_len;
  Serial.write(buf, it - buf);
  free(buf);
}

void Buffer::save() {
  saving = true;

  if((bufSizeA + bufSizeB) == 0){
    saving = false;
    return;
  }

  if(this->fs) saveFs();
  if(this->serial) saveSerial();

  bufSizeA = 0;
  bufSizeB = 0;

  saving = false;
}
