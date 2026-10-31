class AppError(Exception):
    def __init__(self, message, status=409, code='INVALID_STATE'):
        self.message, self.status, self.code = message, status, code
        super().__init__(message)
