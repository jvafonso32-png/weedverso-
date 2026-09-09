Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.Run "powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File """ & appDir & "\start_weedverso.ps1"" -OpenBrowser", 0, False
