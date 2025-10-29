import streamlit as st
import random
import os
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
import time

### Admin Login ###
st.sidebar.title("🔒 Admin Login")
admin_pw_input = st.sidebar.text_input("Enter admin password:", type="password")

# show admin panel if password correct
if admin_pw_input == st.secrets.get("admin_password", "default_pw"):
    st.sidebar.success("Admin mode activated")

    st.title("Admin Dashboard - Questionnaire Results")

    SHEET_CSV_URL = st.secrets.get("GOOGLE_SHEET_CSV_URL", "")

    if not SHEET_CSV_URL:
        st.warning("please set GOOGLE_SHEET_CSV_URL")
    else:
        try:
            df = pd.read_csv(SHEET_CSV_URL)
            st.write("### All Responses")
            st.dataframe(df)

            # "group" average score
            if "group" in df.columns and "score" in df.columns:
                avg = df.groupby("group")["score"].mean().reset_index()
                avg.columns = ["Group", "Average Score"]
                st.write("### Average Score per Group")
                st.dataframe(avg)

            # Download button
            st.download_button(
                label="⬇️ Download All Results as CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="results_export.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"Fail to read data: {e}")

    st.stop()



### User Questionnaire App ###
IMAGE_DIR = "Question/images"
IMAGE_DIR_BBOX = "Question/images_bbox"
RESULT_CSV = "Question/results.csv"
NUM_QUESTIONS_PER_PARTICIPANT = 30

images_categories = sorted(os.listdir(IMAGE_DIR))
images_bbox_categories = sorted(os.listdir(IMAGE_DIR_BBOX))

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
    num_to_ask = min(NUM_QUESTIONS_PER_PARTICIPANT, len(QUESTION_BANK))
    st.session_state.question_order = random.sample(range(len(QUESTION_BANK)), k=num_to_ask)

if "q_index" not in st.session_state:
    st.session_state.q_index = 0  # which question number we're on

if "answers" not in st.session_state:
    # we'll store dicts of {q_idx_in_bank, left_img, right_img, choice}
    st.session_state.answers = []

# this tracks the last question number we successfully saved,
# so we never double-save that question
if "last_saved_qnum" not in st.session_state:
    st.session_state.last_saved_qnum = None


#### Saving results to google form via POST ####
def get_form_config():
    """
    fill in .streamlit/secrets.toml (local) or on
    Streamlit Cloud -> Settings -> Secrets
    """
    try:
        action_url = st.secrets["FORM_ACTION_URL"]
        entry_map = {
            "group": st.secrets["FORM_ENTRY_GROUP"],
            "left_img": st.secrets["FORM_ENTRY_LEFT_IMG"],
            "right_img": st.secrets["FORM_ENTRY_RIGHT_IMG"],
            "score": st.secrets["FORM_ENTRY_SCORE"],
            "choice": st.secrets["FORM_ENTRY_CHOICE"],
            "participant_id": st.secrets["FORM_ENTRY_PID"],
            "timestamp": st.secrets["FORM_ENTRY_TS"],
        }
        return action_url, entry_map
    except Exception as e:
        st.error(f"cannot find the configuration: {e}")
        return None, None
    

def submit_single_row_to_google_form(action_url, entry_map, row):
    """
    row is a dict, including keys:
    group, left_img, right_img, score, participant_id, timestamp
    send to Google form (formResponse).
    """
    payload = {
        entry_map["group"]: row["group"],
        entry_map["left_img"]: row["left_img"],
        entry_map["right_img"]: row["right_img"],
        entry_map["score"]: row["score"],
        entry_map["participant_id"]: row["participant_id"],
        entry_map["timestamp"]: row["timestamp"],
    }
    try:
        r = requests.post(action_url, data=payload, timeout=10)
        return 200 <= r.status_code < 300
    except Exception:
        return False


def submit_all_answers_to_google_form():
    """
    write current st.session_state.answers to Google Form.
    Every answer will be sent as a separate row.
    """
    action_url, entry_map = get_form_config()
    if not action_url or not entry_map:
        return 0, len(st.session_state.answers)

    success = 0
    fail = 0

    for ans in st.session_state.answers:
        ans_to_send = ans.copy()
        ans_to_send["participant_id"] = st.session_state.participant_id
        ans_to_send["timestamp"] = datetime.now().isoformat()

        ok = submit_single_row_to_google_form(action_url, entry_map, ans_to_send)
        if ok:
            success += 1
        else:
            fail += 1

    return success, fail


### ### Main app UI ### ###
st.title("Rating the Realism of Vehicles")

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
    succ, fail = submit_all_answers_to_google_form()

    if fail == 0:
        st.success(f"Thank you! Your responses have been recorded. 🙏")
    else:
        st.warning(f"Submissions: {succ} successful, {fail} fail.")

    # clear session_state.answers，avoid resubmission
    st.session_state.answers = []

    st.stop()


# Get the pair for this step, show current question number
bank_idx = st.session_state.question_order[current_step]
pair = QUESTION_BANK[bank_idx]
left_path = os.path.join(IMAGE_DIR, pair["group"], pair["left"])
right_path = os.path.join(IMAGE_DIR_BBOX, pair["group"], pair["right"])


st.subheader(f"Question {current_step + 1} of {total_steps}")

# Put two images side by side
col1, col2 = st.columns(2)

with col1:
    imgL = Image.open(left_path)
    display_wl = min(imgL.width, 600)
    st.image(left_path, width=display_wl, caption="Image")

with col2:
    imgR = Image.open(right_path)
    display_wr = min(imgR.width, 600)
    st.image(right_path, width=display_wr, caption="Image where the vehicle is marked with a red dashed box")

st.write("How realistic / natural does the vehicle inside the red box look? That is, does it look like a real vehicle that naturally belongs in the scene and doesn't stand out?")

# Radio buttons for 4-point scale
choice_text = st.radio(
    "Your answer:",
    CHOICES_TEXTS,
    index=None,  # force them to pick
    key=f"choice_{current_step}",
)

is_last_question = (current_step == total_steps - 1)
button_label = "Submit" if is_last_question else "Next"


with st.form(key=f"form_{current_step}"):
    submitted = st.form_submit_button(button_label)
    if submitted:
        if choice_text is None:
            st.warning("Please select an answer before continuing.")
        else:
            current_question_number = current_step + 1
            
            if st.session_state.last_saved_qnum == current_question_number:
                # We already stored this one. Ignore the spam click.
                st.info("Answer already recorded, loading next...")
            
            # record answer
            else:
                score = CHOICE_TO_SCORE[choice_text]
                st.session_state.answers.append({
                    "question_number": current_step + 1,
                    "left_img": pair["left"],
                    "right_img": pair["right"],
                    "group": pair["group"],
                    "choice": choice_text,
                    "score": score,
                })
                
                # mark this question as saved   
                st.session_state.last_saved_qnum = current_question_number

                # move to next
                st.session_state.q_index += 1

                # Rerun to refresh UI
                st.rerun()