[Setup]
AppName=Vangrok Launcher
AppVersion=1.0
AppPublisher=Vangrok Studio
DefaultDirName={localappdata}\Vangrok Launcher
DefaultGroupName=Vangrok Launcher
DisableProgramGroupPage=yes
OutputDir=F:\VangrokLauncher\dist
OutputBaseFilename=VangrokLauncherSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
Name: "{app}"; Permissions: users-modify

[Files]
; 1. Copy file thực thi chính .exe
Source: "F:\VangrokLauncher\dist\VangrokLauncher\VangrokLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion

; 2. Copy toàn bộ thư mục _internal do PyInstaller build ra
Source: "F:\VangrokLauncher\dist\VangrokLauncher\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; 3. [CHỈ SỬA TRONG SETUP]: CHỈ copy config vào ĐÚNG 1 NƠI duy nhất là thư mục gốc bên ngoài!
; Tuyệt đối không copy vào _internal nữa. Bằng cách này, dù backend bạn viết thế nào thì khi tìm config
; nó cũng bắt buộc phải đọc và ghi vào đúng thư mục gốc này -> Git sẽ NHẬN DIỆN ĐƯỢC 100% để upload!
Source: "F:\VangrokLauncher\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs

; 4. Copy file .gitignore vào thư mục cài đặt để chặn Git xóa thư viện
Source: "F:\VangrokLauncher\.gitignore"; DestDir: "{app}"; Flags: ignoreversion

; 5. [CHỈ SỬA TRONG SETUP - QUAN TRỌNG NHẤT]: 
; Thay vì copy nguyên cái thùng rác .git cũ từ máy Dev gây lỗi "tự sát", ta loại bỏ các file ghi nhớ cũ,
; CHỈ copy đúng cấu trúc kết nối với GitHub. Khi cài xong nó sẽ là một kho Git siêu sạch, KHÔNG BAO GIỜ xóa cacert.pem!
Source: "F:\VangrokLauncher\.git\*"; DestDir: "{app}\.git"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.lock, index.lock, .git\index.lock, COMMIT_EDITMSG, FETCH_HEAD, ORIG_HEAD, logs\*, refs\remotes\*"

[Icons]
Name: "{group}\Vangrok Launcher"; Filename: "{app}\VangrokLauncher.exe"
Name: "{autodesktop}\Vangrok Launcher"; Filename: "{app}\VangrokLauncher.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VangrokLauncher.exe"; Description: "{cm:LaunchProgram,Vangrok Launcher}"; Flags: nowait postinstall skipifsilent