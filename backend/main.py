
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi import Request, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from utils import create_user, get_user_by_email, hash_password, verify_password, add_recipe_to_favourites, get_user_favourites_by_email, save_chat_log, get_user_chats, update_user_field
from fastapi.middleware.cors import CORSMiddleware
from myChatBot import WebSocketBotSession
from groq import Groq
import io
import wave
from elevenlabs import ElevenLabs
import os
from dotenv import load_dotenv

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}
client = Groq(api_key=os.getenv("GROQ_API_KEY")) 

@app.get("/get-chat-logs")
async def get_chat_logs(email: str):
    chats = await get_user_chats(email)
    return {"chats": chats}

@app.get("/get-profile")
async def get_profile(email: str):
    user = await get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    return {
        "name": user.get("name", ""),
        "likes": user.get("likes", []),
        "dislikes": user.get("dislikes", []),
        "allergies": user.get("allergies", [])
    }

@app.post("/update-profile")
async def update_profile(request: Request):
    data = await request.json()
    email = data.get("email")
    field = data.get("field")  # likes, dislikes, allergies
    updated_list = data.get("updatedList")

    try:
        await update_user_field(email, field, updated_list)
        return {"status": "success"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")



@app.post("/signup")
async def signup(request: Request):
    data = await request.json()

    # Check required fields only
    required_fields = ["email", "password", "gender"]
    for field in required_fields:
        if not data.get(field):
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    # Optional fields with defaults
    optional_fields = {
        "name": "",
        "profession": "",
        "allergies": [],
        "likes": [],
        "dislikes": [],
        "favorite_recipes": []
    }

    for key, default in optional_fields.items():
        data[key] = data.get(key, default)

    existing_user = await get_user_by_email(data["email"])
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = await create_user(data)
    return {"message": "User created successfully", "user_id": user_id}

@app.post("/login")
async def login(request: Request):
    data = await request.json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    user = await get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "message": "Login successful",
        "email": user["email"]
    }

@app.post("/add-favourite")
async def add_favourite(request: Request):
    data = await request.json()
    email = data.get("email")
    title = data.get("title")
    recipe = data.get("recipe")

    if not all([email, title, recipe]):
        raise HTTPException(status_code=400, detail="Missing data.")

    result = await add_recipe_to_favourites(email, title, recipe)
    return result

