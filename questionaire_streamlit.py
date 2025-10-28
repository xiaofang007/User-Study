import streamlit as st
import random
import os
import pandas as pd
from datetime import datetime
from PIL import Image

IMAGE_DIR = "Question/images"
IMAGE_DIR_BBOX = "Question/images_bbox"
RESULT_CSV = "Question/results.csv"
NUM_QUESTIONS_PER_PARTICIPANT = 10

images_categories = os.listdir(IMAGE_DIR)
images_bbox_categories = os.listdir(IMAGE_DIR_BBOX)

QUESTION_BANK = []

for img_cat, img_bbox_cat in zip(images_categories, images_bbox_categories):
    images_name = os.listdir(os.path.join(IMAGE_DIR, img_cat))
    images_bbox_name = os.listdir(os.path.join(IMAGE_DIR_BBOX, img_bbox_cat))
    for img_name, image_bbox_name in zip(images_name, images_bbox_name):
        data_dict = {}
        data_dict['left'] = img_name
        data_dict['right'] = image_bbox_name
        data_dict['group'] = img_cat
        QUESTION_BANK.append(data_dict)

CHOICES_TEXTS = [
    "Completely Real / Normal / Natural",
    "Overall Real with Minor Artifacts",
    "Looks edited but somewhat plausible",
    "Completely Fake / Obviously Abnormal"
]

CHOICE_TO_SCORE = {
    "Completely Real / Normal / Natural": 2,
    "Overall Real with Minor Artifacts": 1,
    "Looks edited but somewhat plausible": -1,
    "Completely Fake / Obviously Abnormal": -2,
}

if "participant_id" not in st.session_state:
    # lightweight anonymous ID
    st.session_state.participant_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

if "question_order" not in st.session_state:
    # pick 30 unique questions from your master bank
    # if you have fewer than 30, it'll just use them all
    num_to_ask = min(NUM_QUESTIONS_PER_PARTICIPANT, len(QUESTION_BANK))
    st.session_state.question_order = random.sample(range(len(QUESTION_BANK)), k=num_to_ask)

if "q_index" not in st.session_state:
    st.session_state.q_index = 0  # which question number we're on

if "answers" not in st.session_state:
    # we'll store dicts of {q_idx_in_bank, left_img, right_img, choice}
    st.session_state.answers = []

def save_results():
    os.makedirs(os.path.dirname(RESULT_CSV), exist_ok=True)

    df_new = pd.DataFrame(st.session_state.answers)
    df_new["participant_id"] = st.session_state.participant_id
    df_new["timestamp"] = datetime.now().isoformat()

    # append to csv
    if os.path.exists(RESULT_CSV):
        df_existing = pd.read_csv(RESULT_CSV)
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
        df_all.to_csv(RESULT_CSV, index=False)
    else:
        df_new.to_csv(RESULT_CSV, index=False)



st.title("Rating the Realism of Vehicles in images")

st.markdown("""
In this questionnaire, you will see pairs of images that show the same scene.
The two images are identical, except that in one of them, the vehicle is highlighted with a red dashed box to help you locate it.
Your task is to rate how real or natural the vehicle in the box looks within the whole image.
Note that in some images, the vehicle has been edited.
""")

current_step = st.session_state.q_index
total_steps = len(st.session_state.question_order)

# If we're DONE:
if current_step >= total_steps:
    st.success("Thank you! Your responses have been recorded 🙏")
    st.stop()

# Get the pair for this step
bank_idx = st.session_state.question_order[current_step]
pair = QUESTION_BANK[bank_idx]
left_path = os.path.join(IMAGE_DIR, pair["group"], pair["left"])
right_path = os.path.join(IMAGE_DIR_BBOX, pair["group"], pair["right"])


st.subheader(f"Question {current_step + 1} of {total_steps}")

# Put two images side by side
col1, col2 = st.columns(2)

with col1:
    imgL = Image.open(left_path)
    st.image(left_path, width=imgL.width, caption="Image")

with col2:
    imgR = Image.open(right_path)
    st.image(right_path, width=imgR.width, caption="Image where the vehicle is marked with a red dashed box")

st.write("How realistic / natural does the vehicle inside the red box look? That is, does it look like a real vehicle that naturally belongs in the scene and doesn't stand out?")

# Radio buttons for 4-point scale
choice_text = st.radio(
    "Your answer:",
    CHOICES_TEXTS,
    index=None,  # force them to pick
    key=f"choice_{current_step}",
)

# "Next" button
if st.button("Next"):
    if choice_text is None:
        st.warning("Please select an answer before continuing.")
    else:
        # record answer
        score = CHOICE_TO_SCORE[choice_text]
        st.session_state.answers.append({
            "question_number": current_step + 1,
            "left_img": pair["left"],
            "right_img": pair["right"],
            "group": pair["group"],
            "choice": choice_text,
            "score": score,
        })

        # move to next
        st.session_state.q_index += 1

        # If that was the last one, save to CSV
        if st.session_state.q_index >= total_steps:
            save_results()

        # Rerun to refresh UI
        st.rerun()