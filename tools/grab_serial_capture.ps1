# Streams a capture off the device over serial and reconstructs the file.
#
# Buffer::saveSerial() wraps each flush in [BUF/BEGIN] ... [BUF/CLOSE], with the
# pcapng bytes in between and the scan statistics as text around them. So the
# whole job is: grab the raw byte stream, slice out the marked regions, and
# concatenate them. The result is a real pcapng that Wireshark can open, which
# is the only way to confirm that "Complete EAPOL: 1" corresponds to an actual
# four-way handshake on disk rather than just four flags in memory.

param(
    [int]$Seconds = 55
)

$port = New-Object System.IO.Ports.SerialPort COM5, 115200, None, 8, one
$port.ReadTimeout = 200
$port.DtrEnable = $false
$port.RtsEnable = $false
$port.Open()
Start-Sleep -Milliseconds 500

# Discard the boot banner so it cannot end up inside a capture block.
$port.DiscardInBuffer()

$port.Write("sniffpmkid -serial`r`n")

$ms = New-Object System.IO.MemoryStream
$tmp = New-Object byte[] 4096
$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline) {
    try {
        $n = $port.Read($tmp, 0, $tmp.Length)
        if ($n -gt 0) { $ms.Write($tmp, 0, $n) }
    } catch { }
}

# Stop and let the final buffer flush.
$port.Write("stopscan`r`n")
$deadline = (Get-Date).AddSeconds(6)
while ((Get-Date) -lt $deadline) {
    try {
        $n = $port.Read($tmp, 0, $tmp.Length)
        if ($n -gt 0) { $ms.Write($tmp, 0, $n) }
    } catch { }
}
$port.Close()

$raw = Join-Path $PSScriptRoot "serial_capture.bin"
[IO.File]::WriteAllBytes($raw, $ms.ToArray())
Write-Host ("ham seri akisi: {0:N0} bayt -> {1}" -f $ms.Length, $raw)