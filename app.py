import os
import json
import requests
from pypdf import PdfReader
from openai import OpenAI
import gradio as gr

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama3-8b-instruct"

PUSHOVER_TOKEN = os.environ.get("PUSHOVER_TOKEN")
PUSHOVER_USER = os.environ.get("PUSHOVER_USER")

client = OpenAI(api_key=OPENAI_API_KEY, base_url=BASE_URL)

def push(text):
    try:
        if not PUSHOVER_TOKEN or not PUSHOVER_USER:
            return
        requests.post(
            "https://api.pushover.net/1/messages.json",
            data={"token": PUSHOVER_TOKEN, "user": PUSHOVER_USER, "message": text},
            timeout=5
        )
    except:
        pass

def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"{name} | {email} | {notes}")
    return {"status": "ok"}

def record_unknown_question(question):
    push(f"{question}")
    return {"status": "ok"}

globals()["record_user_details"] = record_user_details
globals()["record_unknown_question"] = record_unknown_question

tools = [
    {
        "type": "function",
        "function": {
            "name": "record_user_details",
            "description": "Record user's interest and email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "name": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_unknown_question",
            "description": "Record unknown question.",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"]
            }
        }
    }
]

class Me:
    def __init__(self):
        self.name = "Ayush Tyagi"
        self.summary = ""
        self.linkedin = ""

        if os.path.exists("me/summary.txt"):
            self.summary = open("me/summary.txt", "r", encoding="utf-8").read()

        pdf = "me/Ayush_linkdin.pdf"
        if os.path.exists(pdf):
            text = []
            reader = PdfReader(pdf)
            for p in reader.pages:
                t = p.extract_text()
                if t:
                    text.append(t)
            self.linkedin = "\n\n".join(text)

    def system_prompt(self):
        return f"""
You are acting as {self.name}. You answer questions about his background and skills.
If unsure, call record_unknown_question.
If user is interested, ask for email and call record_user_details.

Summary:
{self.summary}

LinkedIn:
{self.linkedin}
"""

    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}]

        for user_msg, bot_msg in history:
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            if bot_msg:
                messages.append({"role": "assistant", "content": bot_msg})

        messages.append({"role": "user", "content": message})

        while True:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=500
            )

            choice = response.choices[0]
            msg = choice.message
            finish = choice.finish_reason

            if finish == "tool_calls":
                for tool_call in msg.tool_calls:
                    func = tool_call.function
                    name = func.name
                    args = json.loads(func.arguments)
                    result = globals()[name](**args)
                    messages.append({"role": "tool", "content": json.dumps(result)})
                continue

            return msg.content


me = Me()

gr.ChatInterface(me.chat, type="messages").launch()
