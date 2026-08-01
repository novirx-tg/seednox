; Seednox Windows Installer Script (Inno Setup 6+)
; Generates standard Windows installer: Seednox-Setup-v1.0.2.exe

#define MyAppName "Seednox"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "novirx-tg"
#define MyAppURL "https://github.com/novirx-tg/seednox"
#define MyAppExeName "Seednox-Windows-v1.0.2.exe"

[Setup]
AppId={{8B8A62A1-94B6-4E8E-8761-FDF97EFA4B12}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\Seednox
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=Seednox-Setup-v1.0.2
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\assets\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Seednox-Windows-v1.0.2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\app.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvPath: string;
begin
  if CurStep = ssPostInstall then
  begin
    EnvPath := ExpandConstant('{app}\.env');
    if not FileExists(EnvPath) then
    begin
      SaveStringToFile(EnvPath, '# Seednox Environment Configuration' + #13#10 + 'BOT_TOKEN=' + #13#10 + 'SESSION_TIMEOUT=900' + #13#10, False);
    end;
  end;
end;
