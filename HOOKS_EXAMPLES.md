# Sistema de Hooks para doti

El sistema de hooks permite ejecutar scripts personalizados antes o después de comandos clave de doti.

## Estructura

Los hooks se guardan en: `~/.doti/hooks/`

### Hooks disponibles

#### Para el comando `add`:
- `pre-add.sh` - Se ejecuta antes de agregar un archivo
- `post-add.sh` - Se ejecuta después de agregar un archivo exitosamente

#### Para el comando `deploy`:
- `pre-deploy.sh` - Se ejecuta antes de desplegar symlinks
- `post-deploy.sh` - Se ejecuta después de desplegar symlinks

#### Para el comando `unlink`:
- `pre-unlink.sh` - Se ejecuta antes de eliminar un symlink
- `post-unlink.sh` - Se ejecuta después de eliminar un symlink

## Ejemplos de Hooks

### 1. Backup automático (pre-add.sh)

```bash
#!/bin/bash
# Backup automático de archivos antes de agregarlos a doti

FILE_PATH="$1"
BACKUP_DIR="$HOME/.doti/backups"

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

# Crear backup con timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/$(basename "$FILE_PATH")_$TIMESTAMP"

if [ -f "$FILE_PATH" ]; then
    cp "$FILE_PATH" "$BACKUP_FILE"
    echo "Backup creado: $BACKUP_FILE"
fi
```

### 2. Notificación después de deploy (post-deploy.sh)

```bash
#!/bin/bash
# Notificar cuando se completó el deploy

echo "==> doti deploy completado"
echo "Symlinks actualizados: $(find ~ -maxdepth 1 -type l -lname "*.doti*" | wc -l)"
```

### 3. Validación de archivos (pre-add.sh)

```bash
#!/bin/bash
# Validar que los archivos sean seguros antes de agregarlos

FILE_PATH="$1"

# Verificar que no sea un archivo binario ejecutable
if file "$FILE_PATH" | grep -q "executable"; then
    echo "Error: No se permiten archivos ejecutables"
    exit 1
fi

# Verificar tamaño máximo (1MB)
MAX_SIZE=$((1024 * 1024))  # 1MB en bytes
FILE_SIZE=$(stat -f%z "$FILE_PATH" 2>/dev/null || stat -c%s "$FILE_PATH" 2>/dev/null)

if [ "$FILE_SIZE" -gt "$MAX_SIZE" ]; then
    echo "Error: Archivo demasiado grande (máximo 1MB)"
    exit 1
fi
```

### 4. Sincronización con Git (post-add.sh)

```bash
#!/bin/bash
# Commitear cambios automáticamente después de agregar archivos

DOTI_DIR="$HOME/.doti"
cd "$DOTI_DIR"

# Verificar si es un repositorio git
if [ -d ".git" ]; then
    git add config.json
    git commit -m "doti: agregar nuevo archivo gestionado"
    echo "Cambios commiteados en repositorio git"
fi
```

### 5. Limpieza de symlinks rotos (pre-deploy.sh)

```bash
#!/bin/bash
# Limpiar symlinks rotos antes de deploy

echo "Limpiando symlinks rotos..."

# Encontrar y eliminar symlinks rotos en el home
find ~ -maxdepth 1 -type l ! -exec test -e {} \; -delete 2>/dev/null

echo "Limpieza completada"
```

## Instalación de Hooks

### 1. Crear el directorio de hooks
```bash
mkdir -p ~/.doti/hooks
```

### 2. Crear un script de hook
```bash
# Crear pre-add.sh
nano ~/.doti/hooks/pre-add.sh
```

### 3. Hacerlo ejecutable
```bash
chmod +x ~/.doti/hooks/pre-add.sh
```

## Variables de Entorno Disponibles

Los hooks pueden acceder a variables de entorno estándar como:
- `$HOME` - Directorio home del usuario
- `$EDITOR` - Editor predeterminado
- `$PATH` - Rutas de ejecutables

## Salida de los Hooks

- **stdout**: Se muestra como `==> [HOOK] Output: ...`
- **stderr**: Se muestra como `==> [HOOK] Error: ...`
- **Código de salida**: 
  - 0: Éxito `==> [HOOK] hook_name completed successfully`
  - !=0: Error `==> [HOOK] hook_name failed with exit code X`

## Seguridad

- Los hooks tienen un timeout de 30 segundos
- Los errores en los hooks no detienen la ejecución de doti
- Los hooks no ejecutables muestran una advertencia pero no fallan
- En modo `--dry-run`, los hooks solo se simulan

## Depuración

Para probar hooks:

```bash
# Probar hook específico
~/.doti/hooks/pre-add.sh

# Ver logs con doti
doti add ~/.bashrc  # Verás la salida del hook

# Probar en dry run
doti --dry-run add ~/.bashrc  # Verás [DRY RUN] Would execute hook
```

## Buenas Prácticas

1. **Manejo de errores**: Siempre verifica códigos de salida
2. **Idempotencia**: Los hooks deben poder ejecutarse múltiples veces
3. **Logs claros**: Usa echo para mensajes informativos
4. **Permisos**: Siempre haz los hooks ejecutables (`chmod +x`)
5. **Testing**: Prueba los hooks manualmente antes de usarlos

## Ejemplo Completo

```bash
# 1. Crear hook de backup
cat > ~/.doti/hooks/pre-add.sh << 'EOF'
#!/bin/bash
FILE_PATH="$1"
BACKUP_DIR="$HOME/.doti/backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/$(basename "$FILE_PATH")_$TIMESTAMP"
cp "$FILE_PATH" "$BACKUP_FILE" 2>/dev/null && echo "Backup: $BACKUP_FILE"
EOF

# 2. Hacerlo ejecutable
chmod +x ~/.doti/hooks/pre-add.sh

# 3. Probar
doti add ~/.vimrc
# Verás: ==> [HOOK] Executing pre-add...
#         ==> [HOOK] Output: Backup: ~/.doti/backups/vimrc_20240427_193000
```
