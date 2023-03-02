; Taken from example2.nsi

;--------------------------------

; The name of the installer
Name "Locatorator"

; The file to write
OutFile "locatorator_setup.exe"

; Request application privileges for Windows Vista and higher
RequestExecutionLevel user

; Build Unicode installer
Unicode True

; The default installation directory
InstallDir $APPDATA\Locatorator

; Registry key to check for directory (so if you install again, it will 
; overwrite the old one automatically)
InstallDirRegKey HKCU "Software\GlowingPixel\Locatorator" "Install_Dir"

;--------------------------------

; Pages

Page components
Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

;--------------------------------

; The stuff to install
Section "Locatorator Application (required)"

  SectionIn RO
  
  ; Set output path to the installation directory.
  SetOutPath $INSTDIR
  
  ; Put file there
  File /r "..\Locatorator\*"
  
  ; Write the installation path into the registry
  WriteRegStr HKLM SOFTWARE\GlowingPixel\Locatorator "Install_Dir" "$INSTDIR"
  
  ; Write the uninstall keys for Windows
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Locatorator" "DisplayName" "Locatorator"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Locatorator" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Locatorator" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Locatorator" "NoRepair" 1
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
SectionEnd

; Optional section (can be disabled by the user)
Section "Start Menu Shortcuts"

  CreateDirectory "$SMPROGRAMS\Locatorator"
  CreateShortcut "$SMPROGRAMS\Locatorator\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  CreateShortcut "$SMPROGRAMS\Locatorator\Locatorator.lnk" "$INSTDIR\Locatorator.exe"

SectionEnd

;--------------------------------

; Uninstaller

Section "Uninstall"
  
  ; Remove registry keys
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Locatorator"
  DeleteRegKey HKCU SOFTWARE\GlowingPixel\Locatorator

  ; Remove directories
  RMDir /r "$SMPROGRAMS\Locatorator"
  RMDir /r "$INSTDIR"

SectionEnd
