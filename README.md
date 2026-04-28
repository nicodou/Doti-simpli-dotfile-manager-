# doti

Una utilidad CLI minimalista en Python para gestionar dotfiles.

## Filosofía

- **Minimalista**: Usa únicamente la librería estándar de Python
- **Estilo Unix**: Comandos directos y predecibles
- **Sin dependencias**: Solo os, pathlib, json, argparse, subprocess

## Uso

```bash
python src/doti.py init                     # Inicializa doti
python src/doti.py add <file_path>          # Mueve archivo a storage y crea symlink
python src/doti.py deploy                   # Recrea todos los symlinks desde config
python src/doti.py list                     # Muestra archivos gestionados
python src/doti.py unlink <file_path>       # Elimina symlink y restaura archivo
python src/doti.py edit <file_path>         # Edita archivo gestionado
python src/doti.py doctor                   # Verifica estado de symlinks
```

## Estructura

```
~/.doti/
├── storage/     # Archivos originales
└── config.json  # Configuración de symlinks
```

## Comandos

- **init**: Crea la estructura de carpetas necesaria
- **add**: Agrega un archivo a doti (mueve a storage, crea symlink)
- **deploy**: Recrea todos los symlinks desde la configuración
- **list**: Muestra archivos gestionados con su estado
- **unlink**: Elimina symlink y opcionalmente restaura el archivo
- **edit**: Abre archivo gestionado en el editor predeterminado (EDITOR o nano)
- **doctor**: Verifica el estado de todos los symlinks
