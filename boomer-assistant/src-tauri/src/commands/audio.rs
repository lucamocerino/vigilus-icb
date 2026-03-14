use std::process::Command;

#[tauri::command]
pub fn get_audio_devices() -> Result<String, String> {
    #[cfg(target_os = "macos")]
    {
        let output = Command::new("system_profiler")
            .arg("SPAudioDataType")
            .output()
            .map_err(|e| format!("Errore: {}", e))?;

        let text = String::from_utf8_lossy(&output.stdout);
        let mut devices = Vec::new();

        for line in text.lines() {
            let trimmed = line.trim();
            if !trimmed.is_empty()
                && !trimmed.starts_with("Audio:")
                && !trimmed.starts_with("Devices:")
                && trimmed.contains(':')
            {
                devices.push(trimmed.to_string());
            }
        }

        if devices.is_empty() {
            Ok("Nessun dispositivo audio trovato".to_string())
        } else {
            Ok(format!("Dispositivi audio trovati:\n{}", devices.join("\n")))
        }
    }

    #[cfg(target_os = "windows")]
    {
        let output = Command::new("powershell")
            .args([
                "-Command",
                "Get-CimInstance Win32_SoundDevice | Select-Object Name, Status | Format-List",
            ])
            .output()
            .map_err(|e| format!("Errore: {}", e))?;

        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    }

    #[cfg(target_os = "linux")]
    {
        let output = Command::new("pactl")
            .args(["list", "sinks", "short"])
            .output()
            .map_err(|e| format!("Errore: {}", e))?;

        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    }
}

#[tauri::command]
pub fn set_volume(level: u32) -> Result<String, String> {
    let level = level.min(100);

    #[cfg(target_os = "macos")]
    {
        let apple_vol = (level as f32 / 100.0 * 7.0).round() as u32;
        Command::new("osascript")
            .args(["-e", &format!("set volume output volume {}", level)])
            .output()
            .map_err(|e| format!("Errore impostazione volume: {}", e))?;

        let _ = apple_vol; // suppress warning
        Ok(format!("Volume impostato a {}%", level))
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("powershell")
            .args([
                "-Command",
                &format!(
                    "[Audio.Volume]::SetMasterVolumeLevelScalar({}/100, [System.Guid]::Empty)",
                    level
                ),
            ])
            .output()
            .map_err(|e| format!("Errore: {}", e))?;

        Ok(format!("Volume impostato a {}%", level))
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("pactl")
            .args(["set-sink-volume", "@DEFAULT_SINK@", &format!("{}%", level)])
            .output()
            .map_err(|e| format!("Errore: {}", e))?;

        Ok(format!("Volume impostato a {}%", level))
    }
}

#[tauri::command]
pub fn fix_audio_issues() -> Result<String, String> {
    let mut report = Vec::new();

    // Step 1: Check if audio devices exist
    report.push("🔍 Controllo dispositivi audio...".to_string());
    match get_audio_devices() {
        Ok(devices) => report.push(format!("✅ {}", devices)),
        Err(e) => {
            report.push(format!("❌ Problema dispositivi: {}", e));
            return Ok(report.join("\n"));
        }
    }

    // Step 2: Try to set volume to 70%
    report.push("🔊 Imposto volume a 70%...".to_string());
    match set_volume(70) {
        Ok(msg) => report.push(format!("✅ {}", msg)),
        Err(e) => report.push(format!("⚠️ Non riesco a cambiare il volume: {}", e)),
    }

    // Step 3: Unmute (macOS)
    #[cfg(target_os = "macos")]
    {
        report.push("🔇 Tolgo il muto...".to_string());
        match Command::new("osascript")
            .args(["-e", "set volume without output muted"])
            .output()
        {
            Ok(_) => report.push("✅ Audio non in muto".to_string()),
            Err(e) => report.push(format!("⚠️ Errore: {}", e)),
        }
    }

    report.push("✅ Diagnostica completata!".to_string());
    Ok(report.join("\n"))
}
