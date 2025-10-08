from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import jwt
from bson import ObjectId
import secrets

from database import (
    connect_to_mongo,
    close_mongo_connection,
    get_spaces_collection,
    get_bookings_collection,
    get_transactions_collection,
    get_gallery_collection,
    get_timeline_collection,
    get_messages_collection,
    get_admins_collection,
)
from services.cloudinary_service import upload_image, delete_image
from services.email_service import send_booking_confirmation, send_contact_notification, send_welcome_email, \
    send_password_reset_email
from services.paystack_service import initialize_payment, verify_payment as verify_paystack_payment

load_dotenv()

app = FastAPI(title="Fombina Tower API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Environment Variables
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")


@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    print("✅ Fombina Tower API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    print("✅ Fombina Tower API shut down")


# Pydantic Models
class Space(BaseModel):
    name: str
    type: str  # office, mall, event-hall
    floor: int
    size: int
    price: int
    features: List[str]
    available: bool
    imageUrl: str
    description: str


class BookingCreate(BaseModel):
    spaceId: str
    userName: str
    userEmail: EmailStr
    userPhone: str
    companyName: Optional[str] = None


class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    phone: str
    message: str


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class MediaUpload(BaseModel):
    title: str
    category: str


# Helper Functions
def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    # Convert datetime objects to ISO format strings
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc


def create_jwt_token(data: dict):
    """Create JWT token"""
    expiration = datetime.utcnow() + timedelta(days=7)
    to_encode = data.copy()
    to_encode.update({"exp": expiration})
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# API Endpoints

@app.get("/")
def read_root():
    return {"message": "Fombina Tower API", "version": "1.0.0", "status": "running"}


# Spaces Endpoints
@app.get("/api/spaces")
async def get_spaces():
    """Get all available spaces"""
    spaces_collection = get_spaces_collection()
    spaces = await spaces_collection.find().to_list(length=100)
    return [serialize_doc(space) for space in spaces]


@app.get("/api/spaces/{space_id}")
async def get_space(space_id: str):
    """Get single space by ID"""
    try:
        spaces_collection = get_spaces_collection()
        space = await spaces_collection.find_one({"_id": ObjectId(space_id)})
        if not space:
            raise HTTPException(status_code=404, detail="Space not found")
        return serialize_doc(space)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/spaces")
async def create_space(space: Space, token: dict = Depends(verify_jwt_token)):
    """Create new space (Admin only)"""
    spaces_collection = get_spaces_collection()
    space_dict = space.dict()
    space_dict["created_at"] = datetime.utcnow()
    result = await spaces_collection.insert_one(space_dict)
    space_dict["_id"] = str(result.inserted_id)
    return serialize_doc(space_dict)


@app.put("/api/spaces/{space_id}")
async def update_space(space_id: str, space: Space, token: dict = Depends(verify_jwt_token)):
    """Update space (Admin only)"""
    try:
        spaces_collection = get_spaces_collection()
        space_dict = space.dict()
        space_dict["updated_at"] = datetime.utcnow()

        result = await spaces_collection.update_one(
            {"_id": ObjectId(space_id)}, {"$set": space_dict}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Space not found")

        return {"success": True, "message": "Space updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Booking Endpoints
@app.post("/api/book-space")
async def book_space(booking: BookingCreate):
    """Create booking and generate Paystack payment URL"""
    try:
        spaces_collection = get_spaces_collection()
        bookings_collection = get_bookings_collection()

        # Get space details
        space = await spaces_collection.find_one({"_id": ObjectId(booking.spaceId)})
        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        if not space.get("available"):
            raise HTTPException(status_code=400, detail="Space is not available")

        # Calculate deposit (10% of monthly price)
        deposit_amount = int(space["price"] * 0.1)

        # Create booking record
        booking_data = {
            "space_id": booking.spaceId,
            "name": booking.userName,
            "email": booking.userEmail,
            "phone": booking.userPhone,
            "company_name": booking.companyName,
            "status": "pending",
            "payment_status": "pending",
            "amount": deposit_amount,
            "created_at": datetime.utcnow(),
        }

        result = await bookings_collection.insert_one(booking_data)
        booking_id = str(result.inserted_id)

        # Generate Paystack payment URL
        payment_result = await initialize_payment(
            email=booking.userEmail,
            amount=deposit_amount * 100,  # Convert to kobo
            reference=f"FT-{booking_id}",
            metadata={
                "booking_id": booking_id,
                "space_name": space["name"],
                "customer_name": booking.userName,
            },
        )

        if payment_result["success"]:
            return {
                "bookingId": booking_id,
                "paymentUrl": payment_result["authorization_url"],
                "reference": payment_result["reference"],
            }
        else:
            raise HTTPException(status_code=400, detail=payment_result.get("error", "Payment initialization failed"))

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/verify-payment/{reference}")
async def verify_payment(reference: str):
    """Verify Paystack payment and update booking"""
    try:
        bookings_collection = get_bookings_collection()
        transactions_collection = get_transactions_collection()
        spaces_collection = get_spaces_collection()

        # Verify payment with Paystack
        verification = await verify_paystack_payment(reference)

        if not verification["success"]:
            raise HTTPException(status_code=400, detail=verification.get("error", "Payment verification failed"))

        # Extract booking ID from reference
        booking_id = reference.replace("FT-", "")

        # Update booking status
        await bookings_collection.update_one(
            {"_id": ObjectId(booking_id)},
            {
                "$set": {
                    "payment_status": "completed",
                    "status": "confirmed",
                    "payment_reference": reference,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        # Create transaction record
        transaction_data = {
            "booking_id": booking_id,
            "reference": reference,
            "amount": verification["amount"] / 100,  # Convert from kobo
            "status": "success",
            "paystack_data": verification,
            "created_at": datetime.utcnow(),
        }
        await transactions_collection.insert_one(transaction_data)

        # Get booking and space details
        booking = await bookings_collection.find_one({"_id": ObjectId(booking_id)})
        space = await spaces_collection.find_one({"_id": ObjectId(booking["space_id"])})

        # Send confirmation email
        await send_booking_confirmation(
            {
                "name": booking["name"],
                "email": booking["email"],
                "phone": booking["phone"],
                "space_name": space["name"],
                "booking_id": booking_id,
                "amount": verification["amount"] / 100,
            }
        )

        return {
            "success": True,
            "reference": reference,
            "spaceName": space["name"],
            "amount": verification["amount"] / 100,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Gallery Endpoints
@app.get("/api/gallery")
async def get_gallery():
    """Get all gallery items"""
    gallery_collection = get_gallery_collection()
    media = await gallery_collection.find().sort("created_at", -1).to_list(length=100)
    return [serialize_doc(item) for item in media]


# Timeline Endpoints
@app.get("/api/timeline")
async def get_timeline():
    """Get construction timeline"""
    timeline_collection = get_timeline_collection()
    events = await timeline_collection.find().sort("date", 1).to_list(length=100)
    return [serialize_doc(event) for event in events]


# Contact Endpoints
@app.post("/api/contact")
async def submit_contact(contact: ContactMessage):
    """Submit contact form"""
    try:
        messages_collection = get_messages_collection()

        contact_data = contact.dict()
        contact_data["created_at"] = datetime.utcnow()
        contact_data["status"] = "new"

        await messages_collection.insert_one(contact_data)

        # Send notification to admin
        await send_contact_notification(contact_data)

        return {"success": True, "message": "Contact form submitted successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Admin Endpoints
@app.post("/api/admin/login")
async def admin_login(credentials: AdminLogin):
    """Admin login"""
    import bcrypt

    admins_collection = get_admins_collection()
    admin = await admins_collection.find_one({"email": credentials.email})

    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password with bcrypt
    if not bcrypt.checkpw(credentials.password.encode("utf-8"), admin["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt_token({"email": credentials.email, "role": "admin"})

    return {"token": token, "email": credentials.email, "name": admin.get("name", "Admin")}


@app.get("/api/admin/bookings")
async def get_admin_bookings(token: dict = Depends(verify_jwt_token)):
    """Get all bookings (Admin only)"""
    bookings_collection = get_bookings_collection()
    bookings = await bookings_collection.find().sort("created_at", -1).to_list(length=1000)
    return [serialize_doc(booking) for booking in bookings]


@app.get("/api/admin/transactions")
async def get_admin_transactions(token: dict = Depends(verify_jwt_token)):
    """Get all transactions (Admin only)"""
    transactions_collection = get_transactions_collection()
    transactions = await transactions_collection.find().sort("created_at", -1).to_list(length=1000)
    return [serialize_doc(transaction) for transaction in transactions]


@app.post("/api/admin/upload-media")
async def upload_media(
        file: UploadFile = File(...),
        title: str = "",
        category: str = "render",
        token: dict = Depends(verify_jwt_token),
):
    """Upload media to Cloudinary (Admin only)"""
    try:
        gallery_collection = get_gallery_collection()

        # Read file data
        file_data = await file.read()

        # Upload to Cloudinary
        result = await upload_image(file_data, folder="fombina-tower", public_id=None)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Upload failed"))

        # Save to database
        media_data = {
            "title": title or file.filename,
            "type": "image" if file.content_type.startswith("image") else "video",
            "url": result["url"],
            "public_id": result["public_id"],
            "category": category,
            "created_at": datetime.utcnow(),
        }

        await gallery_collection.insert_one(media_data)

        return {"success": True, "url": result["url"], "public_id": result["public_id"]}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/admin/contacts")
async def get_admin_contacts(token: dict = Depends(verify_jwt_token)):
    """Get all contact messages (Admin only)"""
    messages_collection = get_messages_collection()
    contacts = await messages_collection.find().sort("created_at", -1).to_list(length=1000)
    return [serialize_doc(contact) for contact in contacts]


@app.get("/api/admin/stats")
async def get_admin_stats(token: dict = Depends(verify_jwt_token)):
    """Get dashboard statistics (Admin only)"""
    spaces_collection = get_spaces_collection()
    bookings_collection = get_bookings_collection()
    transactions_collection = get_transactions_collection()
    messages_collection = get_messages_collection()

    total_spaces = await spaces_collection.count_documents({})
    available_spaces = await spaces_collection.count_documents({"available": True})
    total_bookings = await bookings_collection.count_documents({})
    confirmed_bookings = await bookings_collection.count_documents({"status": "confirmed"})
    total_revenue = await transactions_collection.aggregate([
        {"$match": {"status": "success"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    unread_messages = await messages_collection.count_documents({"status": "new"})

    return {
        "totalSpaces": total_spaces,
        "availableSpaces": available_spaces,
        "totalBookings": total_bookings,
        "confirmedBookings": confirmed_bookings,
        "totalRevenue": total_revenue[0]["total"] if total_revenue else 0,
        "unreadMessages": unread_messages,
    }


# Auth Endpoints
@app.post("/api/auth/register")
async def register_user(user_data: UserRegister):
    """Register new user"""
    import bcrypt

    admins_collection = get_admins_collection()

    # Check if user already exists
    existing_user = await admins_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password = bcrypt.hashpw(user_data.password.encode("utf-8"), bcrypt.gensalt())

    # Create user
    user_dict = {
        "name": user_data.name,
        "email": user_data.email,
        "password": hashed_password.decode("utf-8"),
        "phone": user_data.phone,
        "role": "user",
        "created_at": datetime.utcnow(),
    }

    result = await admins_collection.insert_one(user_dict)

    # Send welcome email
    await send_welcome_email({
        "name": user_data.name,
        "email": user_data.email,
    })

    # Generate token
    token = create_jwt_token({"email": user_data.email, "role": "user"})

    return {
        "token": token,
        "email": user_data.email,
        "name": user_data.name,
        "message": "Registration successful"
    }


@app.post("/api/auth/reset-password-request")
async def request_password_reset(reset_request: PasswordResetRequest):
    """Request password reset"""
    from services.email_service import send_password_reset_email

    admins_collection = get_admins_collection()

    # Find user
    user = await admins_collection.find_one({"email": reset_request.email})
    if not user:
        # Don't reveal if email exists or not for security
        return {"success": True, "message": "If the email exists, a reset link has been sent"}

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    reset_expiry = datetime.utcnow() + timedelta(hours=1)

    # Store reset token
    await admins_collection.update_one(
        {"email": reset_request.email},
        {
            "$set": {
                "reset_token": reset_token,
                "reset_token_expiry": reset_expiry,
            }
        }
    )

    # Send reset email
    await send_password_reset_email({
        "name": user.get("name", "User"),
        "email": reset_request.email,
        "reset_token": reset_token,
    })

    return {"success": True, "message": "If the email exists, a reset link has been sent"}


@app.post("/api/auth/reset-password-confirm")
async def confirm_password_reset(reset_data: PasswordResetConfirm):
    """Confirm password reset with token"""
    import bcrypt

    admins_collection = get_admins_collection()

    # Find user with valid reset token
    user = await admins_collection.find_one({
        "reset_token": reset_data.token,
        "reset_token_expiry": {"$gt": datetime.utcnow()}
    })

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Hash new password
    hashed_password = bcrypt.hashpw(reset_data.new_password.encode("utf-8"), bcrypt.gensalt())

    # Update password and clear reset token
    await admins_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password": hashed_password.decode("utf-8"),
                "updated_at": datetime.utcnow(),
            },
            "$unset": {
                "reset_token": "",
                "reset_token_expiry": "",
            }
        }
    )

    return {"success": True, "message": "Password reset successful"}


@app.post("/api/auth/login")
async def user_login(credentials: AdminLogin):
    """User login"""
    import bcrypt

    admins_collection = get_admins_collection()
    user = await admins_collection.find_one({"email": credentials.email})

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password with bcrypt
    if not bcrypt.checkpw(credentials.password.encode("utf-8"), user["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt_token({"email": credentials.email, "role": user.get("role", "user")})

    return {
        "token": token,
        "email": credentials.email,
        "name": user.get("name", "User"),
        "role": user.get("role", "user")
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
