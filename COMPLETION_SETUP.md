# Configuración de Autocompletado para doti en Zsh

## Paso a paso para habilitar el autocompletado con TAB

### 1. Mover el archivo de completado a tu directorio personal

```bash
# Copiar el archivo a tu directorio home (opcional pero recomendado)
cp /path/to/doti/doti_completion.zsh ~/.doti_completion.zsh
```

### 2. Añadir la configuración a ~/.zshrc

Abre tu archivo `~/.zshrc` con tu editor preferido:

```bash
nano ~/.zshrc
```

Añade las siguientes líneas al final del archivo:

```zsh
# doti completion
if [[ -f ~/.doti_completion.zsh ]]; then
  source ~/.doti_completion.zsh
fi
```

### 3. Recargar la configuración de Zsh

```bash
# Recargar zshrc para aplicar cambios inmediatamente
source ~/.zshrc
```

O simplemente cierra y vuelve a abrir la terminal.

### 4. Verificar que funciona

Escribe en tu terminal:

```bash
doti <TAB>
```

Deberías ver los subcomandos disponibles:
- init
- add  
- deploy
- list
- unlink
- edit
- doctor
- help

También puedes probar:

```bash
doti --<TAB>
```

Para ver las opciones globales:
- --dry-run
- --hooks-strict
- --help
- -h

## Funcionalidades del autocompletado

### Completado de subcomandos
- `doti <TAB>` → Muestra todos los subcomandos disponibles
- Cada comando incluye una breve descripción

### Completado de archivos
- `doti add <TAB>` → Autocompleta rutas de archivos
- `doti unlink <TAB>` → Autocompleta rutas de archivos  
- `doti edit <TAB>` → Autocompleta rutas de archivos

### Opciones globales
- `doti --<TAB>` → Muestra --dry-run, --hooks-strict, --help, -h

## Solución de problemas

### Si no funciona después de recargar:

1. **Verifica que el archivo exista**:
   ```bash
   ls -la ~/.doti_completion.zsh
   ```

2. **Verifica que esté cargado**:
   ```bash
   echo $fpath
   ```

3. **Fuerza la recarga**:
   ```bash
   unfunction _doti 2>/dev/null
   autoload -U _doti
   ```

4. **Verifica la sintaxis del script**:
   ```bash
   zsh -n ~/.doti_completion.zsh
   ```

### Si usas Oh My Zsh:

El autocompletado debería funcionar sin problemas con Oh My Zsh. Si tienes conflictos, puedes añadir esta línea adicional en tu ~/.zshrc:

```zsh
# doti completion (para Oh My Zsh)
compdef _doti doti
```

## Características técnicas

- **Nativo Zsh**: Usa el sistema de completado nativo de Zsh (`compdef`)
- **Sin dependencias**: No requiere instalar paquetes adicionales
- **Contextual**: Ofrece diferentes opciones según el subcomando
- **Descripciones**: Muestra ayuda contextual para cada comando
