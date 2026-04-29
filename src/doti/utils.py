"""
Utilidades auxiliares para doti

Este módulo contiene funciones de utilidad compartidas usadas por el paquete doti.
"""

import sys


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
