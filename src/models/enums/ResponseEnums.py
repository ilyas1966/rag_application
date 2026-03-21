from enum import Enum
class ResponseSignal(Enum):
    FILE_TYPE_NOT_ALLOWED = "File type not allowed"
    FILE_SIZE_EXCEEDS_LIMIT = "File size exceeds the limit"
    FILE_VALID = "File is valid"
    FILE_UPLOAD_SUCCESS = "File uploaded successfully"
    FILE_UPLOAD_FAILURE = "File upload failed"
    PROCESSING_SUCCESS = "File processed successfully"
    PROCESSING_FAILURE = "File processing failed"
    NO_FILES_ERROR = "No files found for the project"
    FILE_ID_ERROR = "No file found with this id"