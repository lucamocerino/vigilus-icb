use crate::AppState;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use tauri::{AppHandle, Emitter, Manager, State};

static RECORDING: AtomicBool = AtomicBool::new(false);

/// Start recording audio from the default microphone.
/// When stopped, transcribes via Whisper and emits "whisper-result" event.
#[tauri::command]
pub async fn start_listening(
    app: AppHandle,
    state: State<'_, AppState>,
    language: String,
) -> Result<(), String> {
    RECORDING.store(true, Ordering::SeqCst);

    let model_path = resolve_model_path(&app, &state.whisper_model_path)?;
    let lang = if language == "it" { "it" } else { "en" };

    println!("[boomer] start_listening: model={}, lang={}", model_path, lang);

    // Spawn recording + transcription on a background thread
    std::thread::spawn(move || {
        println!("[boomer] Recording thread started, waiting for stop...");
        match record_and_transcribe(&model_path, lang) {
            Ok(text) => {
                println!("[boomer] Transcription result: {:?}", text);
                let _ = app.emit("whisper-result", text);
            }
            Err(e) => {
                eprintln!("[boomer] Whisper error: {}", e);
                let _ = app.emit("whisper-result", format!("[Errore: {}]", e));
            }
        }
        println!("[boomer] Recording thread done");
    });

    Ok(())
}

#[tauri::command]
pub async fn stop_listening(state: State<'_, AppState>) -> Result<(), String> {
    RECORDING.store(false, Ordering::SeqCst);
    *state.is_recording.lock().map_err(|e| e.to_string())? = false;
    Ok(())
}

/// Speak text using Piper TTS, then emit "piper-done" event.
#[tauri::command]
pub async fn speak_text(
    app: AppHandle,
    state: State<'_, AppState>,
    text: String,
    language: String,
) -> Result<(), String> {
    let model_path = resolve_model_path(&app, &state.piper_model_path)?;
    let _lang = language; // Piper model is language-specific

    std::thread::spawn(move || {
        match synthesize_speech(&text, &model_path) {
            Ok(_) => {
                let _ = app.emit("piper-done", ());
            }
            Err(e) => {
                eprintln!("Piper TTS error: {}", e);
                let _ = app.emit("piper-done", ());
            }
        }
    });

    Ok(())
}

#[tauri::command]
pub async fn stop_speaking() -> Result<(), String> {
    // TODO: implement audio playback cancellation
    Ok(())
}

fn resolve_model_path(app: &AppHandle, relative: &str) -> Result<String, String> {
    // Try resource dir first (bundled), then multiple dev paths
    if let Ok(resource_dir) = app.path().resource_dir() {
        let path = resource_dir.join(relative);
        if path.exists() {
            return Ok(path.to_string_lossy().to_string());
        }
    }

    // Dev mode: try various relative paths
    let candidates = [
        PathBuf::from(relative),                              // models/xxx (CWD = src-tauri)
        PathBuf::from(format!("src-tauri/{}", relative)),     // from project root
        PathBuf::from(format!("../{}", relative)),            // from target/debug
    ];

    for path in &candidates {
        if path.exists() {
            println!("[boomer] Model found: {:?}", path);
            return Ok(path.to_string_lossy().to_string());
        }
    }

    // Log CWD for debugging
    let cwd = std::env::current_dir().unwrap_or_default();
    Err(format!(
        "Model not found: {}. CWD={:?}. Download it first (see README).",
        relative, cwd
    ))
}

fn record_and_transcribe(model_path: &str, lang: &str) -> Result<String, String> {
    use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

    let host = cpal::default_host();
    let device = host
        .default_input_device()
        .ok_or("Nessun microfono trovato")?;

    let config = device
        .default_input_config()
        .map_err(|e| format!("Errore configurazione microfono: {}", e))?;

    let sample_rate = config.sample_rate().0;
    let channels = config.channels() as usize;
    let samples = std::sync::Arc::new(std::sync::Mutex::new(Vec::<f32>::new()));
    let samples_clone = samples.clone();

    let stream = device
        .build_input_stream(
            &config.into(),
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                if RECORDING.load(Ordering::SeqCst) {
                    let mut buf = samples_clone.lock().unwrap();
                    // Convert to mono if stereo
                    if channels > 1 {
                        for chunk in data.chunks(channels) {
                            let mono: f32 = chunk.iter().sum::<f32>() / channels as f32;
                            buf.push(mono);
                        }
                    } else {
                        buf.extend_from_slice(data);
                    }
                }
            },
            |err| eprintln!("Audio stream error: {}", err),
            None,
        )
        .map_err(|e| format!("Errore apertura stream audio: {}", e))?;

    stream
        .play()
        .map_err(|e| format!("Errore avvio registrazione: {}", e))?;

    // Record while RECORDING flag is true
    while RECORDING.load(Ordering::SeqCst) {
        std::thread::sleep(std::time::Duration::from_millis(100));
    }

    drop(stream);

    let audio_data = samples.lock().unwrap();
    if audio_data.is_empty() {
        return Err("Nessun audio registrato".to_string());
    }

    // Resample to 16kHz if needed (Whisper requires 16kHz)
    let audio_16k = if sample_rate != 16000 {
        resample(&audio_data, sample_rate, 16000)
    } else {
        audio_data.clone()
    };

    transcribe_whisper(model_path, &audio_16k, lang)
}

