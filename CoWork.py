#CoWork - NC

print("loading...")
    
import os, time, re, pyautogui
from google import genai
import mss
import mss.tools
import cv2
import numpy as np
from datetime import datetime
from google.genai import types
import asyncio

_KEY_ALIASES = {
    "pgdn": "pgdn",
    "pg down": "pgdn",
    "page down": "pgdn",
    "pagedown": "pgdn",
    "PageDown": "pgdn",
    "pgup": "pgup",
    "pg up": "pgup",
    "page up": "pgup",
    "pageup": "pgup",
    "esc": "escape",
    "return": "enter",
    "ctrl": "ctrl",
    "control": "ctrl",
}

def normalize_key(k):
    cleaned = k.strip().lower().replace("_", " ")
    cleaned = _KEY_ALIASES.get(cleaned, cleaned)
    return cleaned.replace(" ", "")

compression_factor = .6 #change this if you want slower but more accurate AI. .7 = 70% res, 1 would be 100% res.

print()

width, height = pyautogui.size()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def s(text="BLANK",skip=False, speed=.02):
    for char in text:
        print(char,end="",flush=not skip)
        time.sleep(speed)

script_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(script_dir, "screenshot.png")


import json

memory_file = os.path.join(script_dir, "memory.json")

def load_memory():
    """Returns the list of past messages, or an empty list if the file doesn't exist yet."""
    if not os.path.exists(memory_file):
        return []
    try:
        with open(memory_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []

def save_memory(memory_list):
    """Saves only the last 3 entries to the JSON file."""
    trimmed = memory_list[-3:]
    with open(memory_file, "w") as f:
        json.dump(trimmed, f, indent=4)

def do_action(text="hey wsp dude [left;100,100] oh yeah and [right;200,200]"):
    pattern = r"\[(.*?)\]"
    
    results = re.findall(pattern, text)

    for raw_action in results:
        action = raw_action.strip()

        parts = action.split(";", 1)
        purpose = parts[0].strip().lower()
        payload = parts[1].strip() if len(parts) > 1 else ""

        try:
            if purpose == "type":
                sentence = payload
                time.sleep(.2)
                pyautogui.write(sentence, interval=0.01)
                time.sleep(.2)
                        
            elif purpose == "multhold":
                keys = [normalize_key(k)  for k in payload.split(",") if k.strip()]
                if keys:
                    for k in keys:
                        time.sleep(0.1)
                        pyautogui.keyDown(k)
                    
            elif purpose == "multiple":
                keys = [normalize_key(k) for k in payload.split(",") if k.strip()]
                if keys:
                    time.sleep(0.1)
                    pyautogui.hotkey(*keys)

            elif purpose in ("left", "right", "middle"):
                coords = [c.strip() for c in payload.split(",")]
                if len(coords) >= 2:
                    norm_x = int(coords[0])
                    norm_y = int(coords[1])
                    x = (norm_x / 1000) * width
                    y = (norm_y / 1000) * height
                    button = "left" if purpose == "left" else ("right" if purpose == "right" else "middle")
                    time.sleep(0.05)
                    pyautogui.moveTo(x=x, y=y, duration=.1)
                    time.sleep(.1)
                    pyautogui.click(x=x, y=y, button=button)
            
            elif purpose == "hover":
                coords = [c.strip() for c in payload.split(",")]
                if len(coords) >= 2:
                    norm_x = int(coords[0])
                    norm_y = int(coords[1])
                    x = (norm_x / 1000) * width
                    y = (norm_y / 1000) * height
                    time.sleep(0.05)
                    pyautogui.moveTo(x=x, y=y, duration=.1)
                else:
                    print("HOVER missing coordinates:", payload)

            elif purpose.endswith("drag") or purpose in ("leftdrag", "rightdrag", "middledrag"):
                coords = [c.strip() for c in payload.split(",")]
                if len(coords) >= 5:
                    norm_sx, norm_sy, norm_ex, norm_ey, duration = coords[:5]
                    norm_sx, norm_sy, norm_ex, norm_ey = map(int, (norm_sx, norm_sy, norm_ex, norm_ey))
                    duration = float(duration)
                    sx = (norm_sx / 1000) * width
                    sy = (norm_sy / 1000) * height
                    ex = (norm_ex / 1000) * width
                    ey = (norm_ey / 1000) * height
                    button = "left" if purpose.startswith("left") else ("right" if purpose.startswith("right") else "middle")
                    time.sleep(0.05)
                    pyautogui.mouseDown(x=sx, y=sy, button=button)
                    pyautogui.moveTo(ex, ey, duration=duration)
                    pyautogui.mouseUp(x=ex, y=ey, button=button)
                else:
                    print("DRAG missing parameters:", payload)
            elif purpose == "hold":
                key = payload
                pyautogui.keyDown(key)

            elif purpose == "releasemultiple":
                keys = [normalize_key(k)  for k in payload.split(",") if k.strip()]
                if keys:
                    for k in keys:
                        time.sleep(0.1)
                        pyautogui.keyUp(k)
            
            elif purpose == "release":
                key = payload
                pyautogui.keyUp(key)

            else:
                print("NOT RECOGNIZED INPUT:", action)
        except Exception as e:
            print("Action failed:", action, "error:", e)

        time.sleep(0.01)

        
async def my_func(result_text="AHHH"):
    await asyncio.sleep(1)
    s(result_text)

async def main_go(result_text="AHHH"):
    task = asyncio.create_task(my_func(result_text))
    await task 
    
def get_gemini_response(image_bytes, prompt_text):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    prompt_text
                ]
            )
            return response
        except Exception as e:
            wait = min(2 ** attempt, 30)  # exponential backoff, capped at 30s
            print(f"Gemini call failed (attempt {attempt+1}/{max_retries}): {e}")
            print(f"Retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError("Gemini API failed after all retries — giving up this cycle.")
                
def main():
    while True:
        s("processing...")
        
        with mss.MSS() as sct:
            # 1. Grab the monitor screenshot
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            
            # 2. Convert the raw MSS pixels directly to a NumPy array (BGRA format)
            # This is much faster than processing through PNG bytes first
            img_np = np.array(shot)
            
            # 3. Define your target low-resolution size (Width, Height)
            # For example, scaling down to 1280x720
            target_resolution = (int(width*compression_factor), int(height*compression_factor))
            
            # 4. Decrease the resolution using OpenCV
            low_res_img = cv2.resize(img_np, target_resolution, interpolation=cv2.INTER_AREA)
            
            # 5. Compress and encode the low-res image back into PNG bytes
            # cv2.imencode returns a tuple (success, encoded_array); we grab the array
            success, encoded_img = cv2.imencode('.png', low_res_img)
            if success:
                image_bytes = encoded_img.tobytes()
        
        # 'image_bytes' is now your lower resolution PNG byte string, 
        # ready to be sent over a network or saved to disk.

        past_messages = load_memory()
    
        memory_context = ""
        if past_messages:
            memory_context = "\n\nHere are your last few messages for context. use them to understand what you did, doing, and need to do:\n"
            for i, entry in enumerate(past_messages, 1):
                memory_context += f"{i}. ({entry['timestamp']}) {entry['text']}\n"
    
        prompt_text = ("You are a AI Assistant of the User. Your goal is to complete the task given to you by the User."
                       + " You can interact with the screen via using textual commands."
                       + "When giving coordinates, express x and y on a normalized 0-1000 scale relative to the screenshot you are viewing "
                       + "(0,0 is the top-left corner, 1000,1000 is the bottom-right corner), NOT actual pixel values. "
                       + "For example [left;500,500] means click the exact center of the screen regardless of its resolution."
                       + "format you commands like so."
                       + "[action;x,y]"
                       + "so if you want to do a left click at 200, 300 you would put in your response,"
                       + "[left;200,300]."
                       + "keep in mind that for dragging the mouse you should form at it like this."
                       + "[action;start_x,start_y,end_x,end_y,duration]"
                       + "so if you wanted to drag the mouse using left click from 200,300 to 400,300 over 1 second it would look like this"
                       + "[leftdrag;200,300,400,300,1]"
                       + "in a situation where you are tasked with opening and dragging a test upwards you would get the screenshot and assess where the pixels woudl align." 
                       + "once you figure out that you should click at 500,200 then drag the mouse from 400,200 to 400,800 in 1 second your output would look like this"
                       + "'first im going to open the application [left;500,200].'"
                       + "then once you do that the action will happen and another screenshot will be sent. from there you figure out where the pixels should go and you read your past memory to see whats the next step."
                       + "'good i've opened the application, now ill drag the mouse [leftdrag;400,200,400,800,1].'"
                       + "the action will be completed and another screenshot will be sent your way which shows that you've completed the task if you haven't you will correct yourself." 
                       + "To type a key or keys is this format [type;hello there!]"
                       + "additionally if you want to press multiple keys at once do [multiple;shift,win]."
                       + "shift defaults to left shift and win is the windows key."
                       + "if you want to hold a key do [hold;win] and ALWAYS type in your next response [release;win]."
                       + "if you want to hold mulitple keys do [multhold;w,space] for releasing multiple do [releasemultiple;w,space]"
                       + "you may also do single hotkeys such as space and enter via [multiple;space]"
                       + "additionally if you'd like to hover over something you may type [hover;x,y]"
                       + "use speech like 'try to' or 'attempt to' when referring to what you are going to do."
                       + "and, in the beginning, asses the screenshot, if you had earlier tried to click or hover something, to check if what you tried to do worked or not."
                       + "if it did not work say that clearly and concisely why so that you can adjust yourself. if you did so successfully also state that."
                       + "In most situations only do one action at a time, so that you may readjust your mouse if needed."
                       + "for more complicated tasks please include, in your output, your plan with future steps and thought processes so you may refer to them in dfuture outputs."
                       + "additionally when referring to coordinates OUTSIDE of actual action do NOT use square brackets []."
                       + "for example: 'im going to put the cursor at 12,100. [hover;12,100]' this is the correst response"
                       + "'i am going to put my cursor at [12,100]. [hover;12,100]' this is the incorrect response."
                       + "additionally never close the command prompt as it will kill you, you may minimize it though."
                       + "In your final response say you are done and type PURGE."
                       + "'perfect i finished my task. PURGE"
                       + "This is your current task, " + user_input
                       + "You have access to two types of memory, temporary and persistent. the latter of which you can edit any time"
                       + "temporary memory is the last 3 messages that you've sent, you access this every time you send a new output"
                       + "persistent, on the other hand, is something you manually edit."
                       + "you can add things to persistent memory by typing [persistent;this is a test]"
                       + "be aware that persistent memory is rewritten every time you edit it"
                       + "you should use persistent memory when you are planning for a long process."
                       + "for example if you need to add several events to a calender you would put in your output:"
                       + "[persistent;first i am going to add event 1, it must add it on dd/mm/yyyy and at 00:00. next i will do event...] etc."
                       + "then once you've recognized you've completed the first event you would include in your output"
                       + "[persistent;first event completed, reading the previous persistent memory i found the details to event 2, 3 (etc) now i am going to add event two, i will do 3 after that]."
                       + ". And This is your previous memory : "
                       + memory_context)
    
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                prompt_text
            ]
        )
        
        response = get_gemini_response(image_bytes, prompt_text)
    
        result_text = response.text
    
        # Save this new response into memory, if retention is enabled
        past_messages.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": result_text
        })
        save_memory(past_messages)
        
        do_action(result_text)
        
        s("done!")
        
        print("")
        print("")

        asyncio.run(main_go(result_text))
                
        print("")
        print("")
        
        time.sleep(.1)
        
        if"PURGE" in result_text:
            print("--")
            save_memory()
            break

while True:
    user_input = input("What would you like me to do?: ")
    
    print("--")
    
    main()

input()
