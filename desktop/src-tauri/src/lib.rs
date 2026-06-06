use tauri::Manager;
use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;

struct BackendProcess(Mutex<Option<Child>>);

impl Drop for BackendProcess {
    fn drop(&mut self) {
        if let Ok(mut child) = self.0.lock() {
            if let Some(mut process) = child.take() {
                let _ = process.kill();
            }
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let _ = app.get_webview_window("main");
            let backend = start_backend_if_needed();
            app.manage(BackendProcess(Mutex::new(backend)));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("app start failed");
}

fn start_backend_if_needed() -> Option<Child> {
    if backend_is_running() {
        return None;
    }

    let backend_dir = project_root().join("backend");
    let run_py = backend_dir.join("run.py");
    if !run_py.exists() {
        eprintln!("backend run.py not found: {}", run_py.display());
        return None;
    }

    spawn_python_backend("python", &[], &backend_dir, &run_py)
        .or_else(|| spawn_python_backend("py", &["-3"], &backend_dir, &run_py))
}

fn backend_is_running() -> bool {
    let addr: SocketAddr = match "127.0.0.1:8765".parse() {
        Ok(addr) => addr,
        Err(_) => return false,
    };
    TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok()
}

fn project_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|desktop_dir| desktop_dir.parent())
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
}

fn spawn_python_backend(
    executable: &str,
    prefix_args: &[&str],
    backend_dir: &PathBuf,
    run_py: &PathBuf,
) -> Option<Child> {
    let mut command = Command::new(executable);
    command
        .args(prefix_args)
        .arg(run_py)
        .current_dir(backend_dir)
        .env("PYTHONUTF8", "1");

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }

    match command.spawn() {
        Ok(child) => Some(child),
        Err(err) => {
            eprintln!("failed to start backend with {executable}: {err}");
            None
        }
    }
}
