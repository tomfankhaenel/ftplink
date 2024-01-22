from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import asyncio
import telegram
import os

bot_token = os.getenv("bot_token", "bot_token does not exist")
group_chat_id = os.getenv("group_chat_id", "group_chat_id does not exist")

class Telegram(FTPHandler):
    def on_file_received(self, file_path):
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            asyncio.run(telegram.Bot(bot_token).sendPhoto(chat_id=group_chat_id, photo=file_path))
        if file_path.lower().endswith(('.mp4')):
            asyncio.run(telegram.Bot(bot_token).sendVideo(chat_id=group_chat_id, video=file_path))


def create_ftp_server():
    # Create an authorizer with an 'anonymous' user without a password
    authorizer = DummyAuthorizer()
    authorizer.add_anonymous("/app/ftp", perm="elradfmw")
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
    create_ftp_server()