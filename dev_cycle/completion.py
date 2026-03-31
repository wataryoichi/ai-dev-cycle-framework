"""Shell completion scripts for devcycle CLI."""

from __future__ import annotations

SUBCOMMANDS = [
    "run", "resume", "status",
    "start", "prepare", "review-loop", "followup", "next", "check", "finalize",
    "handoff", "import-review", "finalize-review",
    "index", "latest", "mark-phase", "setup-hooks", "append-history", "doctor",
    "completion",
    # Long aliases
    "start-cycle", "prepare-review", "run-review-loop", "generate-followup",
    "next-step", "check-cycle", "finalize-cycle", "review-handoff",
    "show-index", "latest-cycle",
]

GLOBAL_OPTS = ["--help", "--version", "--project-root", "--json"]


def bash_completion() -> str:
    cmds = " ".join(SUBCOMMANDS)
    return f'''\
_devcycle() {{
    local cur prev cmds
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    cmds="{cmds}"

    if [[ ${{COMP_CWORD}} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${{cmds}} --help --version" -- "${{cur}}") )
        return 0
    fi

    case "${{prev}}" in
        --from-file)
            COMPREPLY=( $(compgen -f -- "${{cur}}") )
            return 0
            ;;
        --cycle-dir)
            COMPREPLY=( $(compgen -d -- "${{cur}}") )
            return 0
            ;;
        --phase)
            COMPREPLY=( $(compgen -W "started implementation_done review_pending review_imported review_done followup_done completed" -- "${{cur}}") )
            return 0
            ;;
        --format)
            COMPREPLY=( $(compgen -W "jsonl markdown" -- "${{cur}}") )
            return 0
            ;;
    esac

    COMPREPLY=( $(compgen -W "--help --json --cycle-dir --strict --from-file --text --version --generate-followup --live --detailed --format --verbose" -- "${{cur}}") )
    return 0
}}
complete -F _devcycle devcycle
'''


def zsh_completion() -> str:
    cmds_lines = "\n".join(f"        '{c}:{c} command'" for c in SUBCOMMANDS if not c.startswith("start-"))
    return f'''\
#compdef devcycle

_devcycle() {{
    local -a commands
    commands=(
{cmds_lines}
    )

    _arguments -C \\
        '--help[Show help]' \\
        '--version[Show version]' \\
        '--project-root[Project root directory]:directory:_directories' \\
        '1:command:->command' \\
        '*::arg:->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            _arguments \\
                '--help[Show help]' \\
                '--json[Output as JSON]' \\
                '--cycle-dir[Cycle directory]:directory:_directories' \\
                '--strict[Fail if quality issues exist]' \\
                '--from-file[Read from file]:file:_files' \\
                '--text[Text argument]' \\
                '--generate-followup[Generate followup draft]' \\
                '--live[Scan cycle dirs]' \\
                '--detailed[Show full details]' \\
                '--format[Output format]:format:(jsonl markdown)' \\
                '--verbose[Show details]' \\
                '--phase[Phase]:phase:(started implementation_done review_pending review_imported review_done followup_done completed)'
            ;;
    esac
}}

_devcycle
'''
