' Starts the 026 live supervisor hidden (no console window).
' Put a shortcut to this in the Windows Startup folder (Win+R -> shell:startup)
' so the fleet refreshes automatically every time you log in.
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = folder
' 0 = hidden window, False = don't wait
sh.Run "cmd /c python live\supervisor.py", 0, False
