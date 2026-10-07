import os
import random
from collections import Counter
from dataclasses import dataclass, field

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

GAME_WORDS = [
    ("pisang", "jeruk"),
    ("kapal", "pesawat"),
    ("gunung", "bukit"),
    ("rumah", "apartemen"),
    ("mobil", "motor"),
    ("sapi", "kambing"),
    ("buku", "majalah"),
    ("mangga", "alpukat"),
    ("sepatu", "sandal"),
    ("kucing", "anjing"),
    ("kertas", "plastik"),
    ("telepon", "tablet"),
    ("kota", "desa"),
    ("sungai", "danau"),
    ("kolam", "pantai"),
    ("kereta", "kapal"),
    ("baju", "jaket"),
    ("taman", "hutan"),
    ("lagu", "musik"),
    ("cincin", "kalung"),
]

GAME_STATE = {}


@dataclass
class Player:
    user_id: int
    first_name: str
    username: str | None = None


@dataclass
class GameSession:
    chat_id: int
    players: dict[int, Player] = field(default_factory=dict)
    round_started: bool = False
    spy_id: int | None = None
    secret_word: str | None = None
    round_number: int = 0
    votes: dict[int, int] = field(default_factory=dict)

    def add_player(self, user) -> bool:
        if user.id in self.players:
            return False
        self.players[user.id] = Player(
            user_id=user.id,
            first_name=user.first_name or user.full_name or "Player",
            username=user.username,
        )
        return True

    def reset_round(self):
        self.round_started = False
        self.spy_id = None
        self.secret_word = None
        self.votes = {}

    def start_round(self):
        if len(self.players) < 3:
            return "Minimal 3 pemain untuk memulai ronde."

        self.round_number += 1
        self.votes = {}
        self.spy_id = random.choice(list(self.players.keys()))
        selected_pair = random.choice(GAME_WORDS)
        self.secret_word = random.choice(selected_pair)
        self.round_started = True

        messages = []
        for user_id, player in self.players.items():
            if user_id == self.spy_id:
                messages.append((user_id, "Kamu adalah SPY! Jangan kasih tahu kata. Mainkan strategi dan sembunyikan diri dengan baik."))
            else:
                messages.append((user_id, f"Kata rahasia kamu: {self.secret_word}"))
        return messages

    def cast_vote(self, voter_id: int, target_id: int):
        if not self.round_started:
            return "Ronde belum dimulai."
        if voter_id not in self.players:
            return "Kamu belum terdaftar di game ini."
        if target_id not in self.players:
            return "Target vote harus pemain yang ikut game."

        self.votes[voter_id] = target_id
        if len(self.votes) < len(self.players):
            remaining = len(self.players) - len(self.votes)
            return f"Vote kamu sudah tercatat. Masih ada {remaining} vote yang belum masuk."

        tally = Counter(self.votes.values())
        guessed_spy_id, _ = tally.most_common(1)[0]

        result_lines = []
        for player_id, player in self.players.items():
            target_name = self.players.get(guessed_spy_id).first_name if guessed_spy_id in self.players else "?"
            result_lines.append(f"{player.first_name}: {self.players[voter_id].first_name if voter_id in self.players else '??'} voted {target_name}")

        if guessed_spy_id == self.spy_id:
            spy_name = self.players[self.spy_id].first_name
            self.reset_round()
            return f"✅ Vote benar! Spy adalah {spy_name}. Tim menang."

        spy_name = self.players[self.spy_id].first_name
        self.reset_round()
        return f"❌ Vote salah. Spy sebenarnya adalah {spy_name}. Tim spy menang."


def get_session(chat_id: int) -> GameSession:
    if chat_id not in GAME_STATE:
        GAME_STATE[chat_id] = GameSession(chat_id=chat_id)
    return GAME_STATE[chat_id]


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Halo {user.first_name}! 👋\n\n"
        "Saya bot Who's the Spy.\n\n"
        "Perintah utama:\n"
        "/newgame - buat room baru\n"
        "/join - ikut game\n"
        "/status - lihat pemain\n"
        "/startgame - mulai ronde\n"
        "/vote - vote spy (balas pesan target lalu ketik /vote)\n"
        "/endgame - reset game\n"
        "/help - aturan permainan"
    )


