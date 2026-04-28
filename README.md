# doti

`doti` es una utilidad CLI minimalista escrita en Python para gestionar tus archivos de configuración (dotfiles) de forma eficiente.

## Filosofía
- **Minimalista**: Construido usando únicamente la librería estándar de Python.
- **Sin dependencias**: No requiere instalación de paquetes externos.
- **Estilo Unix**: Comandos predecibles y directos.
- **Extensible**: Sistema de *hooks* para automatización personalizada.

## Instalación

1. Clona el repositorio o descarga los archivos del proyecto
2. Haz el wrapper ejecutable:
```bash
chmod +x doti
```
3. Asegúrate de tener Python 3 instalado en el sistema

## Estructura de directorios
```text
~/.doti/
├── storage/     # Archivos originales gestionados
├── hooks/       # Scripts personalizados (ver sección Hooks)
└── config.json  # Configuración y mapeo de symlinks
```

## Comandos

### init
```bash
./doti init
```
Crea la estructura de carpetas `~/.doti/storage`, `~/.doti/hooks` y el archivo `config.json`.

### add
```bash
./doti add <file_path>
```
Agrega un archivo a doti. Mueve el archivo a `~/.doti/storage/` y crea un symlink en la ubicación original.

### deploy
```bash
./doti deploy
```
Recrea todos los symlinks desde la configuración guardada en `config.json`.
- **Seguridad**: Solo recrea symlinks gestionados, nunca sobrescribe archivos reales
- **Detección de conflictos**: Muestra advertencias para archivos existentes
- **Resumen**: Reporta deployed, conflicted, skipped, failed

### list
```bash
./doti list
```
Muestra todos los archivos gestionados con su ruta original y su ubicación en storage.

### unlink
```bash
./doti unlink <file_path> [--no-restore]
```
Elimina el symlink y opcionalmente restaura el archivo a su ubicación original.
- `--no-restore`: No restaura el archivo desde storage.
- **Seguridad**: Solo opera sobre symlinks gestionados por doti
- **Validación**: Rechaza eliminar archivos reales o symlinks no gestionados

### edit
```bash
./doti edit <file_path>
```
Abre un archivo gestionado en el editor predeterminado (usa la variable `EDITOR` o `nano` por defecto).

### doctor
```bash
./doti doctor
```
Verifica el estado de todos los symlinks gestionados. Detecta symlinks rotos, archivos faltantes en storage y enlaces incorrectos.

### help
```bash
./doti help [comando]
```
Muestra ayuda sobre comandos. Opcionalmente muestra ayuda específica de un comando.

## Opción Global: Dry Run

Todos los comandos que modifican el sistema de archivos soportan el modo `--dry-run`:

```bash
./doti --dry-run add ~/.bashrc
./doti --dry-run deploy
./doti --dry-run unlink ~/.vimrc
```

El modo `--dry-run` simula las operaciones sin realizar cambios reales, mostrando exactamente lo que haría doti.

## Opción Global: Hooks Strict

Controla el comportamiento cuando los hooks fallan:

```bash
./doti --hooks-strict add ~/.bashrc
./doti --hooks-strict deploy
./doti --hooks-strict unlink ~/.vimrc
```

- **Modo normal**: Los hooks fallidos muestran advertencias pero no detienen la ejecución
- **Modo strict**: Los hooks `pre-*` que fallan detienen el comando completamente

## Sistema de Hooks

El sistema de hooks permite ejecutar scripts personalizados antes y después de comandos clave.

### Estructura
Los hooks se guardan en `~/.doti/hooks/` con la nomenclatura:
- `pre-<comando>.sh` - Se ejecuta antes del comando
- `post-<comando>.sh` - Se ejecuta después del comando

### Hooks Disponibles
- `pre-add.sh` / `post-add.sh`
- `pre-deploy.sh` / `post-deploy.sh`
- `pre-unlink.sh` / `post-unlink.sh`

### Ejemplo de Hook
```bash
#!/bin/bash
# ~/.doti/hooks/pre-add.sh
echo "A punto de agregar archivo a doti..."
```

