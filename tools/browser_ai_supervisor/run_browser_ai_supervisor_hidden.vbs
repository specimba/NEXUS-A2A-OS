Option Explicit

Dim shell, fso, scriptDir, repoRoot, psScript, pwsh, command, exitCode
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
repoRoot = fso.GetParentFolderName(fso.GetParentFolderName(scriptDir))
psScript = fso.BuildPath(scriptDir, "run_browser_ai_supervisor.ps1")
pwsh = "C:\Program Files\PowerShell\7\pwsh.exe"
If Not fso.FileExists(pwsh) Then
    pwsh = shell.ExpandEnvironmentStrings("%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe")
End If

shell.CurrentDirectory = repoRoot
command = """" & pwsh & """ -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File """ & psScript & """"
exitCode = shell.Run(command, 0, True)
WScript.Quit exitCode
