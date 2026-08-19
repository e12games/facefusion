; UTF-8 with BOM required for Chinese text in Inno Setup.
#define MyAppName "脸幻中文版"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "非官方中文发行（基于 FaceFusion）"
#define SrcDir "c:\bak\gamesb1_soft\PC端\face\脸幻中文便携版"
#define OutDir "c:\bak\gamesb1_soft\PC端\face\installer-output"

[Setup]
AppId={{A7C4E2B1-8F19-4D3A-9C6E-3F8B21A04D77}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\LianHuanZH
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutDir}
OutputBaseFilename=LianHuanZH-Setup
SetupIconFile={#SrcDir}\internal\app\facefusion.ico
UninstallDisplayIcon={#SrcDir}\internal\app\facefusion.ico
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableWelcomePage=no
InfoBeforeFile={#SrcDir}\使用说明.txt
UsePreviousAppDir=yes
CloseApplications=no
RestartIfNeededByRun=no
; Large payload: keep temp on system drive.
DiskSpanning=no

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "在桌面创建快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "{#SrcDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\internal"; Attribs: hidden

[Icons]
Name: "{group}\脸幻中文版"; Filename: "{app}\启动换脸.bat"; WorkingDir: "{app}"; IconFilename: "{app}\internal\app\facefusion.ico"
Name: "{group}\使用说明"; Filename: "{app}\使用说明.txt"
Name: "{group}\卸载脸幻中文版"; Filename: "{uninstallexe}"
Name: "{autodesktop}\脸幻中文版"; Filename: "{app}\启动换脸.bat"; WorkingDir: "{app}"; IconFilename: "{app}\internal\app\facefusion.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\启动换脸.bat"; Description: "安装完成后立即启动"; Flags: nowait postinstall skipifsilent unchecked
