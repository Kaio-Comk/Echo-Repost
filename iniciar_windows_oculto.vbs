' Abre o iniciar_windows.bat sem janela (usado pela tarefa InstaRepost do Agendador).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "cmd /c iniciar_windows.bat", 0, True
