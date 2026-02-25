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
    "ID", "Дата", "Код", "Медпредставитель", "Username",
    "Учреждение", "Препараты и количество",
    "Сумма полная", "Оплата %", "К оплате", "Статус"
]


def get_sheets_client():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON не задан")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_worksheet():
    client = get_sheets_client()
    spreadsheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID"))
    try:
        ws = spreadsheet.worksheet("Заявки")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet("Заявки", rows=1000, cols=20)
        ws.append_row(SHEET_HEADERS)
        ws.format("A1:K1", {
            "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.9},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
        })
    return ws


def append_order_to_sheet(order_id, rep_code, full_name, username, institution,
                           items, products_map, total_price, payment_percent, payment_amount):
    ws = get_or_create_worksheet()
    items_str = "; ".join(
        f"{products_map.get(i['product_id'], '?')}: {i['quantity']} {i.get('unit','шт')} × {i.get('price',0):.2f}"
        for i in items
    )
    row = [
        order_id,
        datetime.now().strftime("%d.%m.%Y %H:%M"),
        rep_code,
        full_name,
        f"@{username}" if username else "—",
        institution,
        items_str,
        f"{total_price:.2f}",
        f"{payment_percent}%",
        f"{payment_amount:.2f}",
        "Новая",
    ]
    ws.append_row(row)
    return len(ws.get_all_values())
