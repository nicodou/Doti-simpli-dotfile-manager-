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
        self.doti_dir = Path.home() / ".doti"
        self.storage_dir = self.doti_dir / "storage"
        self.hooks_dir = self.doti_dir / "hooks"
        self.config_file = self.doti_dir / "config.json"
        
        # Cache de configuración para reducir I/O
        self._config_cache = None
        self._config_dirty = False
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
    
    def _load_config(self, force=False):
        """Carga la configuración desde config.json con cache"""
        if self._config_cache is None or force:
            try:
                self._config_cache = json.loads(self.config_file.read_text())
            except (json.JSONDecodeError, FileNotFoundError):
                self._config_cache = {}
        return self._config_cache
    
    def _mark_config_dirty(self):
        """Marca la configuración como needing save"""
        self._config_dirty = True
    
    def _save_config_if_dirty(self, dry_run=False):
        """Guarda la configuración solo si está sucia"""
        if not self._config_dirty or dry_run:
            return True
            
        try:
            self.config_file.write_text(json.dumps(self._config_cache, indent=2))
            self._config_dirty = False
            return True
        except OSError as e:
            log(f"Failed to save config: {e}", "error")
            return False
    
    def run_hook(self, hook_name, context=None, dry_run=False, strict_mode=False):
        """
        Ejecuta un script de hook si existe con contexto y variables de entorno
        
        Args:
            hook_name (str): Nombre del hook (ej: 'pre-deploy', 'post-add')
            context (dict): Contexto para el hook (original_path, storage_path, etc.)
            dry_run (bool): Si True, simula la ejecución sin ejecutar el script
            strict_mode (bool): Si True, detiene la ejecución si el hook falla
            
        Returns:
            bool: True si el hook se ejecutó correctamente o no existía, False si falló y strict_mode=True
        """
        hook_file = self.hooks_dir / f"{hook_name}.sh"
        
        if not hook_file.exists():
            # Silencioso si no hay hook - no es un error
            return True
        
        if dry_run:
            context_info = []
            if context:
                for key, value in context.items():
                    if 'path' in key.lower():
                        context_info.append(f"{key}={value}")
                    elif key in ['operation', 'count']:
                        context_info.append(f"{key}={value}")
            
            if context_info:
                log(f"[DRY RUN] Would execute hook: {hook_name} (context: {', '.join(context_info)})", "info")
            else:
                log(f"[DRY RUN] Would execute hook: {hook_name}", "info")
            return True
        
        # Verificar permisos de ejecución
        if not os.access(hook_file, os.X_OK):
            log(f"Hook exists but not executable: {hook_file}", "warning")
            return True
        
        # Preparar variables de entorno
        env = os.environ.copy()
        if context:
            # Variables de entorno DOTI_*
            if 'original_path' in context:
                env['DOTI_ORIGINAL_PATH'] = str(context['original_path'])
            if 'storage_path' in context:
                env['DOTI_STORAGE_PATH'] = str(context['storage_path'])
            if 'operation' in context:
                env['DOTI_OPERATION'] = context['operation']
            if 'count' in context:
                env['DOTI_COUNT'] = str(context['count'])
            
            # Variables globales útiles
            env['DOTI_HOOK_NAME'] = hook_name
            env['DOTI_STORAGE_DIR'] = str(self.storage_dir)
            env['DOTI_CONFIG_FILE'] = str(self.config_file)
        
        # Preparar argumentos de línea de comandos
        cmd = [str(hook_file)]
        if context and 'original_path' in context:
            cmd.append(str(context['original_path']))
        if context and 'storage_path' in context:
            cmd.append(str(context['storage_path']))
        
        try:
            context_info = []
            if context:
                for key, value in context.items():
                    if 'path' in key.lower():
                        context_info.append(f"{key}={value.name if hasattr(value, 'name') else value}")
                    elif key in ['operation', 'count']:
                        context_info.append(f"{key}={value}")
            
            if context_info:
                log(f"[HOOK] Executing {hook_name} (context: {', '.join(context_info)})...", "info")
            else:
                log(f"[HOOK] Executing {hook_name}...", "info")
            
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30,
                                  check=False,
                                  env=env)  # Timeout de 30 segundos
            
            if result.returncode == 0:
                log(f"[HOOK] {hook_name} completed successfully", "success")
                if result.stdout.strip():
                    log(f"[HOOK] Output: {result.stdout.strip()}", "info")
                return True
            else:
                log(f"[HOOK] {hook_name} failed with exit code {result.returncode}", "warning")
                if result.stderr.strip():
                    log(f"[HOOK] Error: {result.stderr.strip()}", "warning")
                
                # En modo estricto, los hooks pre-* que fallan detienen la operación
                if strict_mode and hook_name.startswith('pre-'):
                    log("Strict mode: stopping due to pre-hook failure", "error")
                    return False
                
                return True
            
        except subprocess.TimeoutExpired:
            log(f"[HOOK] {hook_name} timed out after 30 seconds", "warning")
            if strict_mode and hook_name.startswith('pre-'):
                log("[HOOK] Strict mode: stopping due to pre-hook timeout", "error")
                return False
            return True
        except OSError as e:
            log(f"[HOOK] Failed to execute {hook_name}: {e}", "warning")
            if strict_mode and hook_name.startswith('pre-'):
                log("[HOOK] Strict mode: stopping due to pre-hook execution error", "error")
                return False
            return True
    
    def _is_managed_symlink(self, path, storage_path):
        """
        Verifica si un path es un symlink gestionado por doti
        
        Args:
            path (Path): Ruta a verificar
            storage_path (Path): Ruta esperada en storage
            
        Returns:
            bool: True si es un symlink gestionado, False en caso contrario
        """
        if not path.is_symlink():
            return False
        
        try:
            target = path.readlink()
            # Comparar rutas absolutas para evitar problemas relativos
            return target.resolve() == storage_path.resolve()
        except (OSError, RuntimeError):
            return False
    
    def _save_config(self, config, dry_run=False):
        """Guarda la configuración en config.json (deprecated - usar cache)"""
        if dry_run:
            log(f"Would save config to: {self.config_file}", "info")
            return True
            
        # Actualizar cache y marcar como sucia
        self._config_cache = config
        self._config_dirty = True
        return self._save_config_if_dirty(dry_run=dry_run)
    
    def add_file(self, file_path, dry_run=False, strict_mode=False):
        """
        Agrega un archivo a doti
        
        Args:
            file_path (str): Ruta del archivo a agregar
            dry_run (bool): Si True, simula la operación sin hacer cambios
            strict_mode (bool): Si True, detiene la ejecución si los pre-hooks fallan
            
        Returns:
            bool: True si se agregó exitosamente, False en caso contrario
        """
        # Ejecutar hook pre-add
        context = {'operation': 'add'}
        if not self.run_hook("pre-add", context=context, dry_run=dry_run, strict_mode=strict_mode):
            return False
        
        if not self._ensure_directories(dry_run=dry_run):
            return False
            
        file_path = Path(file_path).absolute()   
        config = self._load_config()
        
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
                self._config_cache[str(file_path)] = {
                    "storage_path": str(storage_path),
                    "original_name": file_path.name
                }
                self._mark_config_dirty()
                log(f"[DRY RUN] Would update config with: {file_path}", "info")
                
                log(f"[DRY RUN] Would successfully add: {file_path.name}", "info")
                # Ejecutar hook post-add en dry run
                context = {
                    'original_path': file_path,
                    'storage_path': storage_path,
                    'operation': 'add'
                }
                self.run_hook("post-add", context=context, dry_run=dry_run)
                return True
            
            # Mover archivo a storage
            file_path.rename(storage_path)
            log(f"Moved to storage: {storage_path.name}", "success")
            
            # Symlink: Crea un enlace simbólico desde la ubicación original
            file_path.symlink_to(storage_path)
            log(f"Created symlink: {file_path}", "success")
            
            # Registro: Guarda la relación en ~/.doti/config.json
            self._config_cache[str(file_path)] = {
                "storage_path": str(storage_path),
                "original_name": file_path.name
            }
            self._mark_config_dirty()
            
            if not self._save_config_if_dirty(dry_run=dry_run):
                return False
            
            log(f"Successfully added: {file_path.name}", "success")
            
            # Ejecutar hook post-add
            context = {
                'original_path': file_path,
                'storage_path': storage_path,
                'operation': 'add'
            }
            self.run_hook("post-add", context=context, dry_run=dry_run)
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
    
    def add(self, file_path, dry_run=False, strict_mode=False):
        """Método de compatibilidad que llama a add_file"""
        return self.add_file(file_path, dry_run=dry_run)
    
    def unlink(self, file_path, restore=True, dry_run=False, strict_mode=False):
        """
        Elimina el symlink y opcionalmente restaura el archivo original
        
        Args:
            file_path (str): Ruta del symlink a eliminar
            restore (bool): Si True, mueve el archivo de vuelta a su ubicación original
            dry_run (bool): Si True, simula la operación sin hacer cambios
            strict_mode (bool): Si True, detiene la ejecución si los pre-hooks fallan
            
        Returns:
            bool: True si la operación fue exitosa
        """
        # Ejecutar hook pre-unlink
        context = {'operation': 'unlink', 'restore': restore}
        if not self.run_hook("pre-unlink", context=context, dry_run=dry_run, strict_mode=strict_mode):
            return False
        
        # Usar absolute() para búsqueda en config (consistente con add_file)
        file_path = Path(file_path).absolute()
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
                log(f"[DRY RUN] Would validate symlink: {file_path}", "info")
                log(f"[DRY RUN] Would remove symlink: {file_path}", "info")
                
                if restore and storage_path.exists():
                    log(f"[DRY RUN] Would restore {file_path.name} to original location", "info")
                    log(f"[DRY RUN] Would move {storage_path} to {file_path}", "info")
                
                log(f"[DRY RUN] Would remove {file_path} from config", "info")
                log(f"[DRY RUN] Unlink completed: {file_path.name}", "info")
                # Ejecutar hook post-unlink en dry run
                context = {
                    'original_path': file_path,
                    'storage_path': storage_path,
                    'operation': 'unlink',
                    'restore': restore
                }
                self.run_hook("post-unlink", context=context, dry_run=dry_run)
                return True
            
            # VALIDACIÓN DE SEGURIDAD: Solo operar en symlinks gestionados
            if not file_path.exists():
                log(f"Symlink not found: {file_path}", "error")
                return False
            
            if not file_path.is_symlink():
                log(f"SECURITY ERROR: '{file_path}' is not a symlink - refusing to delete", "error")
                log(f"This appears to be a real file. Use 'rm {file_path}' if you want to delete it.", "info")
                return False
            
            if not self._is_managed_symlink(file_path, storage_path):
                log(f"SECURITY ERROR: '{file_path}' is a symlink but not managed by doti", "error")
                log(f"Current target: {file_path.readlink()}", "info")
                log(f"Expected target: {storage_path}", "info")
                log("Refusing to delete unmanaged symlink for safety", "warning")
                return False
            
            # Eliminar symlink (validado como gestionado)
            file_path.unlink()
            log(f"Managed symlink removed: {file_path.name}", "success")
            
            # Restaurar archivo si se solicita
            if restore and storage_path.exists():
                log(f"Restoring {file_path.name} to original location...", "step")
                storage_path.rename(file_path)
                log(f"File restored: {file_path.name}", "success")
            
            # Eliminar de configuración
            del self._config_cache[str(file_path)]
            self._mark_config_dirty()
            
            if not self._save_config_if_dirty(dry_run=dry_run):
                return False
            
            log(f"Unlink completed: {file_path.name}", "success")
            
            # Ejecutar hook post-unlink
            context = {
                'original_path': file_path,
                'storage_path': storage_path,
                'operation': 'unlink',
                'restore': restore
            }
            self.run_hook("post-unlink", context=context, dry_run=dry_run)
            return True
            
        except OSError as e:
            log(f"Error during unlink: {e}", "error")
            return False
    
    def deploy(self, dry_run=False, strict_mode=False):
        """Despliega todos los symlinks desde la configuración"""
        # Ejecutar hook pre-deploy
        config = self._load_config()
        context = {
            'operation': 'deploy',
            'count': len(config) if config else 0,
            'storage_dir': self.storage_dir,
            'config_file': self.config_file
        }
        if not self.run_hook("pre-deploy", context=context, dry_run=dry_run, strict_mode=strict_mode):
            return False
        
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
        conflicted = 0
        skipped = 0
        failed = 0
        
        for original_path, data in config.items():
            original_path = Path(original_path)
            storage_path = Path(data["storage_path"])
            
            try:
                if dry_run:
                    log(f"[DRY RUN] Would validate: {original_path}", "info")
                    
                    # Validación en dry run
                    if original_path.exists():
                        if original_path.is_symlink():
                            if self._is_managed_symlink(original_path, storage_path):
                                log(f"[DRY RUN] Would recreate managed symlink: {original_path}", "info")
                                deployed += 1
                            else:
                                log(f"[DRY RUN] Would skip unmanaged symlink: {original_path}", "warning")
                                conflicted += 1
                        else:
                            log(f"[DRY RUN] Would skip real file (conflict): {original_path}", "warning")
                            conflicted += 1
                    else:
                        log(f"[DRY RUN] Would create symlink: {original_path} -> {storage_path}", "info")
                        deployed += 1
                    continue
                
                # VALIDACIÓN DE SEGURIDAD EN DEPLOY REAL
                if original_path.exists():
                    if original_path.is_symlink():
                        if self._is_managed_symlink(original_path, storage_path):
                            # Symlink gestionado correcto - recrear
                            original_path.unlink()
                            original_path.symlink_to(storage_path)
                            log(f"Recreated managed symlink: {original_path.name}", "success")
                            deployed += 1
                        else:
                            # Symlink existente pero no gestionado - CONFLICTO
                            log(f"CONFLICT: '{original_path}' exists as unmanaged symlink", "warning")
                            log(f"Current target: {original_path.readlink()}", "info")
                            log(f"Expected target: {storage_path}", "info")
                            log("Skipping for safety. Remove manually if you want to replace", "info")
                            conflicted += 1
                    else:
                        # Archivo real existente - CONFLICTO
                        log(f"CONFLICT: '{original_path}' exists as real file", "warning")
                        log("Refusing to overwrite real file for safety", "error")
                        log(f"Move or remove the file manually, then run deploy again", "info")
                        conflicted += 1
                else:
                    # No existe - crear symlink
                    original_path.symlink_to(storage_path)
                    log(f"Created symlink: {original_path.name}", "success")
                    deployed += 1
                
            except OSError as e:
                log(f"Failed to deploy {original_path.name}: {e}", "error")
                failed += 1
        
        # Resumen mejorado
        if dry_run:
            log(f"[DRY RUN] Deploy Summary: {deployed} would be deployed, {conflicted} conflicted, {skipped} skipped", "info")
        else:
            log(f"Deploy Summary: {deployed} successful, {conflicted} conflicted, {skipped} skipped, {failed} failed", "info")
            
            if conflicted > 0:
                log(f"{conflicted} conflicts found. Resolve manually or use --dry-run to preview.", "warning")
        
        # Ejecutar hook post-deploy
        context = {
            'operation': 'deploy',
            'deployed': deployed,
            'conflicted': conflicted,
            'skipped': skipped,
            'failed': failed,
            'storage_dir': self.storage_dir,
            'config_file': self.config_file
        }
        self.run_hook("post-deploy", context=context, dry_run=dry_run)
        
        return failed == 0 and conflicted == 0
    
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
        
        # Validación crítica: el archivo en storage debe existir
        if not storage_path.exists():
            log(f"Storage file missing: {storage_path}", "error")
            log(f"Cannot edit '{file_path.name}' - storage file not found", "error")
            log(f"Try running 'doti doctor' to diagnose issues", "info")
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
        Verifica el estado de todos los symlinks gestionados usando validación robusta
        
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
        storage_missing = 0
        symlink_missing = 0
        wrong_target = 0
        not_symlink = 0
        
        for original_path, data in config.items():
            original_path = Path(original_path)
            storage_path = Path(data["storage_path"])
            
            print(f"\n{original_path}")
            print(f"  → {storage_path}")
            
            # Verificar archivo en storage
            if not storage_path.exists():
                log("Storage file missing", "error")
                storage_missing += 1
                continue
            
            # Verificar symlink
            if not original_path.exists():
                log("Symlink missing", "error")
                symlink_missing += 1
            elif not original_path.is_symlink():
                log("Not a symlink (real file)", "warning")
                not_symlink += 1
            else:
                # Validación robusta del symlink usando readlink()
                try:
                    # Obtener el target declarado del symlink
                    declared_target = original_path.readlink()
                    
                    # Normalizar ambas rutas para comparación
                    # Usar resolve() solo en el storage_path (que debe existir)
                    normalized_storage = storage_path.resolve()
                    
                    # Normalizar el target del symlink de forma segura
                    if declared_target.is_absolute():
                        normalized_target = declared_target.resolve()
                    else:
                        # Target relativo - resolver contra el directorio del symlink
                        normalized_target = (original_path.parent / declared_target).resolve()
                    
                    if normalized_target == normalized_storage:
                        log("Healthy symlink", "success")
                        healthy += 1
                    else:
                        log(f"Symlink points to wrong target", "error")
                        log(f"  Declared: {declared_target}", "info")
                        log(f"  Expected: {storage_path}", "info")
                        wrong_target += 1
                        
                except (OSError, RuntimeError) as e:
                    log(f"Broken symlink (cannot read target): {e}", "error")
                    symlink_missing += 1
        
        # Resumen mejorado
        print("\nDoctor Summary:")
        log(f"Healthy symlinks: {healthy}", "success")
        
        issues = 0
        
        if storage_missing > 0:
            log(f"Storage files missing: {storage_missing}", "error")
            issues += storage_missing
            
        if symlink_missing > 0:
            log(f"Symlinks missing: {symlink_missing}", "error")
            issues += symlink_missing
            
        if wrong_target > 0:
            log(f"Wrong target symlinks: {wrong_target}", "error")
            issues += wrong_target
            
        if not_symlink > 0:
            log(f"Real files (not symlinks): {not_symlink}", "warning")
            issues += not_symlink
        
        if issues == 0:
            log("All symlinks are healthy!", "success")
            return True
        else:
            # Sugerencias específicas basadas en los problemas encontrados
            suggestions = []
            
            if storage_missing > 0:
                suggestions.append(f"restore {storage_missing} files from backup")
                
            if symlink_missing > 0 or wrong_target > 0:
                total_broken = symlink_missing + wrong_target
                suggestions.append(f"run 'doti deploy' to fix {total_broken} symlinks")
                
            if not_symlink > 0:
                suggestions.append(f"remove {not_symlink} real files blocking symlinks")
            
            log(f"Found {issues} issue(s). Suggested commands: {', '.join(suggestions)}.", "warning")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="doti - Gestor de dotfiles",
        prog="doti"
    )
    
    # Argumento global --dry-run
    parser.add_argument("--dry-run", action="store_true", 
                       help="Simulate operations without making changes")
    
    # Argumento global --hooks-strict
    parser.add_argument("--hooks-strict", action="store_true", 
                       help="Stop execution if pre-hooks fail")
    
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
    
    # Comando help explícito (estilo git)
    help_parser = subparsers.add_parser("help", help="Muestra ayuda sobre comandos")
    help_parser.add_argument("command", nargs="?", help="Comando específico para mostrar ayuda")
    
    args = parser.parse_args()
    
    # Manejar comando help explícito
    if args.command == "help":
        if hasattr(args, 'command') and args.command:
            # Mostrar ayuda de un comando específico
            try:
                if args.command == 'init':
                    subparsers.choices['init'].print_help()
                elif args.command == 'add':
                    subparsers.choices['add'].print_help()
                elif args.command == 'deploy':
                    subparsers.choices['deploy'].print_help()
                elif args.command == 'list':
                    subparsers.choices['list'].print_help()
                elif args.command == 'unlink':
                    subparsers.choices['unlink'].print_help()
                elif args.command == 'edit':
                    subparsers.choices['edit'].print_help()
                elif args.command == 'doctor':
                    subparsers.choices['doctor'].print_help()
                elif args.command == 'help':
                    subparsers.choices['help'].print_help()
                else:
                    print(f"Comando '{args.command}' no encontrado")
                    parser.print_help()
            except (KeyError, AttributeError):
                parser.print_help()
        else:
            # Mostrar ayuda general
            parser.print_help()
        sys.exit(0)
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Advertencia de Dry Run si está activo
    if args.dry_run:
        log("Dry run mode enabled. No changes will be made.", "warning")
    
    # Advertencia de Hooks Strict si está activo
    if args.hooks_strict:
        log("Hooks strict mode enabled. Pre-hook failures will stop execution.", "warning")
    
    doti = Doti()
    
    if args.command == "init":
        success = doti.init(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    elif args.command == "add":
        success = doti.add(args.file_path, dry_run=args.dry_run, strict_mode=args.hooks_strict)
        sys.exit(0 if success else 1)
    elif args.command == "deploy":
        success = doti.deploy(dry_run=args.dry_run, strict_mode=args.hooks_strict)
        sys.exit(0 if success else 1)
    elif args.command == "list":
        doti.list()
    elif args.command == "unlink":
        restore = not args.no_restore
        success = doti.unlink(args.file_path, restore=restore, dry_run=args.dry_run, strict_mode=args.hooks_strict)
        sys.exit(0 if success else 1)
    elif args.command == "edit":
        success = doti.edit(args.file_path)
        sys.exit(0 if success else 1)
    elif args.command == "doctor":
        success = doti.doctor()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
