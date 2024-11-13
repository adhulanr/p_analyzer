import base64
from requests import post, get
import json
import google.generativeai as genai
import re
from flask import Flask, flash, render_template, request
import markdown2
import os

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
api_key = os.getenv("GOOGLE_GENAI_API_KEY")

# client_id = "c465aaab78de4405bf27729e2e751a23"
# client_secret = "edd928b6cff540d3a2f378625f6e283b"

# Google GenAI API key
# api_key = 'AIzaSyB8bDXuAZIlnevOoFvdh1ZEd4DTJwa4VoM'

# Configure app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") # Needed for flashing messages

# Configure AI
genai.configure(api_key=api_key)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("p_url")

        # Validate and process playlist URL
        try:
            playlist_url = validate_playlist(url)
            token = get_token()
            tracks = get_playlist_tracks(token, playlist_url)

            # Format tracks for AI
            track_list = ""
            for idx, track in enumerate(tracks):
                track_list += f"{idx + 1}. {track}\n"

            # Get AI analysis
            analysis = ai_feed(track_list)
            return render_template("index.html", analysis=analysis)
        
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            # Log the actual error message for debugging
            print("Error occurred:", str(e))
            flash("An error occurred. Please try again. Error: " + str(e), "danger")

    return render_template("index.html")

def validate_playlist(link):
    # Updated regex to allow for optional query parameters after the playlist ID
    match = re.search(r"^https://open\.spotify\.com/playlist/[a-zA-Z0-9]+(\?.*)?$", link)
    if match:
        return link
    else:
        raise ValueError("Invalid Playlist URL!")



def get_token():
    auth_str = client_id + ":" + client_secret
    auth_bytes = auth_str.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token


def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def get_playlist_tracks(token, playlist_url):
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(token)
    params = {"limit": 50}

    result = get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["items"]

    tracks = []
    for item in json_result:
        track = item["track"]
        track_name = track["name"]
        artist_names = ", ".join(artist["name"] for artist in track["artists"])
        tracks.append(f"{track_name} by {artist_names}")

    return tracks


def ai_feed(tracks):
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    chat_session = model.start_chat(history=[])

    response = chat_session.send_message(
        tracks + "Hey! I’ve got a Spotify playlist containing these songs, and I’m curious to know what you think of my music taste. Can you take a look at the songs and, you know, be brutally honest? Feel free to roast, completely obliterate, joke, and critique my choices- it will help me have a few laughs! Oh, and if you have any recommendations that would fit the vibe, I’m all ears. Make sure to roast me and make fun of me while analysing my playlist. Have a friendly and highly informal tone."
    )

    return markdown2.markdown(response.text)