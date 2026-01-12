from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.auth import (
    UserRegister, UserLogin, VerifyOTP, ForgotPassword, 
    ResetPassword, TokenResponse, UserResponse, RefreshTokenRequest
)
from src.services.auth import AuthService
# from src.services.google_oauth import GoogleOAuthService, oauth
from src.utils.response import APIResponse
from src.dependencies.auth import get_current_user, get_current_verified_user
from src.models.user import User
from src.config import get_settings

settings = get_settings()

router = APIRouter(
    prefix="/api/v1/auth", 
    tags=["Authentication"] 
)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    try:
        user = await AuthService.register_user(db, user_data)
        
        return APIResponse.success(
            data={
                "user_id": user.id,
                "email": user.email,
                "message": "Registration successful. Please check your email for verification code."
            },
            user_message="Registration successful! Check your email.",
            developer_message="User registered successfully, verification email sent",
            status_code=status.HTTP_201_CREATED
        )
    except HTTPException as e:
        return APIResponse.error(
            user_message=e.detail,
            developer_message=e.detail,
            status_code=e.status_code
        )
    except Exception as e:
        return APIResponse.error(
            user_message="Registration failed. Please try again.",
            developer_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/verify-email")
async def verify_email(
    verification_data: VerifyOTP,
    db: Session = Depends(get_db)
):
    try:
        user = await AuthService.verify_email(
            db, 
            verification_data.email, 
            verification_data.otp_code
        )
        
        return APIResponse.success(
            data={"email": user.email, "is_verified": user.is_verified},
            user_message="Email verified successfully!",
            developer_message="Email verification completed"
        )
    except HTTPException as e:
        return APIResponse.error(
            user_message=e.detail,
            developer_message=e.detail,
            status_code=e.status_code
        )


@router.post("/resend-verification")
async def resend_verification(
    email: str,
    db: Session = Depends(get_db)
):
    try:
        result = await AuthService.resend_verification_otp(db, email)
        return APIResponse.success(
            data=result,
            user_message="Verification code sent!",
            developer_message="Verification OTP resent successfully"
        )
    except HTTPException as e:
        return APIResponse.error(
            user_message=e.detail,
            developer_message=e.detail,
            status_code=e.status_code
        )


@router.post("/login")
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    try:
        result = AuthService.login_user(db, login_data)
        
        return APIResponse.success(
            data={
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "bearer",
                "user": {
                    "id": result["user"].id,
                    "email": result["user"].email,
                    "full_name": result["user"].full_name,
                    "is_verified": result["user"].is_verified
                }
            },
            user_message="Login successful!",
            developer_message="User authenticated successfully"
        )
    except HTTPException as e:
        return APIResponse.error(
            user_message=e.detail,
            developer_message=e.detail,
            status_code=e.status_code
        )


@router.post("/refresh-token")
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    try:
        result = AuthService.refresh_access_token(db, token_data.refresh_token)
        
        return APIResponse.success(
            data=result,
            user_message="Token refreshed successfully",
            developer_message="Access token regenerated"
        )
    except HTTPException as e:
        return APIResponse.error(
            user_message=e.detail,
            developer_message=e.detail,
            status_code=e.status_code
        )


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPassword,
    db: Session = Depends(get_db)
):
    try:
        result = await AuthService.forgot_password(db, data.email)
        
        return APIResponse.success(
            data=result,
            user_message="If your email is registered, you'll receive a reset code.",
            developer_message="Password reset OTP sent if email exists"
        )
    except Exception as e:
        return APIResponse.success(
            data={"message": "If the email exists, a reset code has been sent"},
            user_message="If your email is registered, you'll receive a reset code.",
            developer_message="Password reset request processed"
        )


@router.post("/reset-password")
async def reset_password(
    reset_data: ResetPassword,
    db: Session = Depends(get_db)
):
    try:
        user = await AuthService.reset_password(
            db,
            reset_data.email,
            reset_data.otp_code,
            reset_data.new_password
        )
        
        return APIResponse.success(
            data={"email": user.email},
            user_message="Password reset successful! Please login with your new password.",
            developer_message="Password updated and sessions revoked"
        )
    except HTTPException as e:
        return APIResponse.error(
            user_message=e.detail,
            developer_message=e.detail,
            status_code=e.status_code
        )

# @router.get("/google/login")
# async def google_login():
#     try:
#         redirect_uri = settings.GOOGLE_REDIRECT_URI
#         authorization_url = await oauth.google.authorize_redirect(
#             redirect_uri=redirect_uri
#         )
#         return authorization_url
        
#     except Exception as e:
#         return APIResponse.error(
#             user_message="Google login unavailable. Please try again.",
#             developer_message=str(e),
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )


# @router.get("/google/callback")
# async def google_callback(
#     request: Request,
#     db: Session = Depends(get_db)
# ):
#     try:
#         token = await oauth.google.authorize_access_token(request)
#         result = await GoogleOAuthService.handle_callback(db, token)
    
#         frontend_url = f"{settings.FRONTEND_URL}/auth/callback"
#         redirect_url = (
#             f"{frontend_url}"
#             f"?access_token={result['access_token']}"
#             f"&refresh_token={result['refresh_token']}"
#             f"&user_id={result['user'].id}"
#         )
        
#         from fastapi.responses import RedirectResponse
#         return RedirectResponse(url=redirect_url)
        
#     except Exception as e:
#         error_url = f"{settings.FRONTEND_URL}/auth/error?message={str(e)}"
#         from fastapi.responses import RedirectResponse
#         return RedirectResponse(url=error_url)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    try:
      return APIResponse.success(
        data={
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "auth_provider": current_user.auth_provider.value,
            "created_at": current_user.created_at
        },
        user_message="User information retrieved",
        developer_message="Current user data fetched successfully"
    )
    except HTTPException as e:
        return APIResponse.error(
            user_message="Not authenticated",
            developer_message="Not authenticated",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        from src.models.user import RefreshToken

        db.query(RefreshToken).filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False
        ).update({"revoked": True})
        
        db.commit()
        
        return APIResponse.success(
            data={"message": "Logged out successfully"},
            user_message="You've been logged out",
            developer_message="All refresh tokens revoked"
        )
    except Exception as e:
        return APIResponse.error(
            user_message="Logout failed",
            developer_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )