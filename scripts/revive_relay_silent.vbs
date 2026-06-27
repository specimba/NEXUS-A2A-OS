' revive_relay_silent.vbs — zero-window launcher for revive_relay_ports.ps1
' Run by the NexusServiceAutoRevive scheduled task so the relay revival never
' flashes a console window. WScript has no UI; the spawned powershell is hidden.
Option Explicit
Dim sh, root, ps1, cmd
Set sh = CreateObject("WScript.Shell")
root = "C:\Users\speci.000\Documents\NEXUS"
ps1 = root & "\scripts\revive_relay_ports.ps1"
cmd = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ps1 & """"
' 0 = hidden window, False = don't wait
sh.Run cmd, 0, False
