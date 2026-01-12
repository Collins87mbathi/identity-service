from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.models.user import User, RefreshToken, OTP, AuthProvider
from src.schemas.auth import UserRegister, UserLogin
from src.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_otp,
    decode_token
)
from src.services.email import EmailService
from src.config import get_settings

settings = get_settings()


class AuthService:
    @staticmethod
    async def register_user(db: Session, user_data: UserRegister):
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            auth_provider=AuthProvider.LOCAL
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        otp_code = generate_otp()
        otp_expires = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        
        otp_record = OTP(
            email=user_data.email,
            otp_code=otp_code,
            otp_type="email_verification",
            expires_at=otp_expires
        )
        db.add(otp_record)
        db.commit()
        
        await EmailService.send_verification_email(user_data.email, otp_code)
        
        return new_user

    @staticmethod
    async def verify_email(db: Session, email: str, otp_code: str):
        otp_record = db.query(OTP).filter(
            OTP.email == email,
            OTP.otp_code == otp_code,
            OTP.otp_type == "email_verification",
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        ).first()
        
        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        otp_record.is_used = True
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_verified = True
        user.is_active = True
        
        db.commit()
        return user

    @staticmethod
    def login_user(db: Session, login_data: UserLogin):
        user = db.query(User).filter(User.email == login_data.email).first()
        
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please verify your email first."
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        refresh_token_expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=refresh_token_expires
        )
        db.add(refresh_token_record)
        db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user
        }

    @staticmethod
    async def forgot_password(db: Session, email: str):
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return {"message": "If the email exists, a reset code has been sent"}
        
        otp_code = generate_otp()
        otp_expires = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        
        otp_record = OTP(
            email=email,
            otp_code=otp_code,
            otp_type="password_reset",
            expires_at=otp_expires
        )
        db.add(otp_record)
        db.commit()
        
        await EmailService.send_password_reset_email(email, otp_code)
        
        return {"message": "If the email exists, a reset code has been sent"}

    @staticmethod
    async def reset_password(db: Session, email: str, otp_code: str, new_password: str):
        otp_record = db.query(OTP).filter(
            OTP.email == email,
            OTP.otp_code == otp_code,
            OTP.otp_type == "password_reset",
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        ).first()
        
        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.hashed_password = get_password_hash(new_password)
        otp_record.is_used = True
        
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({"revoked": True})
        
        db.commit()
        return user

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str):
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        token_record = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired or revoked"
            )
        
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        
        return {"access_token": access_token}

    @staticmethod
    async def resend_verification_otp(db: Session, email: str):
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        otp_code = generate_otp()
        otp_expires = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        
        otp_record = OTP(
            email=email,
            otp_code=otp_code,
            otp_type="email_verification",
            expires_at=otp_expires
        )
        db.add(otp_record)
        db.commit()
        
        await EmailService.send_verification_email(email, otp_code)
        
        return {"message": "Verification code sent"}