import config


def lister_options_publiques() -> list[dict]:
    options = []

    for option in config.OPTIONS_DE_CLARIFICATION:
        option_publique = {"id": option["id"], "libelle": option["libelle"]}

        if "style" in option:
            option_publique["style"] = option["style"]

        options.append(option_publique)

    return options


def trouver_option(id_option: str) -> dict | None:
    return next((option for option in config.OPTIONS_DE_CLARIFICATION if option["id"] == id_option), None)
