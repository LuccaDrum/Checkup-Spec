"""Base class for actions that modify the system.

Every action goes through the same flow: describe, warn, confirm, run.
The flow lives here once (template method); subclasses only fill in the steps.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

from pc_checkup.messages import get_message
from pc_checkup.models import Level, Line

logger = logging.getLogger(__name__)

Show = Callable[[str, Level], None]
Confirm = Callable[[str], bool]


class ActionError(Exception):
    """The action could not be completed. `key` is the message shown to the user."""

    def __init__(self, key: str = "action.failed") -> None:
        super().__init__(key)
        self.key = key


class Action(ABC):
    @abstractmethod
    def describe(self, language: str) -> str: ...

    @abstractmethod
    def warning(self, language: str) -> str: ...

    @abstractmethod
    def run(self, language: str) -> list[Line]:
        """Do the work and return the lines to show. Raise ActionError on failure."""

    def execute(self, language: str, show: Show, confirm: Confirm) -> bool:
        """Describe, warn, ask for confirmation, then run. Returns True if it ran."""
        show(self.describe(language), Level.LOG)
        show(self.warning(language), Level.LOG)
        if not confirm(get_message("action.confirm", language)):
            show(get_message("action.cancelled", language), Level.LOG)
            return False
        try:
            lines = self.run(language)
        except ActionError as error:
            logger.exception("Action %s failed", type(self).__name__)
            show(get_message(error.key, language), Level.ERROR)
            return False
        for line in lines:
            show(line.text, line.level)
        return True
