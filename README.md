# Telegram bot for Chettam guys 🔫

Bot is used to book a time slot for a CS:GO game.

### Development

1. Clone the repo and request access to contribute.
1. Sign-up to [Heroku](https://www.heroku.com/) and request access to the [hosted app](https://dashboard.heroku.com/apps/chettam-telegram-bot).
1. Dev bot:
    - Create your own dev bot using [@BotFather](https://t.me/BotFather) in telegram.
    - Store your bot's token as a `TOKEN` env var.
1. Dev DB:
    - Get `HEROKU_POSTGRESQL_COPPER_URL` url from [Heroku app settings](https://dashboard.heroku.com/apps/chettam-telegram-bot/settings).
    - Store it as `DATABASE_URL` env var.
1. Dev Sentry (optional):
    - Get `SENTRY_DSN_DEBUG` token from [Heroku app settings](https://dashboard.heroku.com/apps/chettam-telegram-bot/settings).
    - Store it as `SENTRY_DSN` env var.
1. Set `DEBUG` env var to "True" for debug mode and run the code:
    ```bash
    python3.7 bot.py
    ```
1. Push your changes, create MR and wait for MR approval.

### Deploy

When your branch is merged into master it will be automatically deployed.

### Guidelines

- Refactoring is welcomed.
- Format your code using [Black](https://pypi.org/project/black/) before commiting:
    ```bash
    black .
    ```
- Do the right thing.
- Move fast and break things.
