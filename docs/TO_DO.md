# — Що зробити —

> Ось повний список дій, які потребують вашої участї.
> Вони згруповані за пріоритетом та логічним порядком виконання.

---

## 🔴 Критичні (блокують подальший прогрес)

### GitHub

| # | Дія | Деталі |
| --- | --- | --- |
| 1 | Створити приватний репозиторій на GitHub | `hermes/pulse-of-earth` (private) |
| 2 | Додати remote на репозиторій | `git remote add origin git@github.com:hermes/pulse-of-earth.git` |
| 3 | Запушити всі гілки | `git push origin master feat/staging-bootstrap feat/orchestrator-phase0` |
| 4 | Увімкнути branch protection на main | Settings → Branches → Add rule → main |
| 5 | Вимагати CI перед merge | "Require status checks to pass" → вибрати `ci.yml` jobs |
| 6 | Заборонити force push | "Require a pull request before merging" + "Allow force pushes: off" |
| 7 | Створити GitHub Environment: staging | Settings → Environments → New → staging |
| 8 | Додати секрети в staging environment | `STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY` |

### Cloudflare

| # | Дія | Деталі |
| --- | --- | --- |
| 9 | Додати DNS A-запис | `earthbit.staging.terrabits.org` → `157.180.125.174` (DNS only, без Proxy) |

---

## 🟡 Важливі (потрібні для повноцінної роботи)

### Telegram

| # | Дія | Деталі |
| --- | --- | --- |
| 10 | Створити Telegram бота (якщо немає) | Через @BotFather → `/newbot` |
| 11 | Надати токен бота | Зберегти для GitHub secrets |
| 12 | Надати Chat ID для staging alerts | Створити групу/канал, додати бота, отримати chat ID |

### Hetzner

| # | Дія | Деталі |
| --- | --- | --- |
| 13 | Перевірити Hetzner Firewall | Переконатися що дозволяє 22, 80, 443 ззовні |
| 14 | Налаштувати Private Network | З'єднати Hermes VPS (nbg1) ↔ Staging VPS (hel1) |
| 15 | Створити Object Storage бакет | Для PostgreSQL backupів |
| 16 | Надати S3 credentials | `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` |
| 17 | Надати ключ шифрування бэкапів | Випадковий пароль (32+ символів) |

### Staging Bootstrap

| # | Дія | Деталі |
| --- | --- | --- |
| 18 | Створити структуру директорій на staging | `sudo mkdir -p /opt/terrabits/{apps/pulse-of-earth,caddy,backups/{postgres,releases},scripts,shared/releases}` |
| 19 | Встановити власника | `sudo chown -R deploy:deploy /opt/terrabits` |
| 20 | Створити .env файл | `ENVIRONMENT=staging`, `LOG_LEVEL=INFO` |

### Linear

| # | Дія | Деталі |
| --- | --- | --- |
| 21 | Створити Linear workspace (якщо немає) | "TerraBits" |
| 22 | Створити проєкт "Pulse of Earth" | В середині workspace |
| 23 | Надати Linear API key | Settings → API → Personal API tokens |
| 24 | Створити labels | discovery, architecture, backend, frontend, devops, security, testing, documentation, low-risk, medium-risk, high-risk, blocked, needs-owner |

### Obsidian

| # | Дія | Детали |
| --- | --- | --- |
| 25 | Налаштувати Git-синхронізацію | Встановити Obsidian Git plugin або Syncthing |
| 26 | Зв'язати з репозиторієм | Відкрити `docs/obsidian/` як vault (або налаштувати Git sync) |

### Cloudflare (додатково)

| # | Дія | Деталі |
| --- | --- | --- |
| 27 | Надати Zone ID | Для terrabits.org |
| 28 | Надати API token | З правами Zone.DNS для автоматизації |
| 29 | Надати emails команди | Для Cloudflare Access allowlist |

---

## 🟢 Додатково (потім, за потреби)

| # | Дія | Деталі |
| --- | --- | --- |
| 30 | Вирішити з n8n | Self-hosted (окремий VPS) або n8n Cloud |
| 31 | Затвердити встановлення n8n | Якщо self-hosted |
| 32 | Створити production environment | GitHub Environment + secrets |
| 33 | Надати production chat ID | Для Telegram alerts |
| 34 | Розгорнути PostgreSQL контейнер | На staging |
| 35 | Перший deploy через CI | Запушити тег → CI зробить build → deploy |

---

## 📋 Порядок виконання (рекомендований)

```
День 1:  #1-9   (GitHub + Cloudflare DNS)
День 2:  #10-12 (Telegram) + #18-20 (Staging bootstrap)
День 3:  #13-17 (Hetzner) + #21-24 (Linear)
День 4:  #25-26 (Obsidian) + #34-35 (PostgreSQL + deploy)
День 5:  #27-29 (Cloudflare Access) + #30-33 (n8n + production)
```

---

## 📝 Примітки

- Після #1-3 (GitHub push) — я зможу запустити CI та перевірити пайплайн
- Після #7-8 (staging secrets) — я зможу налаштувати automated deploy
- Після #9 (DNS) — отримаю доступ до staging через домен
- Після #10-12 (Telegram) — отримуватиму сповіщення про деплої
- Після #15-17 (Object Storage) — налаштую PostgreSQL backups
- Після #21-24 (Linear) — синхронізую задачи з репозиторієм

**Після виконання критичних (#1-9) — напишіть мені, і я продовжу з наступними фазами автоматично.**
