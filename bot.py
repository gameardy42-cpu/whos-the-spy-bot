import os
import random
from collections import Counter

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WORD_PAIRS = [
    ("pisang", "jeruk"),
    ("kapal", "pesawat"),
    ("gunung", "bukit"),
    ("buku", "majalah"),
    ("mangga", "alpukat"),
    ("rumah", "apartemen"),
    ("sepatu", "sandal"),
    ("sapi", "kambing"),
    ("mobil", "motor"),
    ("kucing", "anjing"),
]

STATE = {}


class GameSession:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = {}
        self.started = False
        self.spy_id = None
        self.civilian_word = None
        self.round = 0
        self.votes = {}

    def add_player(self, user):
        user_id = user.id
        if user_id in self.players:
            return False
        self.players[user_id] = {
            "name": user.full_name or user.first_name or "Player",
            "username": user.username,
        }
        return True

    def start_round(self):
        if len(self.players) < 3:
            return "Minimal 3 pemain untuk mulai game."

        self.round += 1
        self.spy_id = random.choice(list(self.players.keys()))
        chosen_pair = random.choice(WORD_PAIRS)
        self.civilian_word = random.choice(chosen_pair)
        self.votes = {}
        self.started = True

        message = []
        for user_id, info in self.players.items():
            if user_id == self.spy_id:
                message.append((user_id, "Kamu adalah SPY! Jangan kasih tahu kata rahasia. Sembunyikan diri dengan baik."))
            else:
                message.append((user_id, f"Kata rahasia kamu: {self.civilian_word}"))
        return message

    def vote(self, voter_id, target_id):
        if not self.started:
            return "Game belum dimulai."
        if voter_id not in self.players:
            return "Kamu belum terdaftar di game ini."
        if target_id not in self.players:
            return "Target vote harus dari pemain yang sudah join."

        self.votes[voter_id] = target_id

        if len(self.votes) < len(self.players):
            return f"Vote kamu sudah tercatat. Menunggu {len(self.players) - len(self.votes)} vote lagi."

        tally = Counter(self.votes.values())
        voted_target, _ = tally.most_common(1)[0]

        if voted_target == self.spy_id:
            spy_name = self.players[self.spy_id]["name"]
            self.started = False
            self.spy_id = None
            self.civilian_word = None
            self.votes = {}
            return f"✅ Tebakan benar! Spy adalah {spy_name}. Tim berhasil menang!"

        spy_name = self.players[self.spy_id]["name"]
        self.started = False
        self.spy_id = None
        self.civilian_word = None
        self.votes = {}
        return f"❌ Vote salah. Spy sebenarnya adalah {spy_name}."


def get_session(chat_id):
    if chat_id not in STATE:
        STATE[chat_id] = GameSession(chat_id)
    return STATE[chat_id]


def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(
        f"Halo {user.first_name}!\n"
        "Bot Who's the Spy siap membantu permainan di grup ini.\n\n"
        "Perintah:\n"
        "/newgame - mulai game baru\n"
        "/join - ikut game\n"
        "/status - lihat daftar pemain\n"
        "/startgame - mulai ronde\n"
        "/vote - reply pesan orang yang diduga spy lalu ketik /vote\n"
        "/help - lihat aturan"
    )


def new_game(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    STATE[chat_id] = GameSession(chat_id)
    update.message.reply_text("Game baru dibuat. Semua pemain silakan ketik /join")


def join_game(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    user = update.effective_user

    if session.add_player(user):
        update.message.reply_text(f"{user.first_name} berhasil join game.")
    else:
        update.message.reply_text(f"{user.first_name} sudah terdaftar sebelumnya.")


def status_game(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)

    if not session.players:
        update.message.reply_text("Belum ada pemain. Gunakan /join terlebih dahulu.")
        return

    names = [info["name"] for info in session.players.values()]
    text = "Daftar pemain:\n- " + "\n- ".join(names)
    if session.started and session.spy_id:
        text += f"\n\nRonde aktif: {session.round}."
    update.message.reply_text(text)


def start_game(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)

    if not session.players:
        update.message.reply_text("Belum ada pemain. Ketik /join dulu.")
        return

    if len(session.players) < 3:
        update.message.reply_text("Minimal 3 pemain untuk memulai round.")
        return

    result = session.start_round()
    if isinstance(result, str):
        update.message.reply_text(result)
        return

    update.message.reply_text(
        f"Ronde {session.round} dimulai! Spy sudah dipilih. Kata rahasia dikirim ke DM masing-masing pemain."
    )

    for user_id, message in result:
        try:
            context.bot.send_message(chat_id=user_id, text=message)
        except Exception:
            pass


def vote(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)

    if not session.started:
        update.message.reply_text("Belum ada ronde yang aktif.")
        return

    if not update.message.reply_to_message:
        update.message.reply_text("Balas pesan orang yang kamu duga sebagai spy, lalu ketik /vote.")
        return

    target_user = update.message.reply_to_message.from_user
    if target_user is None:
        update.message.reply_text("Target tidak valid.")
        return

    if target_user.id not in session.players:
        update.message.reply_text("Target vote harus merupakan pemain yang ikut game.")
        return

    result = session.vote(update.effective_user.id, target_user.id)
    update.message.reply_text(result)


def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Aturan singkat Who's the Spy:\n\n"
        "- Semua pemain mendapat kata rahasia yang sama kecuali 1 orang sebagai spy.\n"
        "- Spy tidak diberi kata rahasia, hanya tahu ia adalah spy.\n"
        "- Pada saat voting, balas pesan target lalu ketik /vote.\n"
        "- Jika vote tepat, tim menang; kalau tidak, spy menang.\n\n"
        "Perintah utama: /newgame /join /status /startgame /vote /help"
    )


def main():
    if not TOKEN:
        raise ValueError("Token Bot Telegram belum diatur. Isi TELEGRAM_BOT_TOKEN di file .env")

    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("newgame", new_game))
    dispatcher.add_handler(CommandHandler("join", join_game))
    dispatcher.add_handler(CommandHandler("status", status_game))
    dispatcher.add_handler(CommandHandler("startgame", start_game))
    dispatcher.add_handler(CommandHandler("vote", vote))
    dispatcher.add_handler(CommandHandler("help", help_command))

    print("Bot Who's the Spy sedang berjalan...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
