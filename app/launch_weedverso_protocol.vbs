Dim shell
Dim args
Dim uri
Dim command

Set shell = CreateObject("WScript.Shell")
Set args = WScript.Arguments

uri = ""
If args.Count > 0 Then
  uri = args.Item(0)
End If

uri = Replace(uri, """", """""")

command = "powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File ""C:\Users\joaov\OneDrive\Documentos\Desktop\WEEDVERSO\app\handle_weedverso_protocol.ps1"" -Uri """ & uri & """"
shell.Run command, 0, False
