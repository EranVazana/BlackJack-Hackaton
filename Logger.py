import logging
from colorama import init

# Input: none
# Output: none
# Description: Initializes colorama to auto-reset terminal colors.
init(autoreset=True)

INPUT_LEVEL = 25
logging.addLevelName(INPUT_LEVEL, "INPUT")

# Input: msg (str), *args, **kwargs
# Output: none
# Description: Adds a custom INPUT logging level for inline user prompts.
def _input(self, msg, *args, **kwargs):
    """logger.input("Prompt: ")"""
    if self.isEnabledFor(INPUT_LEVEL):
        self._log(INPUT_LEVEL, msg, args, **kwargs)

logging.Logger.input = _input


class ColoredFormatter(logging.Formatter):
    # Input: none
    # Output: formatted log string
    # Description: Formatter that adds color to log level names and messages.
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "INPUT": "\033[35m",    # Magenta
    }
    RESET = "\033[0m"

    # Input: record (logging.LogRecord)
    # Output: string
    # Description: Formats log records with ANSI color codes.
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)

        orig_levelname = record.levelname
        orig_msg = record.msg
        orig_args = record.args

        try:
            record.levelname = f"{color}{orig_levelname}{self.RESET}"

            message = record.getMessage()
            record.msg = f"{color}{message}{self.RESET}"
            record.args = ()  

            return super().format(record)
        finally:
            record.levelname = orig_levelname
            record.msg = orig_msg
            record.args = orig_args


class InputAwareStreamHandler(logging.StreamHandler):
    # Input: record (logging.LogRecord)
    # Output: none
    # Description: Writes INPUT logs without a newline, others with newline.
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)

            if record.levelno == INPUT_LEVEL:
                self.stream.write(msg)
            else:
                self.stream.write(msg + self.terminator)

            self.flush()
        except Exception:
            self.handleError(record)


_logger = None 


# Input: name (str), level (int)
# Output: logging.Logger
# Description: Creates or returns a singleton colored logger instance.
def get_logger(name: str = "app", level: int = logging.INFO) -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  

    if not logger.handlers:
        handler = InputAwareStreamHandler()
        handler.setFormatter(
            ColoredFormatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)

    _logger = logger
    return logger


# Input: none
# Output: none
# Description: Demo usage of the custom colored logger.
if __name__ == "__main__":
    log = get_logger(level=logging.DEBUG)

    log.info("Starting...")
    log.input("Enter your name: ")  # stays on same line
    name = input()
    log.info("Hello %s", name)
