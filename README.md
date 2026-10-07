# Who's the Spy Telegram Bot

Bot Telegram untuk game Who's the Spy yang bisa dipakai di grup.

## Fitur
- /start
- /newgame
- /join
- /status
- /startgame
- /vote (reply ke pemain yang dituduh sebagai spy)
- /help

## Cara install
1. Buat bot Telegram lewat BotFather.
2. Salin token bot Anda.
3. Buat file `.env` dari contoh:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env` dan isi token Telegram.
5. Install dependency:
   ```bash
   pip install -r requirements.txt
   ```
6. Jalankan bot:
   ```bash
   python bot.py
   ```

## Cara main di grup
1. Masuk ke grup Telegram.
2. Ketik `/newgame`
3. Semua pemain ketik `/join`
4. Setelah cukup pemain, ketik `/startgame`
5. Bot akan mengirim kata rahasia ke tiap pemain via DM.
6. Saat ronde aktif, pemain bisa menuduh spy dengan cara reply pesan orang yang diduga lalu ketik `/vote`
7. Bot akan menghitung vote dan menentukan hasilnya.

## Catatan
- Minimal pemain: 3 orang
- Setiap ronde, satu orang menjadi spy.
- Civilian mendapat kata rahasia yang sama; spy tidak mendapat kata, hanya diberi tahu dia adalah spy.
