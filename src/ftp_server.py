from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import asyncio
import telegram
import os
import time
from telegram.error import RetryAfter, TimedOut
import requests
import json
from requests.exceptions import Timeout, ConnectionError, RequestException

detection_endpoint = os.getenv("detection_endpoint", "")
allowed_objects = set(o.strip().lower() for o in os.getenv("allowed_objects", "person").split(","))
confidence_level = float(os.getenv("confidence_level", "0.65"))
bot_token = os.getenv("bot_token", "bot_token does not exist")
group_chat_id = os.getenv("group_chat_id", "group_chat_id does not exist")
homedir = os.getenv("homedir", "/app/ftp")
resenddir = os.getenv("resenddir", "/app/ftp/resend")

class Telegram(FTPHandler):
    def on_file_received(self, file_path):
        if detection_endpoint:
            if is_allowed_by_detection(file_path):
                send_to_telegram(file_path)
            else:
                print(f"File {file_path} does not contain allowed objects. Deleting.")
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting filtered file: {e}")
        else:
            # No detection filtering, always send
            send_to_telegram(file_path)


def is_allowed_by_detection(file_path):
    try:
        with open(file_path, 'rb') as f:
            files = {'image': f}
            response = requests.post(detection_endpoint, files=files, timeout=120)

            if response.status_code != 200:
                error_msg = f"Detection endpoint returned status {response.status_code}: {response.text}"
                print(error_msg)
                notify_telegram_error(error_msg)
                send_to_telegram(file_path)
                return False

            try:
                detections = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON from detection endpoint: {e}"
                print(error_msg)
                notify_telegram_error(error_msg)
                send_to_telegram(file_path)
                return False

            for detection in detections:
                for obj in detection.get("objects", []):
                    name = obj.get("name", "").lower()
                    confidence = obj.get("confidence", 0.0)
                    if name in allowed_objects and confidence >= confidence_level:
                        print(f"Allowed object detected: {name} (confidence: {confidence:.2f})")
                        print(f"DEBUG: {detections}")
                        return True

            print("No allowed objects detected.")
            print(f"DEBUG: {detections}")
            return False

    except (Timeout, ConnectionError) as e:
        error_msg = f"Network error contacting detection endpoint: {type(e).__name__} - {e}"
        print(error_msg)
        notify_telegram_error(error_msg)
        send_to_telegram(file_path)
        return False
    except RequestException as e:
        error_msg = f"Request error contacting detection endpoint: {e}"
        print(error_msg)
        notify_telegram_error(error_msg)
        send_to_telegram(file_path)
        return False
    except Exception as e:
        error_msg = f"Unexpected error during detection: {e}"
        print(error_msg)
        notify_telegram_error(error_msg)
        send_to_telegram(file_path)
        return False

def notify_telegram_error(message):
    try:
        asyncio.run(telegram.Bot(bot_token).send_message(chat_id=group_chat_id, text=f"❗ Detection error:\n{message}"))
    except Exception as e:
        print(f"Failed to send error notification to Telegram: {e}")

def send_to_telegram(file_path):
    try:
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            asyncio.run(telegram.Bot(bot_token).sendPhoto(chat_id=group_chat_id, photo=file_path)) # Send photo via Telegram
            os.remove(file_path)  # Delete the file after successful send
        elif file_path.lower().endswith(('.mp4')):
            asyncio.run(telegram.Bot(bot_token).sendVideo(chat_id=group_chat_id, video=file_path)) # Send video via Telegram
            os.remove(file_path)  # Delete the file after successful send
    except RetryAfter as e:
        print(f"Flood control exceeded. Retrying in {e.retry_after} seconds...")
        time.sleep(e.retry_after)
        send_to_telegram(file_path)  # Retry after delay
    except TimedOut:
        print("Telegram request timed out. Retrying in 10 seconds...")
        time.sleep(10)
        send_to_telegram(file_path)
    except Exception as e:
        print(f"Error sending file to Telegram, marking file for resend: {e}")
        base, extension = os.path.splitext(file_path)
        try:
            os.rename(file_path, (resenddir + "/" + str(time.time()) + extension))
        except Exception as e:
            print(f"Error renaming the file for resend: {e}")


def send_old_files(): # send files in resendirdir on startup; a failed retry will create a new file in this folder with the same content
    for filename in os.listdir(resenddir):
        print("Sending leftover file " + filename)
        send_to_telegram((resenddir + "/" + filename))


def create_ftp_server():
    # Create an authorizer with an 'anonymous' user without a password
    authorizer = DummyAuthorizer()
    authorizer.add_anonymous(homedir, perm="elradfmw")
    # Instantiate an FTP handler with the provided authorizer
    handler = Telegram
    handler.authorizer = authorizer

    # Passive mode settings
    handler.passive_ports = range(60000, 60010)  # Set a range of passive ports

    # Create the FTP server on 0.0.0.0:21
    server = FTPServer(("0.0.0.0", 2121), handler)

    # Start the FTP server
    server.serve_forever()


if __name__ == "__main__":
    send_old_files()
    create_ftp_server()
