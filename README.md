# curry

Bot de Telegram desplegable en Railway.

## Variables en Railway

Configura estas variables en el servicio:

```env
BOT_TOKEN=token_del_bot
CURRY_GROUP_ID=0
CURRY_GROUP_INVITE_URL=https://t.me/Curry_comprobantebot
WEBHOOK_PATH=telegram-webhook
```

`BOT_TOKEN` no debe subirse a GitHub. Cambialo solo desde Railway.

Si Railway tiene un dominio publico, el bot usa webhook automaticamente con
`RAILWAY_PUBLIC_DOMAIN`. Tambien puedes fijar `WEBHOOK_URL` manualmente.

## Start command

Railway usa:

```bash
python main.py
```
