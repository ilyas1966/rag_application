from controllers.BaseController import BaseController
from fastapi import UploadFile
from models import ResponseSignal
from .ProjectController import ProjectController
import re
import os
class DataController(BaseController):
    def __init__(self):
        super().__init__()
    
    def validate_uploaded_file(self, file : UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPE:
            return False, ResponseSignal.FILE_TYPE_NOT_ALLOWED.value
        if file.size > self.app_settings.FILE_MAX_SIZE:
            return False, ResponseSignal.FILE_SIZE_EXCEEDS_LIMIT.value
        return True, ResponseSignal.FILE_VALID.value     

    def generate_file_path(self, original_filename:str, project_id:str):
        random_name = self.random_string()
        project_path = ProjectController().get_project_path(project_id=project_id)
        cleaned_file_name = self.clean_file_name(original_filename=original_filename)
        new_file_path = os.path.join(project_path, random_name + "_" + cleaned_file_name)

        while os.path.exists(new_file_path):
            random_name = self.random_string()
            new_file_path = os.path.join(project_path, random_name + "_" + cleaned_file_name)

        return new_file_path, random_name + "_" + cleaned_file_name




    def clean_file_name(self, original_filename:str):
        cleaned_file_name = re.sub(r'[^\w.]', '', original_filename.strip())
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name