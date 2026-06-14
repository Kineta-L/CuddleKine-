use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;

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
            let backend = start_backend_if_needed(app);
            app.manage(BackendProcess(Mutex::new(backend)));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("app start failed");
}

fn start_backend_if_needed(app: &tauri::App) -> Option<Child> {
    if backend_is_running() {
        return None;
    }

    if let Some(child) = packaged_backend_candidates(app)
        .into_iter()
        .find_map(|candidate| spawn_packaged_backend(app, candidate))
    {
        return Some(child);
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

fn packaged_backend_candidates(app: &tauri::App) -> Vec<PathBuf> {
    let mut candidates = Vec::new();

    if let Ok(resource_dir) = app.path().resource_dir() {
        candidates.push(resource_dir.join("backend").join("cuddlekine-backend.exe"));
        candidates.push(
            resource_dir
                .join("resources")
                .join("backend")
                .join("cuddlekine-backend.exe"),
        );
    }

    candidates.push(
        project_root()
            .join("desktop")
            .join("src-tauri")
            .join("resources")
            .join("backend")
            .join("cuddlekine-backend.exe"),
    );

    candidates
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

fn spawn_packaged_backend(app: &tauri::App, executable: PathBuf) -> Option<Child> {
    if !executable.exists() {
        return None;
    }

    let resource_root = resource_root(app);
    let app_data = app
        .path()
        .app_local_data_dir()
        .unwrap_or_else(|_| project_root().join("data").join("app"));

    let mut command = Command::new(&executable);
    command
        .current_dir(executable.parent().unwrap_or_else(|| executable.as_path()))
        .env("PYTHONUTF8", "1")
        .env("CUDDLEKINE_APP_ROOT", &resource_root)
        .env("CUDDLEKINE_RESOURCE_DIR", &resource_root)
        .env("CUDDLEKINE_DATA_DIR", app_data.join("data"))
        .env("CUDDLEKINE_OUTPUT_DIR", app_data.join("outputs"));

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }

    match command.spawn() {
        Ok(child) => Some(child),
        Err(err) => {
            eprintln!(
                "failed to start packaged backend {}: {err}",
                executable.display()
            );
            None
        }
    }
}

fn resource_root(app: &tauri::App) -> PathBuf {
    let Ok(resource_dir) = app.path().resource_dir() else {
        return project_root();
    };

    if resource_dir.join("comfyui").join("workflows").exists() {
        return resource_dir;
    }

    let nested = resource_dir.join("resources");
    if nested.join("comfyui").join("workflows").exists() {
        return nested;
    }

    resource_dir
}
