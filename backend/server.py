from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
import tempfile
import shutil

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-here')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Emergent LLM Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    password_hash: str
    full_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class ClaimAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    policy_file: str
    claim_file: str
    bills_file: str
    doctor_notes_file: str
    decision: str  # "PASS" or "FAIL"
    reasoning: str
    confidence_score: Optional[float] = None
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# Auth routes
@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name
    )
    
    user_dict = user.model_dump()
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    await db.users.insert_one(user_dict)
    
    # Create token
    access_token = create_access_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": user['id']})
    
    return TokenResponse(
        access_token=access_token,
        user={
            "id": user['id'],
            "email": user['email'],
            "full_name": user['full_name']
        }
    )

@api_router.get("/auth/me")
async def get_me(current_user = Depends(get_current_user)):
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "full_name": current_user['full_name']
    }

# Claim analysis routes
@api_router.post("/claims/analyze")
async def analyze_claim(
    policy: UploadFile = File(...),
    claim: UploadFile = File(...),
    bills: UploadFile = File(...),
    doctor_notes: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    try:
        # Save uploaded files temporarily
        temp_dir = tempfile.mkdtemp()
        
        policy_path = os.path.join(temp_dir, f"policy_{uuid.uuid4()}.pdf")
        claim_path = os.path.join(temp_dir, f"claim_{uuid.uuid4()}.pdf")
        bills_path = os.path.join(temp_dir, f"bills_{uuid.uuid4()}.pdf")
        doctor_path = os.path.join(temp_dir, f"doctor_{uuid.uuid4()}.pdf")
        
        with open(policy_path, "wb") as f:
            shutil.copyfileobj(policy.file, f)
        with open(claim_path, "wb") as f:
            shutil.copyfileobj(claim.file, f)
        with open(bills_path, "wb") as f:
            shutil.copyfileobj(bills.file, f)
        with open(doctor_path, "wb") as f:
            shutil.copyfileobj(doctor_notes.file, f)
        
        # Initialize Gemini chat with file support
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"claim_analysis_{uuid.uuid4()}",
            system_message="You are an expert insurance claim analyst. Analyze insurance claims based on policy rules."
        ).with_model("gemini", "gemini-2.0-flash")
        
        # Create file attachments
        policy_file = FileContentWithMimeType(file_path=policy_path, mime_type="application/pdf")
        claim_file = FileContentWithMimeType(file_path=claim_path, mime_type="application/pdf")
        bills_file = FileContentWithMimeType(file_path=bills_path, mime_type="application/pdf")
        doctor_file = FileContentWithMimeType(file_path=doctor_path, mime_type="application/pdf")
        
        # Analyze with AI
        prompt = """Analyze this insurance claim submission carefully:

1. First, extract all relevant rules and coverage criteria from the POLICY document
2. Review the CLAIM form for what is being claimed
3. Verify the BILLS for amounts and medical procedures
4. Cross-check DOCTOR NOTES for medical necessity and diagnosis
5. Determine if the claim should PASS or FAIL based on policy rules

Provide your response in this exact format:

DECISION: [PASS or FAIL]

REASONING:
[Detailed explanation of why the claim passes or fails, referencing specific policy rules and evidence from the documents]

CONFIDENCE: [percentage, e.g., 85%]"""
        
        user_message = UserMessage(
            text=prompt,
            file_contents=[policy_file, claim_file, bills_file, doctor_file]
        )
        
        response = await chat.send_message(user_message)
        
        # Parse AI response
        decision = "UNKNOWN"
        reasoning = response
        confidence = None
        
        if "DECISION:" in response:
            lines = response.split('\n')
            for line in lines:
                if line.strip().startswith("DECISION:"):
                    decision_text = line.split("DECISION:")[1].strip()
                    decision = "PASS" if "PASS" in decision_text.upper() else "FAIL"
                elif line.strip().startswith("CONFIDENCE:"):
                    conf_text = line.split("CONFIDENCE:")[1].strip()
                    try:
                        confidence = float(conf_text.replace('%', '').strip())
                    except:
                        confidence = None
            
            if "REASONING:" in response:
                reasoning = response.split("REASONING:")[1].split("CONFIDENCE:")[0].strip()
        
        # Save analysis to database
        analysis = ClaimAnalysis(
            user_id=current_user['id'],
            policy_file=policy.filename,
            claim_file=claim.filename,
            bills_file=bills.filename,
            doctor_notes_file=doctor_notes.filename,
            decision=decision,
            reasoning=reasoning,
            confidence_score=confidence
        )
        
        analysis_dict = analysis.model_dump()
        analysis_dict['analyzed_at'] = analysis_dict['analyzed_at'].isoformat()
        await db.claim_analyses.insert_one(analysis_dict)
        
        # Cleanup temp files
        shutil.rmtree(temp_dir)
        
        return {
            "id": analysis.id,
            "decision": decision,
            "reasoning": reasoning,
            "confidence_score": confidence,
            "analyzed_at": analysis.analyzed_at.isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error analyzing claim: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing claim: {str(e)}")

@api_router.get("/claims/history")
async def get_claim_history(current_user = Depends(get_current_user)):
    claims = await db.claim_analyses.find(
        {"user_id": current_user['id']},
        {"_id": 0}
    ).sort("analyzed_at", -1).to_list(100)
    
    for claim in claims:
        if isinstance(claim.get('analyzed_at'), str):
            claim['analyzed_at'] = datetime.fromisoformat(claim['analyzed_at']).isoformat()
    
    return claims

@api_router.get("/claims/{claim_id}")
async def get_claim_details(claim_id: str, current_user = Depends(get_current_user)):
    claim = await db.claim_analyses.find_one(
        {"id": claim_id, "user_id": current_user['id']},
        {"_id": 0}
    )
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    return claim

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()