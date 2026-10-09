# Reads the device's own view of the SD card over serial.
#
# The card does not show up as a Windows drive, which leaves two possibilities:
# the reader is not plugged in, or the card is not detected by the firmware.
# Those need different answers, so ask the device directly -- Marauder reports
# SD state in the Device Info screen, and the boot banner prints the SD object.
#
# Also runs a short EAPOL scan so the pcap path is exercised, and reports
# whether saveFs() was reached: with no card, fs is NULL and Buffer::save()
# writes nothing at all, silently.

param(
    [int]$Seconds = 30
)

$port = New-Object System.IO.Ports.SerialPort COM5, 115200, None, 8, one
$port.ReadTimeout = 300
$port.DtrEnable = $false
$port.RtsEnable = $false
$port.Open()
Start-Sleep -Milliseconds 400
$port.DiscardInBuffer()

# Reset so the boot banner reflects the current card state.
$port.DtrEnable = $true
$port.RtsEnable = $true
Start-Sleep -Milliseconds 120
$port.DtrEnable = $false
$port.RtsEnable = $false

$sb = New-Object System.Text.StringBuilder
$tmp = New-Object byte[] 4096
$deadline = (Get-Date).AddSeconds($Seconds)

function Drain([double]$For) {
    $end = (Get-Date).AddSeconds($For)
    while ((Get-Date) -lt $end) {
        try {
            $n = $port.Read($tmp, 0, $tmp.Length)
            if ($n -gt 0) { [void]$sb.Append([Text.Encoding]::ASCII.GetString($tmp, 0, $n)) }
        } catch { }
    }
}

# Boot banner first.
Drain 6

# A short capture so Buffer::save() runs. No -serial: the point is to see
# whether the file lands on the card, not to read it off the wire.
$port.Write("sniffpmkid`r`n")
Drain ([Math]::Max(1, $Seconds - 16))
$port.Write("stopscan`r`n")
Drain 8
$port.Close()

$out = Join-Path $PSScriptRoot "sd_check.txt"
[IO.File]::WriteAllText($out, $sb.ToString())
Write-Host "seri: $($sb.Length) karakter -> $out"
