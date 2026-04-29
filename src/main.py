#!/usr/bin/env python3
"""
Punto de entrada principal para doti CLI

Este módulo contiene la función main() y toda la configuración de argparse
para la interfaz de línea de comandos de doti.
"""

import sys
import argparse

from doti import Doti
from doti.utils import log


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