@app.post("/transcribe-audio")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        wav_buffer = io.BytesIO(contents)
        wav_buffer.name = "audio.wav"

        transcription = client.audio.transcriptions.create(
            file=wav_buffer,
            model="whisper-large-v3-turbo",
            language="ar",
            response_format="verbose_json"
        )

        return {"text": transcription.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


import requests

@app.get("/get-favourites")
async def get_favourites(email: str):
    favourites = await get_user_favourites_by_email(email)
    if favourites is None:
        raise HTTPException(status_code=404, detail="User not found or no favorites.")
    return {"favourites": favourites}

# @app.post("/speak-text")
# async def speak_text(request: Request):
#     try:
#         data = await request.json()
#         text = data.get("text", "").strip()

#         if not text:
#             raise HTTPException(status_code=400, detail="Text is required.")

#         api_key = os.getenv("GROQ_API_KEY")
#         url = "https://api.groq.com/openai/v1/audio/speech"

#         headers = {
#             "Authorization": f"Bearer {api_key}",
#             "Content-Type": "application/json"
#         }

#         payload = {
#             "model": "playai-tts-arabic",
#             "input": text,
#             "voice": "Nasser-PlayAI",
#             "response_format": "wav"
#         }

#         groq_response = requests.post(url, json=payload, headers=headers)

#         if groq_response.status_code != 200:
#             raise HTTPException(status_code=500, detail=f"Groq TTS failed: {groq_response.text}")

#         audio_stream = io.BytesIO(groq_response.content)
#         audio_stream.seek(0)

#         return StreamingResponse(audio_stream, media_type="audio/wav")

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.post("/speak-text")
async def speak_text(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()

        if not text:
            raise HTTPException(status_code=400, detail="Text is required.")

        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))  # 🔁 Replace this with your actual API key

        audio = client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_multilingual_v2"
        )

        import io
        audio_bytes = b"".join(audio)  # convert generator to bytes
        audio_stream = io.BytesIO(audio_bytes)

        audio_stream.seek(0)

        return StreamingResponse(audio_stream, media_type="audio/mpeg")

    except Exception as e:
        import traceback
        traceback.print_exc()  # 👈 prints full error in console
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🟢 WebSocket connection established.")

    session = WebSocketBotSession()
    session.chat_history = []

    try:
        # Step 1: Wait for email (identifier)
        await websocket.send_json({
            "type": "auth_request",
            "message": "من فضلك ادخل البريد الإلكتروني لتسجيل الدخول."
        })

        login_info = await websocket.receive_json()
        user_email = login_info.get("email", "").strip()
        mode = login_info.get("mode", "text")

        user_data = await get_user_by_email(user_email)
        if not user_data:
            await websocket.send_json({
                "type": "error",
                "message": "المستخدم غير موجود. من فضلك سجل أولاً."
            })
            await websocket.close()
            return

        # Step 2: Use user data from DB to set session
        session.set_user_info(
            name=user_data.get("name", ""),
            gender=user_data.get("gender", "male"),
            profession=user_data.get("profession", None),
            likes = user_data.get("likes", []),
            dislikes = user_data.get("dislikes", []),
            allergies = user_data.get("allergies", []),
            favorite_recipes = user_data.get("favorite_recipes", []),
        )

        session.user_email = user_email  # (optional for future reference)
        session.set_mode(mode)  # Set the mode (text or voice)
        session._update_system_prompt()

        # Step 3: Start the chat loop
        while True:
            user_message = await websocket.receive_text()
            print(f"\n📨 Incoming WebSocket message: {user_message}")

            # Check for reset command
            if user_message.strip() == "/new":
                session = WebSocketBotSession()  # Reset session completely
                session.set_user_info(
                    name=user_data.get("name", ""),
                    gender=user_data.get("gender", "male"),
                    profession=user_data.get("profession", None),
                    likes = user_data.get("likes", []),
                    dislikes = user_data.get("dislikes", []),
                    allergies = user_data.get("allergies", []),
                    favorite_recipes = user_data.get("favorite_recipes", [])
                )
                session.user_email = user_email

                await websocket.send_json({
                    "type": "reset",
                    "message": "✅ تم بدء محادثة جديدة تمامًا."
                })

                continue

            if session.expecting_choice:
                try:
                    selected_index = int(user_message.strip()) - 1

                    # ✅ Append the original query only if stored
                    if session.last_user_query:
                        session.chat_history.append({"sender": "user", "text": session.last_user_query})
                        session.last_user_query = None  # reset after logging

                    # ✅ Append the user's choice
                    session.chat_history.append({"sender": "user", "text": user_message})

                    result = await session.handle_choice(selected_index)

                    if result["type"] == "response":
                        session.chat_history.append({"sender": "bot", "text": result["message"]})

                except (ValueError, IndexError):
                    result = {
                        "type": "error",
                        "message": "من فضلك اختر رقم من الاختيارات الموجودة."
                    }

            else:
                result = await session.handle_message(user_message)

                # ✅ Only append here if NOT expecting a follow-up choice
                if result["type"] == "suggestions":
                    session.last_user_query = user_message  # store temporarily for next choice
                else:
                    session.chat_history.append({"sender": "user", "text": user_message})
                    session.chat_history.append({"sender": "bot", "text": result["message"]})




            await websocket.send_json(result)
            # if result["type"] == "response":
            #     session.chat_history.append({"sender": "user", "text": user_message})
            #     session.chat_history.append({"sender": "bot", "text": result["message"]})

            print("📤 Response sent to frontend.\n")

    except WebSocketDisconnect:
         print("🔴 WebSocket disconnected.")
         if session.chat_history:
            await save_chat_log(user_email, session.chat_history)
        
