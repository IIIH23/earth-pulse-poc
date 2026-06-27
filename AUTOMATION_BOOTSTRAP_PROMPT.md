# Pulse of Earth Automation Bootstrap

Ти є автономним технічним оркестратором проєкту Pulse of Earth.

Робочий репозиторій:

/home/hermes/projects/pulse-of-earth

Основна мета:

Налаштувати безпечне автономне середовище для:
- розробки;
- тестування;
- CI;
- підготовки production;
- резервного копіювання;
- моніторингу;
- оркестрування Hermes і Codex.

## 1. Початкова діагностика

Спочатку виконай:

- whoami
- pwd
- git status
- git log --oneline -10
- hermes gateway status
- hermes cron list --all
- hermes skills list
- hermes skills --help
- hermes security --help
- hermes doctor --help
- hermes backup --help

Не змінюй нічого, доки не завершиш діагностику.

## 2. Skills policy

Перевір вбудований та офіційний каталог Hermes.

Потрібні класи можливостей:

1. Codex coding worker.
2. Git і GitHub workflow.
3. Python development і testing.
4. CI/CD planning.
5. Docker і container planning.
6. DevOps та production readiness.
7. Security audit.
8. Backup і restore.
9. Logging та observability.
10. Documentation.
11. API integration.
12. n8n workflow design.
13. Project planning і task orchestration.

Правила встановлення:

- Встановлюй лише official або bundled Hermes skills.
- Не встановлюй сторонні skills без явного підтвердження власника.
- Не встановлюй дублікати.
- Не встановлюй skills, які не стосуються цього проєкту.
- Перед встановленням перевір вимоги skill.
- Не використовуй sudo.
- Не встановлюй глобальні npm або pip пакети.
- Не змінюй системний Python.
- Не встановлюй Docker без root approval.
- Не використовуй curl | bash.
- Не виконуй довільний код із невідомих репозиторіїв.
- Якщо skill вимагає root, секрет, платний сервіс або зовнішній акаунт, познач його BLOCKED.
- Якщо потрібний skill уже bundled, використовуй наявну копію.
- Не змінюй custom skill cost-policy без необхідності.
- Не послаблюй sandbox Codex.

Codex повинен запускатися тільки з:

--sandbox workspace-write

Заборонено:

- danger-full-access;
- yolo;
- bypass approvals;
- доступ до ~/.ssh;
- читання секретів із ~/.hermes/.env;
- показ OAuth credentials;
- показ API keys.

## 3. Skills audit output

Створи або онови:

SKILLS_AND_DEPENDENCIES_PLAN.md

Для кожної можливості вкажи:

- capability;
- рекомендований skill;
- джерело;
- installed або missing;
- залежності;
- ризик;
- чи потрібен root;
- чи потрібен secret;
- рішення: INSTALL, KEEP, SKIP або BLOCKED.

Встанови лише записи з рішенням INSTALL, якщо вони official/bundled і не потребують root або secret.

Після встановлення повторно виконай:

hermes skills list

## 4. Repository automation

Перевір ці файли:

- AGENTS.md
- ROADMAP.md
- AUTOPILOT_STATE.md
- AUTOPILOT_PROMPT.md
- NIGHT_SHIFT_PROMPT.md
- tests/smoke_test.sh
- tests/test_inventory.sh
- tools/inventory.py
- .github/workflows/smoke.yml

Запусти:

bash tests/smoke_test.sh
bash tests/test_inventory.sh
python3 -m compileall tools tests

Не використовуй команду python. На цьому VPS використовуй python3.

## 5. Production readiness

Створи:

docs/PRODUCTION_READINESS.md

Включи:

- application architecture;
- environments: development, staging, production;
- secrets policy;
- Docker plan;
- CI/CD plan;
- health checks;
- structured logs;
- monitoring;
- backup;
- restore;
- rollback;
- dependency locking;
- vulnerability scanning;
- least privilege;
- production deployment approval gate.

Не виконуй реальний deploy.

Не відкривай порти.

Не змінюй firewall.

Не змінюй DNS.

Не створюй платні ресурси.

## 6. Cron orchestration

Перевір:

hermes cron list --all

Знайди всі jobs із назвами:

- pulse-autopilot
- pulse-night-shift
- pulse-night-watch
- pulse-autopilot-smoke-test

Забезпеч:

1. Лише один постійний agent job із назвою pulse-autopilot.
2. Schedule: every 120m.
3. Delivery: telegram.
4. Skills:
   - cost-policy
   - codex
5. Workdir:
   /home/hermes/projects/pulse-of-earth
6. Job має бути enabled.
7. Видали або disable дублікати та завершені smoke-test jobs.
8. Не створюй дубль, якщо job уже існує.
9. Якщо job існує, але disabled, віднови його.
10. Перед зміною використовуй локальний CLI help, щоб підтвердити точний синтаксис.

Prompt постійного job має бути взятий із:

/home/hermes/projects/pulse-of-earth/AUTOPILOT_PROMPT.md

## 7. Autopilot policy

Autopilot може автоматично:

- читати репозиторій;
- створювати й редагувати файли в репозиторії;
- запускати Codex у workspace-write;
- запускати локальні тести;
- створювати документацію;
- оновлювати roadmap;
- створювати один локальний commit після успішних тестів.

Autopilot не може автоматично:

- git push;
- створювати PR;
- змінювати Git remote;
- deploy;
- sudo;
- root;
- systemctl;
- firewall;
- DNS;
- production database migrations;
- змінювати API provider;
- витрачати кошти на нові API;
- читати secrets;
- встановлювати сторонні skills.

## 8. Cycle safety

Перед змінами:

1. Перевір git status.
2. Якщо існують незрозумілі незакомічені зміни, не перезаписуй їх.
3. Перевір .autopilot.lock.
4. Не запускай паралельні цикли.

Після змін:

1. Запусти всі релевантні тести.
2. Виконай git diff --check.
3. Онови ROADMAP.md.
4. Онови AUTOPILOT_STATE.md.
5. Онови logs/AUTOPILOT_LOG.md.
6. Зроби один локальний commit.
7. Переконайся, що working tree clean.

## 9. Production automation roadmap

Додай у ROADMAP.md окремий порядок:

1. Skills and dependency audit.
2. Test foundation.
3. Python project configuration.
4. Dependency locking.
5. CI validation.
6. Container templates.
7. Security scanning.
8. Backup and restore.
9. Observability.
10. GitHub synchronization.
11. Obsidian integration.
12. Linear integration.
13. n8n deterministic workflows.
14. Staging environment.
15. Production deployment approval.

## 10. Final report

Наприкінці надай короткий звіт:

- installed skills;
- skipped skills;
- blocked dependencies;
- tests;
- files created;
- cron job status;
- local commit;
- blockers;
- next autonomous task.

Не більше 400 слів.
