import time
import subprocess
from gtts import gTTS
import tempfile
from playwright.sync_api import sync_playwright

# ------------------ Config ------------------
EMAIL = "dinukanna2003@gmail.com"
PASSWORD = "dinuthillal2003"
MEET_URL = "https://meet.google.com/adi-gyzw-xef"

# Poll captions every N seconds
CAPTION_POLL_INTERVAL = 0.5

# ------------------ Virtual Mic ------------------
def setup_virtual_mic():
    # Idempotent check: skip if already exists
    sinks = subprocess.run(["pactl", "list", "short", "sinks"], capture_output=True).stdout.decode()
    if "VirtualSink" not in sinks:
        subprocess.run([
            "pactl", "load-module", "module-null-sink",
            "sink_name=VirtualSink", "sink_properties=device.description=VirtualSink"
        ])
    sources = subprocess.run(["pactl", "list", "short", "sources"], capture_output=True).stdout.decode()
    if "VirtualMic" not in sources:
        subprocess.run([
            "pactl", "load-module", "module-virtual-source",
            "source_name=VirtualMic", "source_properties=device.description=VirtualMic"
        ])
        subprocess.run([
            "pactl", "load-module", "module-loopback",
            "source=VirtualSink.monitor", "sink=VirtualMic"
        ])
    subprocess.run(["pactl", "set-default-source", "VirtualMic"])
    print("[INFO] VirtualMic ready")

# ------------------ TTS ------------------
def bot_speak(text):
    tts = gTTS(text=text, lang="en")
    tts.save("/tmp/bot_response.wav")
    subprocess.run(["paplay", "--device=VirtualSink", "/tmp/bot_response.wav"])

# def bot_speak(text):
#     # Generate TTS to a temporary file
#     with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
#         tts = gTTS(text=text, lang="en")
#         tts.save(f.name)
#         tts_file = f.name

#     # Stream the audio in real-time to VirtualSink using ffmpeg
#     subprocess.run([
#         "ffmpeg",
#         "-re",              # read in real-time
#         "-i", tts_file,     # input file
#         "-f", "pulse",      # output format: PulseAudio
#         "VirtualSink",      # PulseAudio sink name
#         "-loglevel", "quiet"  # optional: suppress ffmpeg output
#     ])

# ------------------ Google Meet Automation ------------------
def join_meet(playwright):
    browser = playwright.chromium.launch(headless=False, args=[
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--use-fake-ui-for-media-stream",
        "--disable-notifications",
        "--alsa-input-device=VirtualMic",
        "--disable-blink-features=AutomationControlled"
    ])
    # context = browser.new_context()
    # page = context.new_page()

    # Go to Google Sign-In
    # page.goto("https://accounts.google.com/signin/v2/identifier")
    # page.fill("#identifierId", EMAIL)
    # page.click("#identifierNext")
    # page.wait_for_timeout(5000)
    # page.fill("input[name='password']", PASSWORD)
    # page.click("#passwordNext")
    # page.wait_for_timeout(9000)
    # context = browser.new_context()
    # page = context.new_page()
    # page = browser.pages[0]
    context = browser.new_context(storage_state="auth.json")
    page = context.new_page()

    # Join the Meet
    # page.goto(MEET_URL)
    page.goto(MEET_URL, timeout=60000)
    page.wait_for_timeout(5000)

    try:
        cam_button = page.query_selector("div[role='button'][aria-label*='camera']")
        if cam_button:
            cam_button.click()
            print("[INFO] Camera turned off")
    except Exception as e:
        print("[WARN] Camera button not found:", e)

    join_btn = page.query_selector("span:text('Ask to join')")
    if join_btn:
        join_btn.click()
        print("[INFO] Joined the meeting")
    
    time.sleep(10)
    bot_speak("Hello, welcome to the interview. Please introduce yourself. Hey subathra what is your son doing Ask him to go to a job. Kick S dinesh out of the house")


    # Enable captions
    captions_btn = page.query_selector("button[aria-label*='caption']")
    if captions_btn:
        captions_btn.click()
        print("[INFO] Captions enabled")

    return page

# ------------------ Caption Polling ------------------
def poll_captions(page):
    last_text = ""
    while True:
        try:
            # Select the whole captions region
            captions_region = page.query_selector("div[role='region'][aria-label='Captions']")
            if captions_region:
                # Extract speaker label span
                speaker_span = captions_region.query_selector("span.NWpY1d")
                # Extract caption text div
                caption_text_div = captions_region.query_selector("div.ygicle.VbkSUe")

                if speaker_span and caption_text_div:
                    speaker = speaker_span.inner_text().strip()
                    captions_text = caption_text_div.inner_text().strip()

                    # Skip if speaker is "You" (your bot) or blank
                    if speaker.lower() != "you" and captions_text and captions_text != last_text:
                        print(f"[Caption from {speaker}]: {captions_text}")

                        # Send participant's caption text to your AI handler only
                        response = generate_response(captions_text)
                        if response:
                            #bot_speak(response)
                            pass

                        last_text = captions_text
        except Exception as e:
            print("[ERROR]", e)

        time.sleep(CAPTION_POLL_INTERVAL)


# ------------------ LLM / Bot Logic ------------------
def generate_response(text):
    # Replace this with your LLM or rules engine
    return f"I heard: {text}"

# ------------------ Main ------------------
if __name__ == "__main__":
    setup_virtual_mic()
    with sync_playwright() as pw:
        meet_page = join_meet(pw)
        time.sleep(5)  # wait to ensure audio is ready
        poll_captions(meet_page)
