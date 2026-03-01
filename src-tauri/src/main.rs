#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri::api::process::{Command, CommandEvent};
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_window("main").unwrap();
            
            // Launch the Python sidecar
            // Tauri automatically resolves "api" to the correct binary based on the OS architecture
            // e.g., api-x86_64-pc-windows-msvc.exe
            let (mut rx, mut child) = Command::new_sidecar("api")
                .expect("Failed to create sidecar command")
                .spawn()
                .expect("Failed to spawn sidecar");

            // Listen for sidecar events (useful for debugging FastAPI startup)
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    if let CommandEvent::Stdout(line) = event {
                        println!("Sidecar: {}", line);
                    }
                }
            });

            // Kill the sidecar when the main window is closed to prevent zombie processes
            window.on_window_event(move |event| match event {
                tauri::WindowEvent::Destroyed => {
                    child.kill().expect("Failed to kill sidecar");
                }
                _ => {}
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
