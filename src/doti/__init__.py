"""
doti - Minimalista CLI utility para gestionar dotfiles

Este paquete proporciona una interfaz Python para gestionar archivos de configuración
mediante symlinks, con un enfoque minimalista y sin dependencias externas.
"""

from .core import Doti
from .utils import log

__version__ = "2.0.0"
__all__ = ["Doti", "log"]
