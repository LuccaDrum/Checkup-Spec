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
        "ssd.working": "Reading disk information...",
        "ssd.read_failed": (
            "Could not read the disk information. Please try again; "
            "if it keeps failing, ask for technical help."
        ),
        "ssd.none": "No physical disks were found.",
        "ssd.disk": "Disk {id}: {name} ({media}, {size} GB, {bus})",
        "ssd.health.Healthy": "Windows reports this disk as healthy.",
        "ssd.health.Warning": "Windows reports a warning for this disk. Back up your files soon.",
        "ssd.health.Unhealthy": (
            "Windows reports this disk as unhealthy. Back up your files now and get technical help."
        ),
        "ssd.health.unknown": "Windows could not determine the health of this disk.",
        "ssd.wear": "About {life}% of the drive's life remains.",
        "ssd.wear.aging": (
            "About {life}% of the drive's life remains. It is aging; keep your backups up to date."
        ),
        "ssd.wear.critical": (
            "Only about {life}% of the drive's life remains. Replace it soon and back up your files now."
        ),
        "ssd.temperature": "Temperature: {value} °C.",
        "ssd.temperature.hot": "Temperature: {value} °C, which is high. Check ventilation and dust.",
        "ssd.hours": "Powered on for about {hours} hours ({days} days).",
        "ssd.errors.none": "No uncorrected read or write errors.",
        "ssd.errors.found": (
            "The drive reported {count} read or write errors that could not be corrected. "
            "Back up your files now."
        ),
        "ssd.unreadable": (
            "Could not read: {fields}. Some drives, especially behind a RAID controller, "
            "do not share this information with Windows."
        ),
        "ssd.field.wear": "wear",
        "ssd.field.temperature": "temperature",
        "ssd.field.power_on_hours": "hours of use",
        "ssd.field.read_errors": "read errors",
        "ssd.field.write_errors": "write errors",
        "ssd.verdict.ok": "Result: the disk looks fine.",
        "ssd.verdict.limited": (
            "Result: Windows reports the disk as healthy, but without detailed data this check is limited."
        ),
        "ssd.verdict.warning": "Result: worth keeping an eye on. Keep your backups up to date.",
        "ssd.verdict.attention": (
            "Result: the disk needs attention. Back up your files and get technical help."
        ),
        "menu.goodbye": "Goodbye!",
        "settings.language_changed": "Language changed to English.",
        "admin.declined": (
            "PC Checkup needs administrator rights to read system logs and run repairs. "
            "Please run it again and accept the Windows permission prompt."
        ),
        "app.press_enter": "Press Enter to close this window...",
        "bsod.working": "Reading the Windows event log, this may take a few seconds...",
        "bsod.read_failed": (
            "Could not read the Windows event log. Please try again; "
            "if it keeps failing, ask for technical help."
        ),
        "bsod.none": "Good news: no blue screens or unexpected shutdowns in the last {days} days.",
        "bsod.crashes.one": "Your PC crashed once in the last {days} days.",
        "bsod.crashes.many": "Your PC crashed {count} times in the last {days} days.",
        "bsod.crash_line": "- {when}: {explanation}",
        "bsod.shutdowns.one": (
            "There was 1 unexpected shutdown without a crash code "
            "(for example a power cut or holding the power button)."
        ),
        "bsod.shutdowns.many": (
            "There were {count} unexpected shutdowns without a crash code "
            "(for example power cuts or holding the power button)."
        ),
        "bsod.hardware.one": (
            "Windows logged 1 hardware error report (WHEA). "
            "It can point to a problem with the RAM or the processor."
        ),
        "bsod.hardware.many": (
            "Windows logged {count} hardware error reports (WHEA). "
            "They can point to a problem with the RAM or the processor."
        ),
        "bsod.hint.memory": (
            "Some of these problems are linked to memory. "
            "Running the RAM test (option 4) is a good next step."
        ),
        "bsod.verdict.ok": "Result: nothing to worry about.",
        "bsod.verdict.warning": "Result: worth keeping an eye on. If it happens again, ask for technical help.",
        "bsod.verdict.attention": (
            "Result: your PC crashes often. Please get technical help soon and back up your files."
        ),
        "bsod.technical_title": "Technical details:",
        "bsod.technical_event": "{time}  {kind}  id={event_id}  code={code}",
        "bsod.technical_dump": "Dump file: {path}",
        "bsod.technical_no_dumps": "No recent dump files found.",
        "bugcheck.unknown": (
            "Windows reported error code {code}, which is not in our list of common causes. "
            "A driver or hardware problem is possible."
        ),
        "bugcheck.MEMORY_MANAGEMENT": (
            "Memory management error. Often caused by faulty RAM or a problematic driver."
        ),
        "bugcheck.IRQL_NOT_LESS_OR_EQUAL": (
            "A driver or program touched memory it should not have. Usually a driver problem."
        ),
        "bugcheck.PAGE_FAULT_IN_NONPAGED_AREA": (
            "Windows tried to use memory that was not available. "
            "Can come from faulty RAM, a driver or a disk problem."
        ),
        "bugcheck.WHEA_UNCORRECTABLE_ERROR": (
            "The hardware reported an error it could not fix. "
            "Can point to the processor, the RAM or the motherboard."
        ),
        "bugcheck.KERNEL_DATA_INPAGE_ERROR": (
            "Windows could not load data from the disk into memory. "
            "Can be a failing drive, a loose cable or faulty RAM."
        ),
        "bugcheck.SYSTEM_SERVICE_EXCEPTION": (
            "A system service failed unexpectedly. Usually a driver or software problem."
        ),
        "bugcheck.DRIVER_IRQL_NOT_LESS_OR_EQUAL": (
            "A driver used memory the wrong way. Usually a faulty or outdated driver."
        ),
        "bugcheck.SYSTEM_THREAD_EXCEPTION_NOT_HANDLED": (
            "A system component failed and Windows could not recover. Usually a driver problem."
        ),
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
        "ssd.working": "Lendo informações do disco...",
        "ssd.read_failed": (
            "Não foi possível ler as informações do disco. Tente novamente; "
            "se continuar falhando, peça ajuda técnica."
        ),
        "ssd.none": "Nenhum disco físico foi encontrado.",
        "ssd.disk": "Disco {id}: {name} ({media}, {size} GB, {bus})",
        "ssd.health.Healthy": "O Windows informa que este disco está saudável.",
        "ssd.health.Warning": (
            "O Windows informa um aviso para este disco. Faça backup dos seus arquivos em breve."
        ),
        "ssd.health.Unhealthy": (
            "O Windows informa que este disco não está saudável. "
            "Faça backup dos seus arquivos agora e peça ajuda técnica."
        ),
        "ssd.health.unknown": "O Windows não conseguiu determinar a saúde deste disco.",
        "ssd.wear": "Resta cerca de {life}% da vida útil do disco.",
        "ssd.wear.aging": (
            "Resta cerca de {life}% da vida útil do disco. Ele está envelhecendo; "
            "mantenha seus backups em dia."
        ),
        "ssd.wear.critical": (
            "Resta apenas cerca de {life}% da vida útil do disco. "
            "Troque-o em breve e faça backup dos seus arquivos agora."
        ),
        "ssd.temperature": "Temperatura: {value} °C.",
        "ssd.temperature.hot": (
            "Temperatura: {value} °C, o que é alto. Verifique a ventilação e a poeira."
        ),
        "ssd.hours": "Ligado há cerca de {hours} horas ({days} dias).",
        "ssd.errors.none": "Nenhum erro de leitura ou gravação sem correção.",
        "ssd.errors.found": (
            "O disco registrou {count} erros de leitura ou gravação que não puderam ser corrigidos. "
            "Faça backup dos seus arquivos agora."
        ),
        "ssd.unreadable": (
            "Não foi possível ler: {fields}. Alguns discos, principalmente atrás de um controlador "
            "RAID, não compartilham essa informação com o Windows."
        ),
        "ssd.field.wear": "desgaste",
        "ssd.field.temperature": "temperatura",
        "ssd.field.power_on_hours": "horas de uso",
        "ssd.field.read_errors": "erros de leitura",
        "ssd.field.write_errors": "erros de gravação",
        "ssd.verdict.ok": "Resultado: o disco parece estar bem.",
        "ssd.verdict.limited": (
            "Resultado: o Windows informa que o disco está saudável, "
            "mas sem dados detalhados esta verificação é limitada."
        ),
        "ssd.verdict.warning": (
            "Resultado: vale ficar de olho. Mantenha seus backups em dia."
        ),
        "ssd.verdict.attention": (
            "Resultado: o disco precisa de atenção. Faça backup dos seus arquivos "
            "e peça ajuda técnica."
        ),
        "menu.goodbye": "Até logo!",
        "settings.language_changed": "Idioma alterado para português.",
        "admin.declined": (
            "O PC Checkup precisa de direitos de administrador para ler os logs do sistema "
            "e executar reparos. Execute novamente e aceite o aviso de permissão do Windows."
        ),
        "app.press_enter": "Pressione Enter para fechar esta janela...",
        "bsod.working": "Lendo o registro de eventos do Windows, pode levar alguns segundos...",
        "bsod.read_failed": (
            "Não foi possível ler o registro de eventos do Windows. Tente novamente; "
            "se continuar falhando, peça ajuda técnica."
        ),
        "bsod.none": (
            "Boa notícia: nenhuma tela azul ou desligamento inesperado nos últimos {days} dias."
        ),
        "bsod.crashes.one": "Seu PC travou uma vez nos últimos {days} dias.",
        "bsod.crashes.many": "Seu PC travou {count} vezes nos últimos {days} dias.",
        "bsod.crash_line": "- {when}: {explanation}",
        "bsod.shutdowns.one": (
            "Houve 1 desligamento inesperado sem código de erro "
            "(por exemplo, falta de energia ou botão de ligar pressionado)."
        ),
        "bsod.shutdowns.many": (
            "Houve {count} desligamentos inesperados sem código de erro "
            "(por exemplo, falta de energia ou botão de ligar pressionado)."
        ),
        "bsod.hardware.one": (
            "O Windows registrou 1 relatório de erro de hardware (WHEA). "
            "Pode indicar problema na memória RAM ou no processador."
        ),
        "bsod.hardware.many": (
            "O Windows registrou {count} relatórios de erro de hardware (WHEA). "
            "Podem indicar problema na memória RAM ou no processador."
        ),
        "bsod.hint.memory": (
            "Alguns desses problemas estão ligados à memória. "
            "Executar o teste de RAM (opção 4) é um bom próximo passo."
        ),
        "bsod.verdict.ok": "Resultado: nada com que se preocupar.",
        "bsod.verdict.warning": (
            "Resultado: vale ficar de olho. Se acontecer de novo, peça ajuda técnica."
        ),
        "bsod.verdict.attention": (
            "Resultado: seu PC trava com frequência. Procure ajuda técnica em breve "
            "e faça backup dos seus arquivos."
        ),
        "bsod.technical_title": "Detalhes técnicos:",
        "bsod.technical_event": "{time}  {kind}  id={event_id}  código={code}",
        "bsod.technical_dump": "Arquivo de despejo: {path}",
        "bsod.technical_no_dumps": "Nenhum arquivo de despejo recente encontrado.",
        "bugcheck.unknown": (
            "O Windows informou o código de erro {code}, que não está na nossa lista de causas "
            "comuns. Pode ser problema de driver ou de hardware."
        ),
        "bugcheck.MEMORY_MANAGEMENT": (
            "Erro de gerenciamento de memória. Costuma vir de RAM defeituosa ou de um driver com problema."
        ),
        "bugcheck.IRQL_NOT_LESS_OR_EQUAL": (
            "Um driver ou programa mexeu em memória que não devia. Geralmente é problema de driver."
        ),
        "bugcheck.PAGE_FAULT_IN_NONPAGED_AREA": (
            "O Windows tentou usar memória que não estava disponível. "
            "Pode vir de RAM defeituosa, de um driver ou de problema no disco."
        ),
        "bugcheck.WHEA_UNCORRECTABLE_ERROR": (
            "O hardware informou um erro que não conseguiu corrigir. "
            "Pode apontar para o processador, a RAM ou a placa-mãe."
        ),
        "bugcheck.KERNEL_DATA_INPAGE_ERROR": (
            "O Windows não conseguiu carregar dados do disco para a memória. "
            "Pode ser disco com defeito, cabo solto ou RAM defeituosa."
        ),
        "bugcheck.SYSTEM_SERVICE_EXCEPTION": (
            "Um serviço do sistema falhou de forma inesperada. Geralmente é driver ou software."
        ),
        "bugcheck.DRIVER_IRQL_NOT_LESS_OR_EQUAL": (
            "Um driver usou a memória de forma errada. Geralmente é um driver defeituoso ou desatualizado."
        ),
        "bugcheck.SYSTEM_THREAD_EXCEPTION_NOT_HANDLED": (
            "Um componente do sistema falhou e o Windows não conseguiu se recuperar. "
            "Geralmente é problema de driver."
        ),
    },
}


def get_message(key: str, language: str = DEFAULT_LANGUAGE, **values: object) -> str:
    """Return the text for `key` in `language`, filling `{placeholders}` with `values`.

    Raises KeyError for an unknown language or key, so typos fail loudly
    instead of showing an empty line to the user.
    """
    text = MESSAGES[language][key]
    return text.format(**values)
