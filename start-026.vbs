Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")

' 0 = fully hidden window, False = don't wait for it to finish
sh.Run "cmd /c cd /d """ & folder & "\agents\T01_Smart_Binance_Intelligence"" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000", 0, False
sh.Run "cmd /c cd /d """ & folder & "\dashboard\frontend"" && npm run dev", 0, False

WScript.Sleep 7000
sh.Run "http://localhost:3000", 1, False
