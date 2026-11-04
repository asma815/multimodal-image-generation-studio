
import os
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
import streamlit as st


# ---------------- PAGE SETTINGS ----------------

st.set_page_config(
    page_title="Multimodal Image Generation Studio",
    page_icon="🎨",
    layout="wide"
)

st.title("🎨 Multimodal Image Generation Studio")
st.write("Turn your text descriptions into AI-generated artwork.")


# ---------------- API SETTINGS ----------------

BASE_URL = "https://aihorde.net/api/v2"
API_KEY = "0000000000"

HEADERS = {
    "apikey": API_KEY,
    "Client-Agent": "MultimodalImageStudio:1.0:portfolio"
}

SAVE_FOLDER = "generated_images"
os.makedirs(SAVE_FOLDER, exist_ok=True)


# ---------------- IMAGE DIMENSIONS ----------------

dimensions = {
    "Square (512 x 512)": (512, 512),
    "Landscape (576 x 384)": (576, 384),
    "Portrait (384 x 576)": (384, 576)
}


# ---------------- IMAGE GENERATION ----------------

def generate_images(prompt, width, height, count):

    payload = {
        "prompt": prompt,
        "params": {
            "width": width,
            "height": height,
            "n": count,
            "steps": 20
        },
        "nsfw": False,
        "censor_nsfw": True,
        "r2": True
    }

    response = requests.post(
        f"{BASE_URL}/generate/async",
        headers=HEADERS,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    request_id = response.json().get("id")

    if not request_id:
        raise Exception("The API did not return a request ID.")

    progress = st.progress(0)
    status = st.empty()
    start_time = time.monotonic()

    while time.monotonic() - start_time < 300:

        result = requests.get(
            f"{BASE_URL}/generate/check/{request_id}",
            headers=HEADERS,
            timeout=30
        )

        result.raise_for_status()
        data = result.json()

        if data.get("faulted"):
            raise Exception(
                "The AI service could not generate the image. "
                "Please try again later."
            )

        if data.get("done"):
            progress.progress(100)
            status.success("Generation completed!")
            break

        finished = data.get("finished", 0)
        waiting = data.get("wait_time", 0)

        progress.progress(min(95, int(finished * 100)))

        status.info(
            f"Waiting for AI workers... "
            f"Completed: {finished} | "
            f"Estimated wait: {waiting} seconds"
        )

        time.sleep(4)

    else:
        raise TimeoutError(
            "Generation took too long. Please try again later."
        )

    result = requests.get(
        f"{BASE_URL}/generate/status/{request_id}",
        headers=HEADERS,
        timeout=60
    )

    result.raise_for_status()

    generations = result.json().get("generations", [])

    if not generations:
        raise Exception(
            "No image was returned. Try again later."
        )

    return generations


# ---------------- USER INTERFACE ----------------

st.divider()
st.subheader("Create Your Artwork")

prompt = st.text_area(
    "Describe the image you want:",
    placeholder=(
        "Example: A white cat sitting in a garden "
        "full of colorful flowers"
    ),
    height=120
)


col1, col2, col3 = st.columns(3)

with col1:
    style = st.selectbox(
        "Image Style",
        [
            "Digital Art",
            "Realistic",
            "Anime",
            "Watercolor",
            "3D Render"
        ]
    )

with col2:
    size = st.selectbox(
        "Image Size",
        list(dimensions.keys())
    )

with col3:
    count = st.selectbox(
        "Number of Images",
        [1, 2]
    )


width, height = dimensions[size]


# ---------------- GENERATE BUTTON ----------------

if st.button(
    "✨ Generate AI Image",
    type="primary",
    use_container_width=True
):

    if not prompt.strip():

        st.warning(
            "Please enter an image description first."
        )

    else:

        final_prompt = (
            f"{prompt.strip()}, {style} style, "
            "high quality, detailed artwork"
        )

        try:

            with st.spinner(
                "Connecting to the AI service..."
            ):
                generations = generate_images(
                    final_prompt,
                    width,
                    height,
                    count
                )

            st.subheader("Your Generated Artwork")

            displayed = 0

            for index, item in enumerate(generations):

                image_url = item.get("img")

                if not image_url:
                    continue

                image_response = requests.get(
                    image_url,
                    timeout=60
                )

                image_response.raise_for_status()

                image_bytes = image_response.content

                extension = os.path.splitext(
                    urlparse(image_url).path
                )[1].lower()

                mime_types = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".webp": "image/webp"
                }

                if extension not in mime_types:
                    extension = ".png"

                filename = (
                    "image_"
                    + datetime.now().strftime("%Y%m%d_%H%M%S")
                    + f"_{index + 1}{extension}"
                )

                st.image(
                    image_bytes,
                    caption=f"Generated Image {index + 1}",
                    use_container_width=True
                )

                st.download_button(
                    label="⬇️ Download Image",
                    data=image_bytes,
                    file_name=filename,
                    mime=mime_types[extension],
                    key=f"download_{index}"
                )

                file_path = os.path.join(
                    SAVE_FOLDER,
                    filename
                )

                with open(file_path, "wb") as file:
                    file.write(image_bytes)

                st.caption(
                    f"Local copy saved: {file_path}"
                )

                displayed += 1

            if displayed == 0:
                st.warning(
                    "The API returned no usable image URLs."
                )

        except requests.exceptions.HTTPError as error:

            details = ""

            if error.response is not None:
                details = error.response.text[:500]

            st.error(f"API HTTP error: {error}")

            if details:
                st.code(details)

        except requests.exceptions.RequestException as error:

            st.error(f"Connection error: {error}")

        except TimeoutError as error:

            st.warning(str(error))

        except Exception as error:

            st.error(f"Something went wrong: {error}")


# ---------------- FOOTER ----------------

st.divider()
st.caption("Multimodal Image Generation Studio")

