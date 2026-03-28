# Telegram "Content by Code" Bot (aiogram v3)

Ushbu bot foydalanuvchidan kod qabul qiladi va admin avvaldan saqlagan `video` yoki `document` ni yuboradi.
Kontent yuborishdan oldin majburiy kanal(lar)ga obuna tekshiradi.

## Imkoniyatlar

- Python 3.11+ va `aiogram v3` (async)
- SQLite (`aiosqlite`) bilan oddiy va tez ishga tushadi
- Majburiy obuna: public va private kanallarni qo'llab-quvvatlaydi
- Admin buyruqlari:
  - `/add <KOD>`: kodga media biriktirish
  - `/del <KOD>`: kodni o'chirish
  - `/info <KOD>`: kod bo'yicha ma'lumot
  - `/ch_add <chat_id | @username>`: majburiy kanal qo'shish
  - `/ch_del <chat_id>`: kanal o'chirish
  - `/ch_list`: kanallar ro'yxati
- Anti-spam: oddiy rate-limit (`1 request / 2 sec` default)

## 1) Bot token olish

1. Telegram’da `@BotFather` ga kiring.
2. `/newbot` orqali bot yarating.
3. Berilgan tokenni oling.

## 2) `.env` tayyorlash

```bash
cp .env.example .env
```

`.env` faylni to'ldiring:

```env
BOT_TOKEN=...
ADMINS=111111111,222222222
DB_PATH=data/bot.db
RATE_LIMIT_SECONDS=2
```

`ADMINS` ichida admin Telegram user_id lar bo'lishi shart.
`DB_PATH` nisbiy bo'lsa, loyiha papkasi ichidan olinadi.

## 3) Lokal ishga tushirish

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## 4) Docker orqali ishga tushirish

Loyihada tayyor `Dockerfile` va `docker-compose.yml` bor.

```bash
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f bot
```

Muhim:

- Bot `polling` rejimida ishlaydi, shu sabab odatda HTTP port ochish kerak emas.
- Docker Compose ichida `DB_PATH=data/bot.db` ishlatiladi va DB `bot_data` volume ichida saqlanadi.
- Konteyner restart bo'lsa ham SQLite ma'lumotlari saqlanib qoladi.

Foydali buyruqlar:

```bash
docker compose ps
docker compose logs -f --tail=200 bot
docker compose restart bot
docker compose down
```

## 5) Hetzner serverga deploy qilish

Quyidagi misol Ubuntu server uchun:

1. Hetzner Cloud ichida server yarating va SSH bilan kiring.
2. Docker Engine va Compose plugin o'rnating.
3. Loyihani serverga ko'chiring.
4. `.env` ni to'ldiring.
5. Botni konteynerda ishga tushiring.

Docker o'rnatish (Ubuntu):

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

Loyihani serverga tayyorlash:

```bash
cp .env.example .env
nano .env
docker compose up -d --build
```

Yangilash:

```bash
docker compose down
docker compose up -d --build
```

Eslatma:

- Agar `ufw` ishlatsangiz, bu bot uchun qo'shimcha port ochish shart emas.
- Agar loyihani Git orqali olib borsangiz, `.env` ni repo ichiga commit qilmang.
- DB volume ichida saqlanadi, shuning uchun konteynerni qayta yaratish ma'lumotni o'chirmaydi.

## 6) Kanal sozlamasi (majburiy obuna)

Muhim:

- Botni majburiy kanallarga qo'shing.
- Botga kanal a'zolarini ko'rish huquqi kerak (`administrator` qilib qo'ying).
- Private kanal uchun odatda `chat_id` bilan qo'shiladi (`-100...`).

Admin bot ichida:

- Eng osoni: kanal postini botga shunchaki `forward` qiling, bot "qo'shaymi?" deb so'raydi
- `/ch_add @kanal_username`
- yoki `/ch_add -1001234567890`
- yoki shunchaki `/ch_add` yuborib, kanal postini botga `forward` qiling
- `/ch_list` bilan tekshiring.

## 7) Kontent qo'shish

1. Admin `/add 1024` yuboradi.
2. Bot: "video yoki dokument yuboring" deydi.
3. Admin video/document yuboradi.
4. Bot kod saqlanganini tasdiqlaydi.

Tekshirish:

- `/info 1024`
- `/del 1024`

## 8) Eng oson test (5 daqiqalik checklist)

1. Bitta test kanal yarating (yoki bor kanalni ishlating), botni o'sha kanalga `admin` qiling.
2. Botni ishga tushiring: `python -m app.main` yoki `docker compose up -d`
3. Admin akkauntdan:
   - `/ch_add @kanal_username` (yoki private bo'lsa `/ch_add -100...`)
   - `/add 1024` yuboring
   - keyin video yoki document yuboring
4. Ikkinchi oddiy user akkauntdan:
   - botga `/start`
   - `1024` yuboring
   - agar kanalga a'zo bo'lmasa, obuna xabari + `✅ Obuna bo'ldim` chiqadi
5. O'sha userni kanalga qo'shib, tugmani bosing:
   - endi kontent kelishi kerak.

Tez tekshiruv buyruqlari (`sqlite3` o'rnatilgan bo'lsa):

```bash
sqlite3 data/bot.db ".tables"
sqlite3 data/bot.db "SELECT code,file_type,created_at FROM contents;"
sqlite3 data/bot.db "SELECT chat_id,title,username FROM channels;"
```

## Foydalanuvchi oqimi

- `/start` -> yo'riqnoma
- Oddiy matn sifatida kod yuboradi (masalan `1024`)
- Agar obuna bo'lmagan bo'lsa: kanallar uchun inline tugmalar + `✅ Obunani tekshirish`
- Agar obuna bo'lsa: saqlangan media yuboriladi
- Kod topilmasa: `Kod topilmadi`

## Eslatma

- Bot token va maxfiy ma'lumotlarni log qilmaydi.
- Agar `get_chat_member` xato bersa (huquq yoki bot kanalda yo'qligi), bot xavfsizlik uchun obuna tasdiqlamaydi.
- Kod formati: `1-64` belgi, faqat harf/raqam hamda `-` va `_`.
