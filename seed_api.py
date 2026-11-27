"""
Скрипт быстрого заполнения API тестовыми данными (только стандартная библиотека Python).
Запуск:
    python seed_api.py
    python seed_api.py --url http://127.0.0.1:8000 --date 2026-11-27
"""
import argparse
import datetime as dt
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request


def request_json(method: str, url: str, data=None, token: str | None = None, form: bool = False):
    headers = {}
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw
        return err.code, detail


def main():
    parser = argparse.ArgumentParser(description="Быстрое заполнение API тестовыми данными.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Базовый URL сервера")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="Дата для плана YYYY-MM-DD")
    parser.add_argument("--email", default=os.getenv("SEED_EMAIL", ""), help="Email пользователя")
    parser.add_argument("--password", default=os.getenv("SEED_PASSWORD", ""), help="Пароль (>= 8 символов)")
    parser.add_argument("--chronotype", default="owl", choices=["lark", "owl", "pigeon"])
    args = parser.parse_args()

    base = args.url.rstrip("/")
    email = args.email or f"demo_{secrets.token_hex(3)}@example.com"
    password = args.password or secrets.token_urlsafe(10)

    print(f"1. Регистрация пользователя {email} ...")
    code, reg = request_json(
        "POST",
        f"{base}/api/v1/auth/register",
        {
            "name": "Алексей",
            "email": email,
            "password": password,
            "birth_date": "2006-05-01",
            "chronotype": args.chronotype,
        },
    )

    if code == 409:
        print("   Пользователь уже существует, выполняю вход...")
        code, login = request_json(
            "POST",
            f"{base}/api/v1/auth/login",
            {"username": email, "password": password},
            form=True,
        )
        if code != 200:
            print(f"   Ошибка входа ({code}): {login}")
            sys.exit(1)
        token = login["access_token"]
    elif code == 201:
        token = reg["access_token"]
    else:
        print(f"   Ошибка регистрации ({code}): {reg}")
        sys.exit(1)

    sample_tasks = [
        {
            "title": "Написать курсовую главу",
            "type": "intellectual",
            "duration_minutes": 120,
            "priority": 5,
            "due_datetime": f"{args.date}T18:00:00",
        },
        {
            "title": "Дизайн презентации",
            "type": "creative",
            "duration_minutes": 90,
            "priority": 4,
        },
        {
            "title": "Тренировка в зале",
            "type": "physical",
            "duration_minutes": 60,
            "priority": 3,
        },
        {
            "title": "Разбор почты и планов",
            "type": "routine",
            "duration_minutes": 30,
            "priority": 2,
            "recurrence_days": [0, 1, 2, 3, 4],
        },
        {
            "title": "Подготовка к экзамену",
            "type": "intellectual",
            "duration_minutes": 150,
            "priority": 4,
        },
    ]

    print("2. Создание задач в бэклоге...")
    for t in sample_tasks:
        c, resp = request_json("POST", f"{base}/api/v1/tasks", t, token=token)
        if c == 201:
            print(f"   + [{resp['id']}] {resp['title']} ({resp['status']})")
        else:
            print(f"   ! Ошибка создания '{t['title']}' ({c}): {resp}")

    print(f"3. Добавление ручного слота 'Обед' на {args.date} (13:00–14:00)...")
    c, slot_resp = request_json(
        "POST",
        f"{base}/api/v1/schedule/slots",
        {
            "date": args.date,
            "start_time": "13:00",
            "end_time": "14:00",
            "title": "Обед",
            "type": "rest",
        },
        token=token,
    )
    if c not in (201, 409):
        print(f"   ! Ошибка создания слота ({c}): {slot_resp}")

    print(f"4. Генерация расписания на {args.date}...")
    c, plan = request_json(
        "POST",
        f"{base}/api/v1/schedule/generate",
        {"date": args.date},
        token=token,
    )
    if c != 200:
        print(f"   Ошибка генерации ({c}): {plan}")
        sys.exit(1)

    print("\n=== ГОТОВО ===")
    print(f"Email:      {email}")
    print(f"Пароль:     {password}")
    print(f"Биоритмы:   {plan['biorhythms']} | {plan['status']}")
    print("Слоты дня:")
    for s in plan["slots"]:
        print(f"  [{s['id']}] {s['start_time']}–{s['end_time']}  {s['title']} ({s['type']}) | {s['reason']}")
        if s.get("warning"):
            print(f"       ! {s['warning']}")
    if plan["unplaced"]:
        print("Не поместилось:", [u["title"] for u in plan["unplaced"]])


if __name__ == "__main__":
    main()
