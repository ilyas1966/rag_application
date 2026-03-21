from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request
import os
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from controllers import DataController
from controllers import ProjectController
from models import ResponseSignal
from models.ProjectModel import ProjectModel
import aiofiles
import logging
from .schemes.data import ProcessRequest
from controllers import ProcessController
from models.db_schemes import DataChunk
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.db_schemes import Asset
from bson.objectid import ObjectId
from models.enums.AssetTypeEnums import AssetTypeEnum
logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(prefix="/api/v1/data", tags=['data'])
@data_router.post("/upload/{project_id}")
async def upload_data(request: Request, project_id : str, file : UploadFile, 
                      app_settings : Settings=Depends(get_settings)):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    is_valid, signal = DataController().validate_uploaded_file(file=file)
    if not is_valid:
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content = {"signal" : signal}
        )
    project_dir = ProjectController().get_project_path(project_id=project_id)

    file_path, file_id = DataController().generate_file_path(original_filename=file.filename, project_id=project_id)
    try:

        async with aiofiles.open(file_path,'wb') as f :
            while chunk := await file.read(app_settings.FILE_CHUNK_SIZE):
                await f.write(chunk)

    except Exception as e:
        logger.error(f"error while uploading file : {e}")
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content = {'signal': ResponseSignal.FILE_UPLOAD_FAILURE.value }
        )
        
    
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)

    asset_ressource = Asset(asset_project_id=project.id, asset_name=file_id, asset_type=AssetTypeEnum.File.value, asset_size=os.path.getsize(file_path))

    asset_record = await asset_model.create_asset(asset=asset_ressource)

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {'signal': ResponseSignal.FILE_UPLOAD_SUCCESS.value , 'file id': asset_record.id 
                   } )


@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id : str, process_request : ProcessRequest):

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)

    project = await project_model.get_project_or_create_one(project_id=project_id)

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)

    project_files_ids = {}
    if process_request.file_id:
        asset_record = await asset_model.get_asset_record(asset_project_id=project.id, asset_name=process_request.file_id)
        if asset_record is None:
            return JSONResponse(content={"signal": ResponseSignal.FILE_ID_ERROR.value}, status_code = status.HTTP_400_BAD_REQUEST)
        project_files_ids = {asset_record.id: asset_record.asset_name}
    else:
        asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
        project_files = await asset_model.get_all_project_asset(asset_project_id=project.id, asset_type=AssetTypeEnum.File.value)
        project_files_ids =  {record.id: record.asset_name for record in project_files}
    if len(project_files_ids) == 0:
        return JSONResponse(content={"signal": ResponseSignal.NO_FILES_ERROR.value}, status_code = status.HTTP_400_BAD_REQUEST)

    file_id = process_request.file_id

    chunk_size = process_request.chunk_size

    overlap_size = process_request.overlap_size

    do_reset = process_request.do_reset

    process_controller = ProcessController(project_id=project_id)

    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    if do_reset == 1:
            await chunk_model.delete_chunks_by_project_id(project_id=project.id)


    no_record = 0
    no_files = 0
    for asset_id, file_id in project_files_ids.items():
        file_content = process_controller.get_file_content(file_id=file_id)
        if file_content is None:
            logger.error(f"file content is none for file id : {file_id}")
            continue

        file_chunks = process_controller.process_file_content(file_id=file_id, file_content=file_content, chunk_size=chunk_size, overlap_size=overlap_size)

        if file_chunks is None or len(file_chunks)==0 :
            return JSONResponse(
                status_code = status.HTTP_400_BAD_REQUEST,
                content = {'signal': ResponseSignal.PROCESSING_FAILURE.value}
            )
        
        file_chunks_records = [DataChunk( 
        chunk_text = chunk.page_content,
        chunk_metadata = chunk.metadata,
        chunk_order = i+1,
        chunk_project_id=project.id,
        chunk_asset_id=asset_id
        ) for i, chunk in enumerate(file_chunks)]

        

        no_record += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
        no_files += 1

    return JSONResponse(
            content = {'signal': ResponseSignal.PROCESSING_SUCCESS.value, 
                       'inserted_chunks': no_record, 'files_processed': no_files}
        )



