use std::process::Command;

/// Comandi bloccati — MAI eseguire, neanche con conferma
const BLOCKED_PATTERNS: &[&str] = &[
    "rm -rf /",
    "rm -rf ~",
    "rm -rf *",
    "mkfs",
    "dd if=",
    ":(){",
    "fork bomb",
    "> /dev/sda",
    "chmod -R 777 /",
    "curl | sh",
    "wget | sh",
    "shutdown",
    "reboot",
    "halt",
    "init 0",
    "passwd",
    "useradd",
    "userdel",
    "visudo",
    "diskutil erase",
    "format c:",
    "del /f /s /q",
    "reg delete",
];

/// Comandi che richiedono conferma utente
const CONFIRM_PATTERNS: &[&str] = &[
    "rm ",
    "del ",
    "move ",
    "mv ",
    "kill",
    "pkill",
    "sudo",
    "defaults write",
    "defaults delete",
    "networksetup",
    "dscl",
    "launchctl",
    "systemctl",
    "npm install -g",
    "pip install",
    "brew install",
    "apt install",
];

#[derive(Debug, serde::Serialize)]
pub enum CommandSafety {
    Safe,
    NeedsConfirm(String),
    Blocked(String),
}

pub fn check_command_safety(command: &str) -> CommandSafety {
    let lower = command.to_lowercase();

    for pattern in BLOCKED_PATTERNS {
        if lower.contains(pattern) {
            return CommandSafety::Blocked(format!(
                "Comando bloccato per sicurezza: contiene '{}'",
                pattern
            ));
        }
    }

    for pattern in CONFIRM_PATTERNS {
        if lower.contains(pattern) {
            return CommandSafety::NeedsConfirm(format!(
                "Questo comando modifica il sistema ({}). Serve conferma.",
                pattern.trim()
            ));
        }
    }

    CommandSafety::Safe
}

#[tauri::command]
pub fn run_command(command: String, confirmed: bool) -> Result<String, String> {
    println!("[boomer] run_command: {:?}, confirmed={}", command, confirmed);

    match check_command_safety(&command) {
        CommandSafety::Blocked(reason) => {
            return Err(format!("🚫 {}", reason));
        }
        CommandSafety::NeedsConfirm(reason) => {
            if !confirmed {
                return Err(format!("⚠️ CONFERMA RICHIESTA: {}\nComando: {}\nRichiamare con confirmed=true per procedere.", reason, command));
            }
        }
        CommandSafety::Safe => {}
    }

    #[cfg(target_os = "macos")]
    let output = Command::new("sh")
        .args(["-c", &command])
        .output()
        .map_err(|e| format!("Errore esecuzione: {}", e))?;

    #[cfg(target_os = "windows")]
    let output = Command::new("cmd")
        .args(["/C", &command])
        .output()
        .map_err(|e| format!("Errore esecuzione: {}", e))?;

    #[cfg(target_os = "linux")]
    let output = Command::new("sh")
        .args(["-c", &command])
        .output()
        .map_err(|e| format!("Errore esecuzione: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if output.status.success() {
        if stdout.trim().is_empty() {
            Ok("✅ Comando eseguito con successo (nessun output)".to_string())
        } else {
            Ok(stdout)
        }
    } else {
        Err(format!(
            "Comando fallito (exit code {}):\n{}{}",
            output.status.code().unwrap_or(-1),
            if !stdout.is_empty() { &stdout } else { "" },
            if !stderr.is_empty() { &stderr } else { "" }
        ))
    }
}

#[tauri::command]
pub fn run_applescript(script: String) -> Result<String, String> {
    println!("[boomer] run_applescript: {:?}", script);

    let lower = script.to_lowercase();
    for pattern in BLOCKED_PATTERNS {
        if lower.contains(pattern) {
            return Err(format!("🚫 Script bloccato: contiene '{}'", pattern));
        }
    }

    let output = Command::new("osascript")
        .args(["-e", &script])
        .output()
        .map_err(|e| format!("Errore AppleScript: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if output.status.success() {
        if stdout.trim().is_empty() {
            Ok("✅ Script eseguito con successo".to_string())
        } else {
            Ok(stdout)
        }
    } else {
        Err(format!("Errore: {}", stderr))
    }
}
