class QzoneError(RuntimeError):
    """HTTP OK, but Qzone returns an error code.
    """
    msg = 'unknown'

    def __init__(self, code: int, *args):
        self.code = int(code)
        if len(args) > 0 and isinstance(args[0], str):
            self.msg = args[0]
        RuntimeError.__init__(self, *args)

    def __str__(self) -> str:
        return f"Code {self.code}: {self.msg}"


class LoginError(RuntimeError):
    def __init__(self, msg: str, strategy: str = None) -> None:
        msg = "登陆失败: " + msg
        super().__init__(msg, strategy)
        self.msg = msg
        self.strategy = strategy
