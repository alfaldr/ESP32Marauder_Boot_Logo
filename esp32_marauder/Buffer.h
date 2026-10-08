#pragma once

#ifndef Buffer_h
#define Buffer_h

#include "Arduino.h"
#include "FS.h"
#include "settings.h"
#include "esp_wifi_types.h"
#include "configs.h"

//#define BUF_SIZE 3 * 1024 // Had to reduce buffer size to save RAM. GG @spacehuhn
//#define SNAP_LEN 2324 // max len of each recieved packet

//extern bool useSD;

extern Settings settings_obj;

// Capture container format. pcapng is a sequence of self-describing blocks and
// can carry a per-packet comment, which is what makes it possible to tell
// which AP a captured handshake belongs to. The classic .pcap format is kept
// as an option for tooling that does not read pcapng.
#ifndef CAPTURE_FORMAT_PCAPNG
  #define CAPTURE_FORMAT_PCAPNG 1
#endif

class Buffer {
  public:
    Buffer();
    void pcapOpen(const char* file_name, fs::FS* fs, bool serial);
    void logOpen(const char* file_name, fs::FS* fs, bool serial);
    void gpxOpen(const char* file_name, fs::FS* fs, bool serial);
    void append(wifi_promiscuous_pkt_t *packet, int len, const char* comment = nullptr);
    void append(String log);
    void save();
    String getFileName();
    void setDirectory(const char* path);

    void setPcapng(bool enabled);
    bool getPcapng() { return pcapng; }

    // Frames the buffer had no room for. Previously these were dropped without
    // a trace, which made an incomplete capture indistinguishable from a quiet
    // channel. Cumulative for the session; reset by clearDropped().
    uint32_t getDropped() { return dropped_frames; }
    void clearDropped() { dropped_frames = 0; }

  private:
    void createFile(const char* name, bool is_pcap, bool is_gpx = false);
    void open(bool is_pcap);
    void openFile(const char* file_name, fs::FS* fs, bool serial, bool is_pcap, bool is_gpx = false);
    void add(const uint8_t* buf, uint32_t len, bool is_pcap, const char* comment = nullptr, size_t comment_len = 0);
    void write(int32_t n);
    void write(uint32_t n);
    void write(uint16_t n);
    void write(const uint8_t* buf, uint32_t len);
    void saveFs();
    void saveSerial();

    uint8_t* bufA;
    uint8_t* bufB;

    uint32_t bufSizeA = 0;
    uint32_t bufSizeB = 0;

    bool writing = false; // acceppting writes to buffer
    bool useA = true; // writing to bufA or bufB
    bool saving = false; // currently saving onto the SD card
    bool pcapng = (CAPTURE_FORMAT_PCAPNG != 0);

    uint32_t dropped_frames = 0;

    String fileName = "/0.pcap";
    const char* directory = NULL;
    File file;
    fs::FS* fs;
    bool serial;
};

#endif
