from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.auth import get_current_user, User
from app.rox_quant.sync_manager import SyncManager
import os

router = APIRouter(prefix="/sync", tags=["Sync"])
sync_manager = SyncManager()

@router.get("/backup", response_class=FileResponse)
async def create_backup(current_user: User = Depends(get_current_user)):
    """
    Generate and download a full system backup zip.
    """
    try:
        zip_path = sync_manager.create_backup_zip(current_user.id)
        filename = os.path.basename(zip_path)
        return FileResponse(path=zip_path, filename=filename, media_type='application/zip')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

@router.post("/restore")
async def restore_backup(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """
    Upload and restore a backup zip.
    """
    try:
        # Save temp upload
        temp_path = os.path.join(SyncManager.TEMP_DIR, f"upload_{file.filename}")
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        success = sync_manager.restore_backup(temp_path, current_user.id)
        
        # Cleanup upload
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if success:
            return {"status": "ok", "message": "Restore completed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Restore process failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
