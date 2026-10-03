#!/usr/bin/env python3
"""Скачивание экспонатов одного музея из Государственного каталога Музейного фонда РФ.

Скрипт обращается к открытому API портала opendata.mkrf.ru (v2) и использует
серверную фильтрацию, поэтому скачивается только выбранный музей, а не весь
архив на ~11 ГБ.

Примеры:
    python scripts/download_data.py --limit 200
    python scripts/download_data.py --output pushkin.jsonl
    MKRF_API_KEY=xxxx python scripts/download_data.py --limit 1000

API-ключ (бесплатный) выдаётся на https://opendata.mkrf.ru/item/dev
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

try:
    from tqdm import tqdm
except ImportError:  # tqdm не обязателен
    tqdm = None

API_ROOT = "https://opendata.mkrf.ru/v2"
DEFAULT_MUSEUM_CODE = "110111"  # ГМИИ им. А.С. Пушкина
DEFAULT_VERSION = "4"
MAX_BATCH = 1000  # больше API не принимает (l=5000 -> 400)

RETRY_STATUSES = {429, 500, 502, 503, 504}
RETRY_ATTEMPTS = 6


def resolve_api_key(cli_value: str | None) -> str:
    """Возвращает API-ключ: аргумент -> переменная окружения -> интерактивный ввод."""
    key = cli_value or os.environ.get("MKRF_API_KEY")
    if key and key.strip():
        return key.strip()

    if not sys.stdin.isatty():
        sys.exit(
            "Не задан API-ключ. Передайте --api-key или переменную окружения "
            "MKRF_API_KEY. Получить ключ: https://opendata.mkrf.ru/item/dev"
        )

    try:
        key = getpass.getpass("Введите API-ключ (https://opendata.mkrf.ru/item/dev): ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nОтменено.")
    if not key:
        sys.exit("Пустой API-ключ.")
    return key


def build_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "X-API-KEY": api_key,
            "Accept": "application/json",
            "User-Agent": "mkrf-pushkin-downloader/1.0",
        }
    )
    return session


def request_json(
    session: requests.Session, url: str, params: dict[str, Any]
) -> dict[str, Any]:
    """GET с ретраями и понятными ошибками."""
    delay = 2.0
    last_error: object = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = session.get(url, params=params, timeout=60)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code == 401:
                sys.exit(
                    "401 Unauthorized: неверный или отсутствующий API-ключ.\n"
                    "Получить бесплатный ключ: https://opendata.mkrf.ru/item/dev"
                )
            if response.status_code in RETRY_STATUSES:
                last_error = RuntimeError(f"HTTP {response.status_code}")
            elif response.status_code >= 400:
                sys.exit(
                    f"HTTP {response.status_code}: {response.text[:300]}"
                )
            else:
                return response.json()

        if attempt < RETRY_ATTEMPTS:
            print(
                f"  ! {last_error}; повтор через {delay:.0f} с "
                f"({attempt}/{RETRY_ATTEMPTS})",
                file=sys.stderr,
            )
            time.sleep(delay)
            delay = min(delay * 2, 60)

    sys.exit(f"Не удалось получить данные: {last_error}")


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as fh:
        for _ in fh:
            count += 1
    return count


def fetch(
    session: requests.Session,
    args: argparse.Namespace,
    output_path: Path,
) -> tuple[int, int | None]:
    """Постранично скачивает записи и пишет их в JSONL. Возвращает (записано, всего)."""
    url = f"{API_ROOT}/museum-exhibits/{args.version}"
    flt = json.dumps({"data.museum.code": args.museum_code}, ensure_ascii=False)

    state_path = output_path.with_name(output_path.name + ".cursor")

    written = 0
    cursor: str | None = None
    if args.resume:
        written = count_lines(output_path)
        if state_path.exists():
            cursor = state_path.read_text(encoding="utf-8").strip() or None

    total: int | None = None
    bar = None
    mode = "a" if args.resume else "w"
    completed = False

    try:
        with output_path.open(mode, encoding="utf-8") as fh:
            while True:
                if args.limit and written >= args.limit:
                    completed = True
                    break

                page_size = args.batch
                if args.limit:
                    page_size = min(page_size, args.limit - written)

                params: dict[str, Any] = {"l": page_size, "f": flt}
                if cursor:
                    params["cursor"] = cursor

                payload = request_json(session, url, params)
                data = payload.get("data") or []

                if total is None:
                    total = payload.get("total")
                    if tqdm is not None and total is not None:
                        bar_total = min(total, args.limit) if args.limit else total
                        bar = tqdm(
                            total=bar_total,
                            initial=written,
                            unit="зап.",
                            desc="Скачивание",
                        )

                if not data:
                    completed = True
                    break

                for record in data:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                    written += 1
                    if bar is not None:
                        bar.update(1)
                    if args.limit and written >= args.limit:
                        break

                fh.flush()

                cursor = payload.get("cursor")
                if cursor:
                    state_path.write_text(cursor, encoding="utf-8")
                else:
                    completed = True
                    break
    finally:
        if bar is not None:
            bar.close()
        if completed and state_path.exists():
            state_path.unlink()

    return written, total


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Скачивание экспонатов музея из Госкаталога Минкультуры через API "
            "(по умолчанию — ГМИИ им. А.С. Пушкина)."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--api-key", help="API-ключ (иначе MKRF_API_KEY или промпт)")
    parser.add_argument(
        "--output",
        default="../data/pushkin_exhibits.jsonl",
        help="куда писать результат (JSON Lines)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="скачать только первые N записей (0 — все)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=MAX_BATCH,
        help=f"размер страницы, максимум {MAX_BATCH}",
    )
    parser.add_argument(
        "--museum-code",
        default=DEFAULT_MUSEUM_CODE,
        help="код музея в наборе (ГМИИ = 110111)",
    )
    parser.add_argument("--version", default=DEFAULT_VERSION, help="версия набора")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="продолжить по сохранённому курсору (<output>.cursor)",
    )

    args = parser.parse_args(argv)
    if args.limit < 0:
        parser.error("--limit не может быть отрицательным")
    if not 1 <= args.batch <= MAX_BATCH:
        parser.error(f"--batch должен быть в диапазоне 1..{MAX_BATCH}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    api_key = resolve_api_key(args.api_key)
    session = build_session(api_key)
    output_path = Path(args.output).expanduser().resolve()

    print(f"Музей (код): {args.museum_code}")
    print(f"Версия набора: {args.version}")
    print(f"Файл: {output_path}")
    if args.limit:
        print(f"Лимит: {args.limit} записей")
    if args.resume:
        print("Режим: дозапись (--resume)")

    try:
        written, total = fetch(session, args, output_path)
    except KeyboardInterrupt:
        print("\nПрервано пользователем.", file=sys.stderr)
        return 130

    size_mb = output_path.stat().st_size / 1024 / 1024 if output_path.exists() else 0
    print(
        f"\nГотово: записано {written} записей"
        + (f" из {total}" if total is not None else "")
        + f", файл {size_mb:.1f} МБ"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