async def cmd_newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    GAME_STATE[chat_id] = GameSession(chat_id=chat_id)
    await update.message.reply_text(
        "🆕 Game baru dibuat.\nSemua pemain bisa ketik /join untuk ikut.\n"
        "Setelah cukup pemain, ketik /startgame untuk mulai ronde."
    )


async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    user = update.effective_user

    if session.add_player(user):
        await update.message.reply_text(f"✅ {user.first_name} berhasil join game.")
    else:
        await update.message.reply_text(f"ℹ️ {user.first_name} sudah terdaftar di game ini.")


async def cmd_endgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in GAME_STATE:
        GAME_STATE[chat_id] = GameSession(chat_id=chat_id)
        await update.message.reply_text("🛑 Game direset. Semua pemain dibersihkan.")
    else:
        await update.message.reply_text("Belum ada game yang aktif.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)

    if not session.players:
        await update.message.reply_text("Belum ada pemain. Ketik /join untuk ikut.")
        return

    lines = ["📋 Daftar pemain:"]
    for player in session.players.values():
        name = player.username or player.first_name
        lines.append(f"- {player.first_name} (@{name if player.username else 'private'})")

    if session.round_started:
        lines.append(f"\n🔹 Ronde aktif: {session.round_number}")
        spy_name = session.players[session.spy_id].first_name if session.spy_id in session.players else "?"
        lines.append(f"🔹 Spy saat ini: {spy_name}")

    await update.message.reply_text("\n".join(lines))


async def cmd_startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)

    if len(session.players) < 3:
        await update.message.reply_text("⚠️ Minimal 3 pemain agar game bisa dimulai.")
        return

    if session.round_started:
        await update.message.reply_text("⚠️ Ronde masih aktif. Tunggu hingga vote selesai.")
        return

    result = session.start_round()
    if isinstance(result, str):
        await update.message.reply_text(result)
        return

    await update.message.reply_text(
        f"🎮 Ronde {session.round_number} dimulai!\n"
        "Semua kata rahasia sudah dikirim melalui DM."
    )

    for user_id, message in result:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception:
            await update.message.reply_text(
                f"⚠️ Tidak bisa mengirim DM ke user_id {user_id}. Pastikan bot sudah bisa DM ke player itu."
            )


async def cmd_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)

    if not session.round_started:
        await update.message.reply_text("🟡 Belum ada ronde aktif. Ketik /startgame dulu.")
        return

    target_user = None

    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        candidate = context.args[0]
        candidate = candidate.replace("@", "")
        for player in session.players.values():
            if player.username and player.username.lower() == candidate.lower():
                target_user = update.effective_user
                break
        if target_user is None:
            for player in session.players.values():
                if player.first_name.lower() == candidate.lower():
                    target_user = update.effective_user
                    break

    if not target_user:
        await update.message.reply_text(
            "Balas pesan orang yang diduga spy, lalu ketik /vote\n"
            "Atau ketik /vote @username"
        )
        return

    target_id = target_user.id
    if target_id not in session.players:
        await update.message.reply_text("Target vote harus pemain yang ikut game.")
        return

    result = session.cast_vote(update.effective_user.id, target_id)
    await update.message.reply_text(result)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Aturan Who's the Spy:\n\n"
        "- Semua pemain ikut room yang sama.\n"
        "- Salah satu pemain dipilih sebagai SPY.\n"
        "- Semua pemain lain mendapat kata rahasia yang sama.\n"
        "- Spy tidak tahu kata sebenarnya dan harus menyamar.\n"
        "- Saat voting, pemain menebak siapa spy dengan /vote.\n"
        "- Jika mayoritas menebak benar, tim civil menang.\n"
        "- Jika tebakannya salah, spy menang.\n\n"
        "Perintah:\n"
        "/newgame\n"
        "/join\n"
        "/status\n"
        "/startgame\n"
        "/vote\n"
        "/endgame\n"
        "/help"
    )


async def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN belum diisi di file .env")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("newgame", cmd_newgame))
    app.add_handler(CommandHandler("join", cmd_join))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("startgame", cmd_startgame))
    app.add_handler(CommandHandler("vote", cmd_vote))
    app.add_handler(CommandHandler("endgame", cmd_endgame))
    app.add_handler(CommandHandler("help", cmd_help))

    print("Bot Who's the Spy sedang berjalan...")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

