import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = [
    "ID", "Дата", "Медпредставитель", "Username", "Учреждение",
    "Телефон", "Препараты и количество", "Всего позиций", "Статус"
]


def get_sheets_client():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON не задан в .env")
    creds_data = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_worksheet():
    client = get_sheets_client()
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    spreadsheet = client.open_by_key(sheet_id)
    
    try:
        ws = spreadsheet.worksheet("Заявки")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet("Заявки", rows=1000, cols=20)
        ws.append_row(SHEET_HEADERS)
        # Форматирование шапки
        ws.format("A1:I1", {
            "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.9},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
        })
    return ws


def append_order_to_sheet(order_id: int, full_name: str, username: str,
                           institution: str, phone: str,
                           items: list[dict], products_map: dict) -> int:
    """
    Добавляет заявку в таблицу. Возвращает номер строки.
    products_map: {product_id: product_name}
    """
    ws = get_or_create_worksheet()
    
    # Формируем читаемую строку препаратов
    items_str = "; ".join(
        f"{products_map.get(i['product_id'], i['product_id'])}: {i['quantity']} {i.get('unit', 'шт')}"
        for i in items
    )
    total = sum(i["quantity"] for i in items)
    
    row = [
        order_id,
        datetime.now().strftime("%d.%m.%Y %H:%M"),
        full_name,
        f"@{username}" if username else "—",
        institution,
        phone or "—",
        items_str,
        total,
        "Новая"
    ]
    
    ws.append_row(row)
    # Возвращаем номер последней строки
    return len(ws.get_all_values())
