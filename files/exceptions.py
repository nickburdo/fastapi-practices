class UploadValidationError(Exception):
    """The upload request is rejected as a whole."""


class TooManyFilesError(UploadValidationError):
    def __init__(self, max_count: int) -> None:
        super().__init__(f"Too many files: at most {max_count} per request")
        self.max_count = max_count


class FileNameTooLongError(UploadValidationError):
    def __init__(self, max_length: int) -> None:
        super().__init__(f"File name is longer than {max_length} characters")
        self.max_length = max_length


class UnsupportedFileTypeError(UploadValidationError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"File '{filename}' has an unsupported type")
        self.filename = filename


class EmptyFileError(UploadValidationError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"File '{filename}' is empty")
        self.filename = filename


class FileTooLargeError(UploadValidationError):
    def __init__(self, filename: str, max_size: int) -> None:
        super().__init__(f"File '{filename}' is larger than {max_size} bytes")
        self.filename = filename
        self.max_size = max_size


class StoredFileNotFoundError(Exception):
    def __init__(self, file_id: int) -> None:
        super().__init__(f"File {file_id} not found")
        self.file_id = file_id
