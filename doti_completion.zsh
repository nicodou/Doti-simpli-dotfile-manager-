#compdef doti

# doti completion script for Zsh
# Place this file in your completion directory and source it in ~/.zshrc

_doti() {
  local -a commands
  commands=(
    'init:Inicializa doti'
    'add:Agrega un archivo a doti'
    'deploy:Despliega todos los symlinks'
    'list:Lista archivos gestionados'
    'unlink:Elimina symlink y restaura archivo'
    'edit:Edita un archivo gestionado'
    'doctor:Verifica estado de los symlinks'
    'help:Muestra ayuda sobre comandos'
  )

  local -a global_options
  global_options=(
    '--dry-run:Simulate operations without making changes'
    '--hooks-strict:Stop execution if pre-hooks fail'
    '--help:Show help message'
    '-h:Show help message'
  )

  local curcontext="$curcontext" state line
  typeset -A opt_args

  _arguments -C \
    '1: :->command' \
    '*::arg:->args' \
    $global_options \
    && return 0

  case $state in
    command)
      _describe 'command' commands
      ;;
    args)
      case $line[1] in
        add)
          _files
          ;;
        unlink)
          _files
          ;;
        edit)
          _files
          ;;
        deploy|list|doctor|init|help)
          # No additional arguments needed for these commands
          ;;
      esac
      ;;
  esac
}

_doti "$@"
