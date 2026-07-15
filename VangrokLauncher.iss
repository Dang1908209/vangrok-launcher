[Setup]
AppName=Vangrok Launcher
AppVersion=1.0
AppPublisher=Vangrok Studio
DefaultDirName={autopf}\Vangrok Launcher
DefaultGroupName=Vangrok Launcher
DisableProgramGroupPage=yes
OutputDir=F:\VangrokLauncher\dist
OutputBaseFilename=VangrokLauncherSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

; Ép bộ cài đặt sử dụng thư mục Program Files 64-bit thay vì (x86)
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 1. Copy file thực thi chính .exe
Source: "F:\VangrokLauncher\dist\VangrokLauncher\VangrokLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion

; 2. Copy toàn bộ thư mục _internal do PyInstaller build ra (kèm mở khóa quyền ghi file)
Source: "F:\VangrokLauncher\dist\VangrokLauncher\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify

; 3. [QUAN TRỌNG VỪA THÊM] Copy bổ sung thư mục CONFIG từ dự án gốc vào thẳng _internal\config (Kèm quyền ghi để lưu user, session không bị lỗi)
Source: "F:\VangrokLauncher\config\*"; DestDir: "{app}\_internal\config"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify

[Icons]
Name: "{group}\Vangrok Launcher"; Filename: "{app}\VangrokLauncher.exe"
Name: "{autodesktop}\Vangrok Launcher"; Filename: "{app}\VangrokLauncher.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VangrokLauncher.exe"; Description: "{cm:LaunchProgram,Vangrok Launcher}"; Flags: nowait postinstall skipifsilent