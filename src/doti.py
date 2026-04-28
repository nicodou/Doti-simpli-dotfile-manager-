#!/usr/bin/env python3
import sys
import json
import argparse
import os
import subprocess
from pathlib import Path


def log(message, log_type="info"):
    """
    Función auxiliar para imprimir mensajes con colores ANSI estilo Homebrew
    
    Args:
        message (str): Mensaje a imprimir
        log_type (str): Tipo de mensaje ('success', 'error', 'info', 'warning', 'step')
    """
    # Códigos de color ANSI
    RESET = '\033[0m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    
    if log_type == "success":
        print(f"{GREEN}==> [OK]{RESET} {message}")
    elif log_type == "error":
        print(f"{RED}==> [ERROR]{RESET} {message}", file=sys.stderr)
    elif log_type == "warning":
        print(f"{YELLOW}==> [WARN]{RESET} {message}")
    elif log_type == "step":
        print(f"{BLUE}==>{RESET} {BOLD}{message}{RESET}")
    else:  # info
        print(f"{BLUE}==>{RESET} {message}")


class Doti:
    def __init__(self):
        self.home = Path.home()
        self.doti_dir = self.home / ".doti"
        self.storage_dir = self.doti_dir / "storage"
        self.config_file = self.doti_dir / "config.json"
        self.hooks_dir = self.doti_dir / "hooks"
    
    def init(self, dry_run=False):
        """Crea la estructura de carpetas ~/.doti/storage y ~/.doti/config.json"""
        try:
            if dry_run:
                log(f"Would create directory: {self.doti_dir}", "info")
                log(f"Would create directory: {self.storage_dir}", "info")
                log(f"Would create directory: {self.hooks_dir}", "info")
                
                if not self.config_file.exists():
                    log(f"Would create config file: {self.config_file}", "info")
                else:
                    log(f"Config file already exists: {self.config_file}", "info")
                
                log(f"doti would be initialized at {self.doti_dir}", "info")
                return True
            
            self.doti_dir.mkdir(exist_ok=True)
            self.storage_dir.mkdir(exist_ok=True)
            self.hooks_dir.mkdir(exist_ok=True)
            
            if not self.config_file.exists():
                self.config_file.write_text(json.dumps({}, indent=2))
                log("Config file created", "success")
            
            log(f"doti initialized at {self.doti_dir}", "success")
            return True
            
        except OSError as e:
            log(f"Failed to initialize: {e}", "error")
            return False
    
    def _ensure_directories(self, dry_run=False):
        """Crea las carpetas necesarias si no existen"""
        if not self.doti_dir.exists():
            return self.init(dry_run=dry_run)
        return True
    
    def _load_config(self):
        """Carga la configuración desde config.json"""
        try:
            return json.loads(self.config_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def run_hook(self, hook_name, dry_run=False):
        """
        Ejecuta un script de hook si existe
        
        Args:
            hook_name (str): Nombre del hook (ej: 'pre-deploy', 'post-add')
            dry_run (bool): Si True, simula la ejecución sin ejecutar el script
        
        Returns:
            bool: True si el hook se ejecutó correctamente o no existía
        """
        hook_file = self.hooks_dir / f"{hook_name}.sh"
        
        if not hook_file.exists():
            # Silencioso si no hay hook - no es un error
            return True
        
        if dry_run:
            log(f"[DRY RUN] Would execute hook: {hook_name}", "info")
            return True
        
        # Verificar permisos de ejecución
        if not os.access(hook_file, os.X_OK):
            log(f"Hook exists but not executable: {hook_file}", "warning")
            return True
        
        try:
            log(f"[HOOK] Executing {hook_name}...", "info")
            result = subprocess.run([str(hook_file)], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30,
                                  check=False)  # Timeout de 30 segundos
            
            if result.returncode == 0:
                log(f"[HOOK] {hook_name} completed successfully", "success")
                if result.stdout.strip():
                    log(f"[HOOK] Output: {result.stdout.strip()}", "info")
            else:
                log(f"[HOOK] {hook_name} failed with exit code {result.returncode}", "warning")
                if result.stderr.strip():
                    log(f"[HOOK] Error: {result.stderr.strip()}", "warning")
            
            return True
            
        except subprocess.TimeoutExpired:
            log(f"[HOOK] {hook_name} timed out after 30 seconds", "warning")
            return True
        except OSError as e:
            log(f"[HOOK] Failed to execute {hook_name}: {e}", "warning")
            return True
    
    def _save_config(self, config, dry_run=False):
        """Guarda la configuración en config.json"""
        if dry_run:
            log(f"Would save config to: {self.config_file}", "info")
            return True
            
        try:
            self.config_file.write_text(json.dumps(config, indent=2))
        except OSError as e:
            log(f"Failed to save config: {e}", "error")
            return False
        return True
    
    def add_file(self, file_path, dry_run=False):
        """
        Agrega un archivo a doti
        
        Args:
            file_path (str): Ruta del archivo a agregar
            dry_run (bool): Si True, simula la operación sin hacer cambios
            
        Returns:
            bool: True si se agregó exitosamente, False en caso contrario
        """
        # Ejecutar hook pre-add
        self.run_hook("pre-add", dry_run=dry_run)
        
        if not self._ensure_directories(dry_run=dry_run):
            return False
            
        file_path = Path(file_path).resolve()
        
        log(f"Adding {file_path.name}...", "step")
        
        # Verificación: Verifica que el archivo existe
        if not file_path.exists():
            log(f"File '{file_path}' does not exist", "error")
            return False
        
        if not file_path.is_file():
            log(f"'{file_path}' is not a file", "error")
            return False
        
        # Manejo de errores: Si el archivo ya está gestionado, avisa al usuario
        config = self._load_config()
        if str(file_path) in config:
            log(f"File '{file_path}' is already managed", "warning")
            return False
        
        # Almacenamiento: Mueve el archivo a .doti/storage/
        storage_path = self._get_unique_storage_path(file_path)
        
        try:
            if dry_run:
                log(f"[DRY RUN] Would move {file_path} to {storage_path}", "info")
                log(f"[DRY RUN] Would create symlink: {file_path} -> {storage_path}", "info")
                
                # Simular registro en configuración
                config[str(file_path)] = {
                    "storage_path": str(storage_path),
                    "original_name": file_path.name
                }
                log(f"[DRY RUN] Would update config with: {file_path}", "info")
                
                log(f"[DRY RUN] Would successfully add: {file_path.name}", "info")
                # Ejecutar hook post-add en dry run
                self.run_hook("post-add", dry_run=dry_run)
                return True
            
            # Mover archivo a storage
            file_path.rename(storage_path)
            log(f"Moved to storage: {storage_path.name}", "success")
            
            # Symlink: Crea un enlace simbólico desde la ubicación original
            file_path.symlink_to(storage_path)
            log(f"Created symlink: {file_path}", "success")
            
            # Registro: Guarda la relación en ~/.doti/config.json
            config[str(file_path)] = {
                "storage_path": str(storage_path),
                "original_name": file_path.name
            }
            
            if not self._save_config(config, dry_run=dry_run):
                return False
            
            log(f"Successfully added: {file_path.name}", "success")
            
            # Ejecutar hook post-add
            self.run_hook("post-add", dry_run=dry_run)
            return True
            
        except OSError as e:
            log(f"Error: {e}", "error")
            return False
    
    def _get_unique_storage_path(self, file_path):
        """
        Obtiene una ruta única en storage para el archivo, manejando conflictos de nombres
        
        Args:
            file_path (Path): Ruta original del archivo
            
        Returns:
            Path: Ruta única en storage
        """
        storage_path = self.storage_dir / file_path.name
        counter = 1
        while storage_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            storage_path = self.storage_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        return storage_path
    
    def add(self, file_path, dry_run=False):
        """Método de compatibilidad que llama a add_file"""
        return self.add_file(file_path, dry_run=dry_run)
    
    def unlink(self, file_path, restore=True, dry_run=False):
        """
        Elimina el symlink y opcionalmente restaura el archivo original
        
        Args:
            file_path (str): Ruta del symlink a eliminar
            restore (bool): Si True, mueve el archivo de vuelta a su ubicación original
            dry_run (bool): Si True, simula la operación sin hacer cambios
            
        Returns:
            bool: True si la operación fue exitosa
        """
        # Ejecutar hook pre-unlink
        self.run_hook("pre-unlink", dry_run=dry_run)
        
        file_path = Path(file_path).resolve()
        config = self._load_config()
        
        # Verificar si el archivo está gestionado
        if str(file_path) not in config:
            log(f"File '{file_path}' is not managed by doti", "error")
            return False
        
        data = config[str(file_path)]
        storage_path = Path(data["storage_path"])
        
        try:
            log(f"Unlinking {file_path.name}...", "step")
            
            if dry_run:
                log(f"[DRY RUN] Would remove symlink: {file_path}", "info")
                
                if restore and storage_path.exists():
                    log(f"[DRY RUN] Would restore {file_path.name} to original location", "info")
                    log(f"[DRY RUN] Would move {storage_path} to {file_path}", "info")
                
                log(f"[DRY RUN] Would remove {file_path} from config", "info")
                log(f"[DRY RUN] Unlink completed: {file_path.name}", "info")
                # Ejecutar hook post-unlink en dry run
                self.run_hook("post-unlink", dry_run=dry_run)
                return True
            
            # Eliminar symlink
            if file_path.is_symlink() or file_path.exists():
                file_path.unlink()
                log(f"Symlink removed: {file_path.name}", "success")
            
            # Restaurar archivo si se solicita
            if restore and storage_path.exists():
                log(f"Restoring {file_path.name} to original location...", "step")
                storage_path.rename(file_path)
                log(f"File restored: {file_path.name}", "success")
            
            # Eliminar de configuración
            del config[str(file_path)]
            if not self._save_config(config, dry_run=dry_run):
                return False
            
            log(f"Unlink completed: {file_path.name}", "success")
            
            # Ejecutar hook post-unlink
            self.run_hook("post-unlink", dry_run=dry_run)
            return True
            
        except OSError as e:
            log(f"Error during unlink: {e}", "error")
            return False
    
    def deploy(self, dry_run=False):
        """Despliega todos los symlinks desde la configuración"""
        # Ejecutar hook pre-deploy
        self.run_hook("pre-deploy", dry_run=dry_run)
        
        if not self._ensure_directories(dry_run=dry_run):
            return False
            
        config = self._load_config()
        
        if not config:
            log("No files to deploy", "info")
            # Ejecutar hook post-deploy incluso si no hay archivos
            self.run_hook("post-deploy", dry_run=dry_run)
            return True
        
        log(f"Deploying {len(config)} symlinks...", "step")
        
        deployed = 0
        failed = 0
        
        for original_path, data in config.items():
            original_path = Path(original_path)
            storage_path = Path(data["storage_path"])
            
            try:
                if dry_run:
                    log(f"[DRY RUN] Would remove existing: {original_path}", "info")
                    log(f"[DRY RUN] Would create symlink: {original_path} -> {storage_path}", "info")
                    deployed += 1
                    continue
                
                # Eliminar si existe (archivo o symlink)
                if original_path.exists() or original_path.is_symlink():
                    original_path.unlink()
                
                # Crear symlink
                original_path.symlink_to(storage_path)
                log(f"Deployed: {original_path.name}", "success")
                deployed += 1
                
            except OSError as e:
                log(f"Failed to deploy {original_path.name}: {e}", "error")
                failed += 1
        
        if dry_run:
            log(f"[DRY RUN] Would deploy {deployed} symlinks", "info")
        else:
            log(f"Deploy Summary: {deployed} successful, {failed} failed", "info")
        
        # Ejecutar hook post-deploy
        self.run_hook("post-deploy", dry_run=dry_run)
        
        return failed == 0
    
    def list(self):
        """Lista los archivos gestionados"""
        if not self._ensure_directories():
            return
            
        config = self._load_config()
        
        if not config:
            log("No managed files", "info")
            return
        
        log(f"Listing {len(config)} managed files...", "step")
        print()
        
        for original_path, data in config.items():
            storage_path = data["storage_path"]
            original_name = data["original_name"]
            
            if Path(original_path).exists():
                log(f"{original_path}", "success")
            else:
                log(f"{original_path}", "error")
            print(f"  → {storage_path}")
            print(f"  Original name: {original_name}")
            print()
    
    def edit(self, file_path):
        """
        Abre un archivo gestionado en el editor predeterminado
        
        Args:
            file_path (str): Ruta del archivo gestionado a editar
            
        Returns:
            bool: True si se abrió exitosamente
        """
        config = self._load_config()
        file_path = Path(file_path).resolve()
        
        # Verificar si el archivo está gestionado
        if str(file_path) not in config:
            log(f"File '{file_path}' is not managed by doti", "error")
            return False
        
        data = config[str(file_path)]
        storage_path = Path(data["storage_path"])
        
        if not storage_path.exists():
            log(f"Storage file not found: {storage_path}", "error")
            return False
        
        # Obtener editor
        editor = os.environ.get("EDITOR", "nano")
        
        try:
            log(f"Opening {file_path.name} with {editor}...", "step")
            subprocess.run([editor, str(storage_path)], check=True)
            log(f"File closed: {file_path.name}", "success")
            return True
            
        except subprocess.CalledProcessError as e:
            log(f"Failed to open editor: {e}", "error")
            return False
        except FileNotFoundError:
            log(f"Editor '{editor}' not found. Please install or set EDITOR environment variable", "error")
            return False
    
    def doctor(self):
        """
        Verifica el estado de todos los symlinks gestionados
        
        Returns:
            bool: True si todos los symlinks están sanos, False si hay problemas
        """
        if not self._ensure_directories():
            return False
            
        config = self._load_config()
        
        if not config:
            log("No managed files", "info")
            return True
        
        log("Checking doti configuration...", "step")
        
        healthy = 0
        broken = 0
        missing = 0
        
        for original_path, data in config.items():
            original_path = Path(original_path)
            storage_path = Path(data["storage_path"])
            
            print(f"\n{original_path}")
            print(f"  → {storage_path}")
            
            # Verificar archivo en storage
            if not storage_path.exists():
                log("Storage file missing", "error")
                missing += 1
                continue
            
            # Verificar symlink
            if not original_path.exists():
                log("Symlink missing", "error")
                broken += 1
            elif not original_path.is_symlink():
                log("Not a symlink", "warning")
                broken += 1
            else:
                # Verificar que el symlink apunte al archivo correcto
                try:
                    target = original_path.resolve()
                    if target == storage_path.resolve():
                        log("Healthy symlink", "success")
                        healthy += 1
                    else:
                        log("Symlink points to wrong target", "error")
                        broken += 1
                except OSError:
                    log("Broken symlink", "error")
                    broken += 1
        
        # Resumen
        print("\nDoctor Summary:")
        log(f"Healthy symlinks: {healthy}", "success")
        
        if broken > 0:
            log(f"Broken symlinks: {broken}", "error")
        
        if missing > 0:
            log(f"Missing storage files: {missing}", "error")
        
        total_issues = broken + missing
        if total_issues == 0:
            log("All symlinks are healthy!", "success")
            return True
        else:
            log(f"Found {total_issues} issue(s). Run 'deploy' to fix broken symlinks.", "warning")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="doti - Gestor de dotfiles",
        prog="doti"
    )
    
    # Argumento global --dry-run
    parser.add_argument("--dry-run", action="store_true", 
                       help="Simulate operations without making changes")
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # Comando init
    subparsers.add_parser("init", help="Inicializa doti")
    
    # Comando add
    add_parser = subparsers.add_parser("add", help="Agrega un archivo a doti")
    add_parser.add_argument("file_path", help="Ruta del archivo a agregar")
    
    # Comando deploy
    subparsers.add_parser("deploy", help="Despliega todos los symlinks")
    
    # Comando list
    subparsers.add_parser("list", help="Lista archivos gestionados")
    
    # Comando unlink
    unlink_parser = subparsers.add_parser("unlink", help="Elimina symlink y restaura archivo")
    unlink_parser.add_argument("file_path", help="Ruta del symlink a eliminar")
    unlink_parser.add_argument("--no-restore", action="store_true", 
                              help="No restaurar el archivo a su ubicación original")
    
    # Comando edit
    edit_parser = subparsers.add_parser("edit", help="Edita un archivo gestionado")
    edit_parser.add_argument("file_path", help="Ruta del archivo gestionado a editar")
    
    # Comando doctor
    subparsers.add_parser("doctor", help="Verifica estado de los symlinks")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Advertencia de Dry Run si está activo
    if args.dry_run:
        log("Dry run mode enabled. No changes will be made.", "warning")
    
    doti = Doti()
    
    if args.command == "init":
        success = doti.init(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    elif args.command == "add":
        success = doti.add(args.file_path, dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    elif args.command == "deploy":
        success = doti.deploy(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    elif args.command == "list":
        doti.list()
    elif args.command == "unlink":
        restore = not args.no_restore
        success = doti.unlink(args.file_path, restore=restore, dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    elif args.command == "edit":
        success = doti.edit(args.file_path)
        sys.exit(0 if success else 1)
    elif args.command == "doctor":
        success = doti.doctor()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
