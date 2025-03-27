from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import asyncio
import telegram
import os
import time


bot_token = os.getenv("bot_token", "bot_token does not exist")
group_chat_id = os.getenv("group_chat_id", "group_chat_id does not exist")
homedir = os.getenv("homedir", "/app/ftp")
resenddir = os.getenv("resenddir", "/app/ftp/resend")


class Telegram(FTPHandler):
    def on_file_received(self, file_path): # only if ftp server receives a file we will trigger a potential telegram notification
        send_to_telegram(file_path)


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
        await asyncio.sleep(e.retry_after)
        await send_to_telegram(file_path)  # Retry after delay
    except TimedOut:
        print("Telegram request timed out. Retrying in 10 seconds...")
        await asyncio.sleep(10)
        await send_to_telegram(file_path)
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
