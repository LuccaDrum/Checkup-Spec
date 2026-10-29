"""All user-facing text, looked up by key and language.

No other module should contain text meant for the user. To add a message,
add the same key to every language in MESSAGES (a test enforces this).
"""

SUPPORTED_LANGUAGES = ("en", "pt")
DEFAULT_LANGUAGE = "en"

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "menu.title": "=== PC Checkup ===",
        "menu.full_check": "Run full check",
        "menu.bsod": "Blue screens (last 15 days)",
        "menu.ssd": "SSD health",
        "menu.ram": "RAM test",
        "menu.sfc": "Repair system files (SFC)",
        "menu.dism": "Repair Windows image (DISM)",
        "menu.settings": "Settings (language)",
        "menu.exit": "Exit",
        "menu.prompt": "Choose an option: ",
        "menu.invalid": "That is not a valid option. Please type a number from the menu.",
        "menu.not_available": "This option is not available yet.",
        "menu.goodbye": "Goodbye!",
        "settings.language_changed": "Language changed to English.",
    },
    "pt": {
        "menu.title": "=== PC Checkup ===",
        "menu.full_check": "Executar verificação completa",
        "menu.bsod": "Telas azuis (últimos 15 dias)",
        "menu.ssd": "Saúde do SSD",
        "menu.ram": "Teste de memória RAM",
        "menu.sfc": "Reparar arquivos do sistema (SFC)",
        "menu.dism": "Reparar imagem do Windows (DISM)",
        "menu.settings": "Configurações (idioma)",
        "menu.exit": "Sair",
        "menu.prompt": "Escolha uma opção: ",
        "menu.invalid": "Essa não é uma opção válida. Digite um número do menu.",
        "menu.not_available": "Esta opção ainda não está disponível.",
        "menu.goodbye": "Até logo!",
        "settings.language_changed": "Idioma alterado para português.",
    },
}


def get_message(key: str, language: str = DEFAULT_LANGUAGE, **values: object) -> str:
    """Return the text for `key` in `language`, filling `{placeholders}` with `values`.

    Raises KeyError for an unknown language or key, so typos fail loudly
    instead of showing an empty line to the user.
    """
    text = MESSAGES[language][key]
    return text.format(**values)
