Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\marco\projetos\LojaVirtual"
WshShell.Run """C:\Users\marco\AppData\Local\Programs\Python\Python312\python.exe"" ""c:\Users\marco\projetos\LojaVirtual\servidor_painel.py""", 0, False
