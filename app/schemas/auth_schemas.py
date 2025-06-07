from pydantic import BaseModel, Field
from typing import Optional

class LoginRequest(BaseModel):
    apiKey: str = Field(..., description='The Gemini API Key provided by the user', min_length=1) # Ensure apiKey is not empty

class User(BaseModel):
    id: str = Field(..., description="Unique identifier for the user (e.g., hash of API key)")
    # email: Optional[str] = None # Example for future extension
    # username: Optional[str] = None # Example for future extension

class TokenData(BaseModel): # Internal model representing the data encoded in the token
    sub: str = Field(..., description="Subject of the token, typically the user ID")
    # You can add other custom claims here if needed

class Token(BaseModel): # Response model for the login endpoint
    access_token: str
    token_type: str = 'bearer'
    user: User # As per blueprint: { "token": "...", "user": { ... } }
