# Boots the device and keeps the serial stream on disk.
#
# Used after a flash to confirm the new image actually runs, rather than
# trusting esptool's own verification: esptool checks the bytes it wrote, not
# whether the sketch boots. A Quick Reference screen that panics on first tap
# would still pass that check.

param(
    [int]$Seconds = 25,
    [string]$Out = (Join-Path $PSScriptRoot "boot_log.txt")
)

$port = New-Object System.IO.Ports.SerialPort COM5, 115200, None, 8, one
$port.ReadTimeout = 300
$port.DtrEnable = $false
$port.RtsEnable = $false
$port.Open()
Start-Sleep -Milliseconds 400
$port.DiscardInBuffer()

# DTR/RTS toggling resets the board, which is what we want: we want the boot
# banner from the image we just wrote, not leftover output.
$port.DtrEnable = $true
$port.RtsEnable = $true
Start-Sleep -Milliseconds 120
$port.DtrEnable = $false
$port.RtsEnable = $false

$ms = New-Object System.IO.MemoryStream
$tmp = New-Object byte[] 4096
$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline) {
    try {
        $n = $port.Read($tmp, 0, $tmp.Length)
        if ($n -gt 0) { $ms.Write($tmp, 0, $n) }
    } catch { }
}
$port.Close()

[IO.File]::WriteAllBytes($Out, $ms.ToArray())
Write-Host ("seri: {0:N0} bayt -> {1}" -f $ms.Length, $Out)
