from fastapi import HTTPException
from fastapi.responses import FileResponse
from pathlib import Path as pathlib_Path

async def get_hist_dumps(namespace):
    path = pathlib_Path(f"/app/downloads/{namespace}")

    try:
        if not path.exists():
                raise HTTPException(status_code=404, detail="No dumps for this namespace")
        
        files = [f.name for f in path.iterdir() if f.is_file()]
        return files
    
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="There no dumps for this namespace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")    

async def get_download_dump(namespace, file_name):
    return FileResponse(f"/app/downloads/{namespace}/{file_name}", media_type="application/octet-stream", filename = file_name)