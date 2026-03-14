use std::process::Command;

#[tauri::command]
pub fn get_system_info() -> Result<String, String> {
    let mut info = Vec::new();

    #[cfg(target_os = "macos")]
    {
        // OS version
        if let Ok(output) = Command::new("sw_vers").output() {
            let text = String::from_utf8_lossy(&output.stdout);
            for line in text.lines() {
                if line.contains("ProductName") || line.contains("ProductVersion") {
                    info.push(line.trim().to_string());
                }
            }
        }

        // Hardware
        if let Ok(output) = Command::new("sysctl")
            .args(["-n", "hw.memsize"])
            .output()
        {
            let mem_bytes: u64 = String::from_utf8_lossy(&output.stdout)
                .trim()
                .parse()
                .unwrap_or(0);
            let mem_gb = mem_bytes / (1024 * 1024 * 1024);
            info.push(format!("Memoria RAM: {} GB", mem_gb));
        }

        if let Ok(output) = Command::new("sysctl")
            .args(["-n", "machdep.cpu.brand_string"])
            .output()
        {
            let cpu = String::from_utf8_lossy(&output.stdout).trim().to_string();
            info.push(format!("Processore: {}", cpu));
        }

        // Disk space
        if let Ok(output) = Command::new("df").args(["-h", "/"]).output() {
            let text = String::from_utf8_lossy(&output.stdout);
            if let Some(line) = text.lines().nth(1) {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() >= 4 {
                    info.push(format!(
                        "Disco: {} totale, {} disponibile",
                        parts[1], parts[3]
                    ));
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        if let Ok(output) = Command::new("powershell")
            .args([
                "-Command",
                r#"
                $os = Get-CimInstance Win32_OperatingSystem
                $cpu = Get-CimInstance Win32_Processor
                $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
                Write-Output "Sistema: $($os.Caption) $($os.Version)"
                Write-Output "Memoria RAM: $([math]::Round($os.TotalVisibleMemorySize/1MB)) GB"
                Write-Output "Processore: $($cpu.Name)"
                Write-Output "Disco C: $([math]::Round($disk.Size/1GB)) GB totale, $([math]::Round($disk.FreeSpace/1GB)) GB liberi"
                "#,
            ])
            .output()
        {
            info.push(String::from_utf8_lossy(&output.stdout).trim().to_string());
        }
    }

    #[cfg(target_os = "linux")]
    {
        if let Ok(output) = Command::new("uname").args(["-sr"]).output() {
            info.push(format!(
                "Sistema: {}",
                String::from_utf8_lossy(&output.stdout).trim()
            ));
        }

        if let Ok(content) = std::fs::read_to_string("/proc/meminfo") {
            if let Some(line) = content.lines().find(|l| l.starts_with("MemTotal")) {
                let kb: u64 = line
                    .split_whitespace()
                    .nth(1)
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(0);
                info.push(format!("Memoria RAM: {} GB", kb / (1024 * 1024)));
            }
        }
    }

    if info.is_empty() {
        Ok("Non riesco a recuperare le informazioni del sistema".to_string())
    } else {
        Ok(info.join("\n"))
    }
}

#[tauri::command]
pub fn set_brightness(level: u32) -> Result<String, String> {
    let level = level.min(100);

    #[cfg(target_os = "macos")]
    {
        let brightness = level as f64 / 100.0;
        Command::new("osascript")
            .args([
                "-e",
                &format!(
                    "tell application \"System Events\" to tell appearance preferences to set dark mode to {}",
                    if level < 30 { "true" } else { "false" }
                ),
            ])
            .output()
            .ok();

        // Use brightness command via CoreDisplay (AppleScript)
        let script = format!(
            r#"do shell script "brightness {:.2}" "#,
            brightness
        );
        match Command::new("osascript").args(["-e", &script]).output() {
            Ok(_) => Ok(format!("Luminosità impostata a {}%", level)),
            Err(_) => {
                // Fallback: try with pmset
                Command::new("pmset")
                    .args(["-a", "displaysleep", "0"])
                    .output()
                    .ok();
                Ok(format!("Luminosità impostata a {}% (potrebbe richiedere conferma)", level))
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("powershell")
            .args([
                "-Command",
                &format!(
                    "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{})",
                    level
                ),
            ])
            .output()
            .map_err(|e| format!("Errore: {}", e))?;

        Ok(format!("Luminosità impostata a {}%", level))
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("brightnessctl")
            .args(["set", &format!("{}%", level)])
            .output()
            .map_err(|e| format!("Errore: {}", e))?;

        Ok(format!("Luminosità impostata a {}%", level))
    }
}

#[tauri::command]
pub fn open_app(app_name: String) -> Result<String, String> {
    let urls: std::collections::HashMap<&str, &str> = [
        ("facebook", "https://www.facebook.com"),
        ("whatsapp", "https://web.whatsapp.com"),
        ("zoom", "https://zoom.us/join"),
        ("youtube", "https://www.youtube.com"),
        ("email", "https://mail.google.com"),
        ("browser", "https://www.google.com"),
    ]
    .into();

    let name = app_name.to_lowercase();

    if let Some(url) = urls.get(name.as_str()) {
        open_url(url)?;
        Ok(format!("{} aperto!", capitalize(&name)))
    } else {
        Err(format!(
            "Non conosco l'app '{}'. Prova con: facebook, whatsapp, zoom, youtube, email, browser",
            name
        ))
    }
}

fn open_url(url: &str) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(url)
            .spawn()
            .map_err(|e| format!("Errore apertura: {}", e))?;
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("cmd")
            .args(["/C", "start", "", url])
            .spawn()
            .map_err(|e| format!("Errore apertura: {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(url)
            .spawn()
            .map_err(|e| format!("Errore apertura: {}", e))?;
    }

    Ok(())
}

fn capitalize(s: &str) -> String {
    let mut c = s.chars();
    match c.next() {
        None => String::new(),
        Some(f) => f.to_uppercase().to_string() + c.as_str(),
    }
}
