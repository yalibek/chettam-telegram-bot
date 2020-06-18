# Telegram bot for Chettam guys

Bot is used to book a time slot for a CS:GO game.

### Development

1. Clone this repo.
1. Sign-up to [Heroku](https://www.heroku.com/) and request access to the [hosted app](https://dashboard.heroku.com/apps/chettam-telegram-bot).
1. Create your own dev bot using [@BotFather](https://t.me/BotFather) in telegram.
1. Store your dev bot's token in a `TOKEN_DEBUG` env var.
1. Connect to dev DB (see [Database](#database) section).
1. Test your code with debug mode:
    ```bash
    python3 bot.py --debug
    ```
1. Push your changes and create MR.
1. Wait for MR approval.

### Deploy

When your branch is merged into master it will be automatically deployed.

### Database

- Dev - use either dev PostgreSQL db (get `HEROKU_POSTGRESQL_COPPER_URL` env var from Heroku) or any other local db (SQLite for example)
- Prod - PostgreSQL (Heroku built-in)

### Guidelines

- Refactoring is welcomed.
- Format your code using [Black](https://pypi.org/project/black/) before commiting:
    ```bash
    black .
    ```
- Do the right thing.
- Move fast and break things.
