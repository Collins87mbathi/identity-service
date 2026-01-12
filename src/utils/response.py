from fastapi import Response
from datetime import datetime
from typing import Any, Optional
import uuid


class APIResponse:
    @staticmethod
    def success(data: Any = None, 
                user_message: str = "Success", 
                developer_message: str = "Request processed successfully", 
                status_code: int = 200, 
                request_ref_id: Optional[str] = None):
        return {
            "header": {
                "requestRefId": request_ref_id or str(uuid.uuid4()),
                "responseCode": status_code,
                "responseMessage": developer_message,
                "customerMessage": user_message,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "body": data
        }
    
    @staticmethod
    def error(
        user_message: str = "An error occurred",
        developer_message: str = "Internal server error",
        status_code: int = 500,
        request_ref_id: Optional[str] = None,
        data: Any = None
    ):
        return {
            "header": {
                "requestRefId": request_ref_id or str(uuid.uuid4()),
                "responseCode": status_code,
                "responseMessage": developer_message,
                "customerMessage": user_message,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "body": data
        }