```bash
chmod +x ~/.doti/hooks/pre-add.sh
```

Los hooks reciben logs claros y no detienen la ejecución de doti si fallan.

## Autocompletado (Zsh)

Para habilitar el autocompletado con TAB en Zsh:

1. Copia el script de completado:
```bash
cp doti_completion.zsh ~/.doti_completion.zsh
```

2. Añade a tu `~/.zshrc`:
```zsh
if [[ -f ~/.doti_completion.zsh ]]; then
  source ~/.doti_completion.zsh
fi
```

3. Recarga la configuración:
```bash
source ~/.zshrc
```

Ahora puedes usar `doti <TAB>` para autocompletar comandos y `doti add <TAB>` para autocompletar archivos.

## Requisitos Técnicos

- **Python 3+**: Requiere Python 3 instalado en el sistema
- **Sistema operativo**: Compatible con macOS, Linux y otros sistemas Unix-like
- **Permisos**: Requiere permisos de lectura/escritura en el directorio home
- **Symlinks**: Requiere capacidad para crear enlaces simbólicos (ver limitaciones Windows)

## Limitaciones de Windows

**Symlinks en Windows**: La creación de symlinks en Windows requiere:
- **Permisos de administrador** o
- **Modo Desarrollador** activado en Windows 10/11

**Síntomas si no tienes permisos**:
```
Error: Failed to create symlink: [WinError 1314]
A required privilege is not held by the client
```

**Soluciones**:
1. **Ejecutar como Administrador**: Abre PowerShell/CMD como administrador
2. **Activar Modo Desarrollador**: Configuración > Actualización y seguridad > Para desarrolladores > Modo desarrollador
3. **Usar Git Bash**: Git Bash puede crear symlinks sin permisos elevados

**Comprobación de permisos**:
```powershell
# En PowerShell (como administrador)
New-Item -ItemType SymbolicLink -Path "test-link" -Target "target-file"
```

Si no puedes obtener permisos de administrador, considera usar alternativas como:
- **Hard links** (limitados al mismo volumen)
- **Copias de archivos** (sin symlinks)
- **WSL** (Windows Subsystem for Linux)

## Flujo de Trabajo Típico

1. **Inicialización**:
```bash
./doti init
```

2. **Agregar archivos**:
```bash
./doti add ~/.bashrc
./doti add ~/.vimrc
./doti add ~/.gitconfig
```

3. **Verificar estado**:
```bash
./doti doctor
./doti list
```

4. **Despliegue en nuevas máquinas**:
```bash
./doti deploy
```

## Características Avanzadas

- **Manejo de conflictos**: Si un archivo con el mismo nombre ya existe en storage, doti añade un sufijo numérico
- **Symlinks seguros**: Verifica que los symlinks apunten a los archivos correctos en storage
- **Protección de archivos**: `deploy` y `unlink` solo operan sobre symlinks gestionados, nunca borran archivos reales
- **Recuperación**: El comando `unlink` puede restaurar archivos a su ubicación original
- **Validación robusta**: El comando `doctor` detecta problemas comunes con diagnóstico preciso
- **Detección de conflictos**: `deploy` muestra advertencias claras cuando encuentra archivos reales o symlinks no gestionados
- **Sistema de hooks**: Automatización personalizada con variables de entorno y argumentos
- **Modo estricto**: Control granular sobre el comportamiento de hooks fallidos

## Licencia

MIT License - Libre para usar y modificar.

## Uso Global

Para ejecutar `doti` desde cualquier ubicación sin necesidad del prefijo `./`, añade el directorio del proyecto a tu PATH:

### Para Zsh (macOS por defecto)
Añade a tu `~/.zshrc`:
```zsh
export PATH="/path/to/doti:$PATH"
```

### Para Bash
Añade a tu `~/.bashrc`:
```bash
export PATH="/path/to/doti:$PATH"
```

Recarga tu configuración:
```bash
source ~/.zshrc  # o source ~/.bashrc
```

Ahora podrás ejecutar:
```bash
doti init
doti add ~/.bashrc
doti --help
```
