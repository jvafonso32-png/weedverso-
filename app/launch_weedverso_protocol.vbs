Dim shell
Dim args
Dim fso
Dim uri
Dim command
Dim appDir
Dim handlerScript

Set shell = CreateObject("WScript.Shell")
Set args = WScript.Arguments
Set fso = CreateObject("Scripting.FileSystemObject")

uri = ""
If args.Count > 0 Then
  uri = args.Item(0)
End If

uri = Replace(uri, """", """""")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
handlerScript = appDir & "\handle_weedverso_protocol.ps1"

command = "powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File """ & handlerScript & """ -Uri """ & uri & """"
shell.Run command, 0, False
