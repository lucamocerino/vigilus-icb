use std::sync::Mutex;
use tauri::Manager;

mod commands;

pub struct AppState {
    pub whisper_model_path: String,
    pub piper_model_path: String,
    pub is_recording: Mutex<bool>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AppState {
            whisper_model_path: "models/ggml-small.bin".to_string(),
            piper_model_path: "models/it_IT-riccardo-x_low.onnx".to_string(),
            is_recording: Mutex::new(false),
        })
        .invoke_handler(tauri::generate_handler![
            commands::voice::start_listening,
            commands::voice::stop_listening,
            commands::voice::speak_text,
            commands::voice::stop_speaking,
            commands::audio::get_audio_devices,
            commands::audio::set_volume,
            commands::audio::fix_audio_issues,
            commands::system::get_system_info,
            commands::system::open_app,
            commands::system::set_brightness,
            commands::shell::run_command,
            commands::shell::run_applescript,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
