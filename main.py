import socket
import threading
import time
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table, TIMESTAMP
from sqlalchemy.orm import sessionmaker, scoped_session
import pg8000

DB_CONFIG = {
    'host': 'bguwkamcnruj1gcx01jy-postgresql.services.clever-cloud.com',
    'port': '50013',
    'database': 'bguwkamcnruj1gcx01jy',
    'user': 'uxxqrinwj2bgkymn9b5g',
    'password': 'kkZLO7HLDOB4AO3gUtO7mzNDUOMQjs'
}

DATABASE_URL = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
engine = create_engine(DATABASE_URL, echo=True)
metadata = MetaData()
Session = scoped_session(sessionmaker(bind=engine))

chat_messages = Table(
    'chat_messages', metadata,
    Column('id', Integer, primary_key=True),
    Column('message', String, nullable=False),
    Column('timestamp', TIMESTAMP, nullable=False)
)

metadata.create_all(engine)

# Server code remains the same
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('127.0.0.1', 12345))
    server_socket.listen(5)
    clients = []

    def handle_client(client_socket):
        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if message:
                    for client in clients:
                        if client != client_socket:
                            client.send(message.encode('utf-8'))
                else:
                    break
            except Exception as e:
                break
        client_socket.close()
        clients.remove(client_socket)

    while True:
        client_socket, addr = server_socket.accept()
        clients.append(client_socket)
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

class ChatDatabase:
    @staticmethod
    def insert_message(username, message):
        session = Session()
        try:
            timestamp = datetime.now()
            formatted_message = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {username}: {message}"
            new_message = {'message': formatted_message, 'timestamp': timestamp}
            stmt = chat_messages.insert().values(new_message)
            result = session.execute(stmt)
            session.commit()
            return result.inserted_primary_key[0]
        except Exception as e:
            print(f"Error inserting message: {e}")
            session.rollback()
        finally:
            session.close()

    @staticmethod
    def fetch_messages():
        session = Session()
        messages = []
        try:
            stmt = chat_messages.select()
            result = session.execute(stmt)
            messages = [(row[0], row[1]) for row in result]
        except Exception as e:
            print(f"Error fetching messages: {e}")
        finally:
            session.close()
        return messages

class ChatClient(BoxLayout):
    def __init__(self, **kwargs):
        super(ChatClient, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.username = None
        self.client_socket = None
        self.padding = dp(5)
        self.spacing = dp(5)
        Window.softinput_mode = "below_target"
        self.create_widgets()
        self.prompt_for_username()

    def create_widgets(self):
        chat_container = BoxLayout(orientation='vertical', size_hint_y=0.9)
        
        self.chat_area = TextInput(
            readonly=True,
            multiline=True,
            background_color=[0.95, 0.95, 0.95, 1],
            font_size=dp(14),
            padding=[dp(10), dp(10)]
        )
        chat_container.add_widget(self.chat_area)
        self.add_widget(chat_container)
        
        input_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(5),
            padding=[dp(5), dp(5)]
        )
        
        self.msg_input = TextInput(
            hint_text='Enter your name',
            multiline=False,
            size_hint_x=0.8,
            font_size=dp(14),
            padding=[dp(10), dp(5)],
            background_color=[1, 1, 1, 1]
        )
        self.msg_input.bind(on_text_validate=self.send_message)
        self.msg_input.bind(focus=self.on_focus)
        input_layout.add_widget(self.msg_input)
        
        self.send_button = Button(
            text='Confirm',
            size_hint_x=0.2,
            background_color=[0.3, 0.6, 1, 1],
            font_size=dp(14)
        )
        self.send_button.bind(on_press=self.send_message)
        input_layout.add_widget(self.send_button)
        self.add_widget(input_layout)

        self.send_button.disabled = False

    def prompt_for_username(self):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        self.username_input = TextInput(
            hint_text='Enter your name (min 3 characters)',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
            font_size=dp(14),
            padding=[dp(10), dp(5)]
        )
        self.username_input.bind(on_text_validate=lambda x: self.validate_username(None))
        content.add_widget(self.username_input)
        
        buttons = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        confirm_button = Button(
            text='Confirm',
            background_color=[0.3, 0.6, 1, 1]
        )
        confirm_button.bind(on_press=self.validate_username)
        buttons.add_widget(confirm_button)
        content.add_widget(buttons)
        
        self.popup = Popup(
            title='Enter Username',
            content=content,
            size_hint=(0.8, None),
            height=dp(150),
            auto_dismiss=False
        )
        self.popup.open()

    def validate_username(self, instance):
        username = self.username_input.text.strip()
        if len(username) >= 3:
            self.username = username
            self.send_button.disabled = False
            self.popup.dismiss()
            self.start_client()
            self.fetch_previous_messages()
        else:
            self.username_input.text = ''
            self.username_input.hint_text = 'Username must be at least 3 characters'

    def on_focus(self, instance, value):
        if value:
            Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.2)

    def scroll_to_bottom(self):
        self.chat_area.cursor = (0, len(self.chat_area.text))

    def start_client(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(('127.0.0.1', 12345))
            threading.Thread(target=self.receive_messages, daemon=True).start()
            Clock.schedule_interval(self.fetch_previous_messages, 5)
        except Exception as e:
            self.show_error_popup(f"Connection error: {e}")

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    Clock.schedule_once(lambda dt, msg=message: self.update_chat_area(msg))
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def fetch_previous_messages(self, dt):
        try:
            messages = ChatDatabase.fetch_messages()
            self.chat_area.text = ''
            for msg in messages:
                self.update_chat_area(msg[1])
        except Exception as e:
            self.show_error_popup(f"Error fetching messages: {e}")

    def send_message(self, instance=None):
        message = self.msg_input.text.strip()
        if message:
            if not self.username:
                self.username = message
                self.send_button.text = 'Send'
                self.msg_input.hint_text = 'Enter your message here'
                self.msg_input.text = ''
                self.start_client()
                self.fetch_previous_messages(0)
                return
            else:
                try:
                    ChatDatabase.insert_message(self.username, message)
                    self.client_socket.send(message.encode('utf-8'))
                    self.msg_input.text = ''
                    Clock.schedule_once(lambda dt: setattr(self.msg_input, 'focus', True), 0.1)
                except Exception as e:
                    self.show_error_popup(f"Error sending message: {e}")

    def update_chat_area(self, message):
        self.chat_area.text += f"{message}\n"
        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)

    def show_error_popup(self, error_message):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=error_message))
        button = Button(text='OK', size_hint_y=0.4)
        content.add_widget(button)
        popup = Popup(title='Error', content=content, size_hint=(0.8, 0.4))
        button.bind(on_press=popup.dismiss)
        popup.open()

class ChatApp(App):
    def build(self):
        return ChatClient()

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    ChatApp().run()