fn resample(input: &[f32], from_rate: u32, to_rate: u32) -> Vec<f32> {
    let ratio = to_rate as f64 / from_rate as f64;
    let output_len = (input.len() as f64 * ratio) as usize;
    let mut output = Vec::with_capacity(output_len);

    for i in 0..output_len {
        let src_idx = i as f64 / ratio;
        let idx = src_idx as usize;
        let frac = src_idx - idx as f64;

        let sample = if idx + 1 < input.len() {
            input[idx] * (1.0 - frac as f32) + input[idx + 1] * frac as f32
        } else if idx < input.len() {
            input[idx]
        } else {
            0.0
        };
        output.push(sample);
    }

    output
}

fn transcribe_whisper(model_path: &str, audio: &[f32], lang: &str) -> Result<String, String> {
    use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

    let ctx = WhisperContext::new_with_params(model_path, WhisperContextParameters::default())
        .map_err(|e| format!("Errore caricamento modello Whisper: {}", e))?;

    let mut state = ctx
        .create_state()
        .map_err(|e| format!("Errore creazione stato Whisper: {}", e))?;

    let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });
    params.set_language(Some(lang));
    params.set_print_progress(false);
    params.set_print_realtime(false);
    params.set_print_timestamps(false);
    params.set_suppress_blank(true);
    params.set_suppress_non_speech_tokens(true);

    state
        .full(params, audio)
        .map_err(|e| format!("Errore trascrizione: {}", e))?;

    let num_segments = state.full_n_segments().map_err(|e| format!("Errore segmenti: {}", e))?;
    let mut text = String::new();

    for i in 0..num_segments {
        if let Ok(segment) = state.full_get_segment_text(i) {
            text.push_str(&segment);
            text.push(' ');
        }
    }

    Ok(text.trim().to_string())
}

fn synthesize_speech(text: &str, _model_path: &str) -> Result<(), String> {
    use std::process::Command;

    // Try Piper first, fallback to macOS `say`
    let piper_available = Command::new("which").arg("piper").output()
        .map(|o| o.status.success()).unwrap_or(false);

    if piper_available {
        let output_path = std::env::temp_dir().join("boomer_tts_output.wav");
        let status = Command::new("piper")
            .arg("--model")
            .arg(_model_path)
            .arg("--output_file")
            .arg(&output_path)
            .stdin(std::process::Stdio::piped())
            .spawn()
            .and_then(|mut child| {
                use std::io::Write;
                if let Some(ref mut stdin) = child.stdin {
                    stdin.write_all(text.as_bytes()).ok();
                }
                child.wait()
            })
            .map_err(|e| format!("Errore Piper TTS: {}", e))?;

        if status.success() {
            play_wav(&output_path.to_string_lossy())?;
            let _ = std::fs::remove_file(&output_path);
            return Ok(());
        }
    }

    // Fallback: macOS native `say` command
    #[cfg(target_os = "macos")]
    {
        println!("[boomer] Using macOS 'say' for TTS");
        Command::new("say")
            .args(["-v", "Alice", text])  // Alice = Italian voice
            .status()
            .map_err(|e| format!("Errore TTS: {}", e))?;
        return Ok(());
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("powershell")
            .args(["-Command", &format!(
                "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('{}')",
                text.replace('\'', "''")
            )])
            .status()
            .map_err(|e| format!("Errore TTS: {}", e))?;
        return Ok(());
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("espeak")
            .args(["-v", "it", text])
            .status()
            .map_err(|e| format!("Errore TTS: {}", e))?;
        return Ok(());
    }

    #[allow(unreachable_code)]
    Err("Nessun motore TTS disponibile".to_string())
}

fn play_wav(path: &str) -> Result<(), String> {
    use std::process::Command;

    // macOS: afplay, Linux: aplay, Windows: powershell
    #[cfg(target_os = "macos")]
    {
        Command::new("afplay")
            .arg(path)
            .status()
            .map_err(|e| format!("Errore riproduzione audio: {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("aplay")
            .arg(path)
            .status()
            .map_err(|e| format!("Errore riproduzione audio: {}", e))?;
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("powershell")
            .args([
                "-Command",
                &format!(
                    "(New-Object System.Media.SoundPlayer '{}').PlaySync()",
                    path
                ),
            ])
            .status()
            .map_err(|e| format!("Errore riproduzione audio: {}", e))?;
    }

    Ok(())
}
