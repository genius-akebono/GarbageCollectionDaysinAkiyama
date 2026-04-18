#!/usr/bin/env python3
"""
秋山自治会ゴミ出しカレンダー HTML自動生成スクリプト

使い方:
    python3 generate_calendar.py                    # 当年度(4月〜翌3月)
    python3 generate_calendar.py 2026               # 2026年度
    python3 generate_calendar.py 2026 3             # 2026年3月のみ
    python3 generate_calendar.py 2026 4 2028 3      # 2026年4月〜2028年3月
"""

import calendar
import base64
import sys
import os
from datetime import date, timedelta
from pathlib import Path

import jpholiday

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent

def _find_image_dir():
    """images/ ディレクトリをスクリプト位置から上位へ探索"""
    candidate = SCRIPT_DIR / "images"
    if candidate.exists():
        return candidate
    for parent in SCRIPT_DIR.parents:
        candidate = parent / "images"
        if candidate.exists():
            return candidate
    return SCRIPT_DIR / "icons"  # フォールバック

ICON_DIR = _find_image_dir()

WEEKDAY_NAMES_JA = ["月", "火", "水", "木", "金", "土", "日"]
MONTH_NAMES_EN = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# アイコンファイル名
ICON_FILES = {
    "saisei_kami":      "01_saisei_kami.png",
    "recycle_plastic":  "02_recycle_plastic.png",
    "kanen_gomi":       "03_kanen_gomi.png",
    "gomu_gawa":        "04_gomu_gawa.png",
    "kan_bin":          "05_kan_bin.png",
    "friday_kami_nuno": "06_friday_kami_nuno.png",
    "friday_bin_kan":   "06_friday_bin_kan.png",
    "shushu_nashi":     "07_shushu_nashi.png",
}

# ---------------------------------------------------------------------------
# アイコンを base64 Data URI に変換（HTMLに埋め込み）
# ---------------------------------------------------------------------------
def load_icons_base64():
    icons = {}
    for key, fname in ICON_FILES.items():
        fpath = ICON_DIR / fname
        if fpath.exists():
            with open(fpath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            icons[key] = f"data:image/png;base64,{b64}"
        else:
            icons[key] = ""
    return icons


# ---------------------------------------------------------------------------
# 曜日ルールに基づくゴミ種別の決定
# ---------------------------------------------------------------------------
def get_garbage_info(d):
    """
    指定日のゴミ収集情報を返す。
    Returns: list of dict with keys: icon_key, label, css_class
    """
    dow = d.weekday()  # 0=Mon ... 6=Sun

    # 第何週目かを計算（月内で同じ曜日が何回目か）
    week_num = (d.day - 1) // 7 + 1  # 1-indexed

    if dow == 6:  # 日曜
        # 第5日曜は収集なし
        if week_num >= 5:
            return [{"icon_key": "shushu_nashi", "label": "収集\nなし", "css_class": "shushu-nashi"}]
        return [{"icon_key": "saisei_kami", "label": "再生する紙", "css_class": "saisei-kami"}]

    if dow == 0:  # 月曜
        return [{"icon_key": "recycle_plastic", "label": "リサイクルする\nプラスチック", "css_class": "recycle-plastic"}]

    if dow == 1:  # 火曜
        return [{"icon_key": "kanen_gomi", "label": "可燃ゴミ", "css_class": "kanen-gomi"}]

    if dow == 2:  # 水曜
        return [{"icon_key": "gomu_gawa", "label": "ゴム・合皮\nその他のプラスチック", "css_class": "gomu-gawa"}]

    if dow == 3:  # 木曜
        return [{"icon_key": "kanen_gomi", "label": "可燃ゴミ", "css_class": "kanen-gomi"}]

    if dow == 4:  # 金曜
        # 奇数週: 資源ゴミ(紙・布) / 偶数週: 資源ゴミ(ビン・缶)
        if week_num % 2 == 1:
            icon_key = "friday_kami_nuno"
            label = "・不燃ゴミ\n・有害ゴミ\n・資源ゴミ(紙・布)\n・剪定枝・雑草\n・かさ・乾電池"
        else:
            icon_key = "friday_bin_kan"
            label = "・不燃ゴミ\n・有害ゴミ\n・資源ゴミ(ビン・缶)\n・剪定枝・雑草\n・かさ・乾電池"
        return [{
            "icon_key": icon_key,
            "label": label,
            "css_class": "friday-img",
        }]

    if dow == 5:  # 土曜
        return [
            {"icon_key": "kanen_gomi", "label": "可燃ゴミ", "css_class": "kanen-small"},
            {"icon_key": "kan_bin", "label": "缶・ビン", "css_class": "kan-bin"},
        ]

    return []


# ---------------------------------------------------------------------------
# 1ヶ月分の HTML テーブル生成
# ---------------------------------------------------------------------------
def generate_month_html(year, month, icons_b64):
    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり
    weeks = cal.monthdayscalendar(year, month)

    rows_html = ""
    for week in weeks:
        row = ""
        for i, day in enumerate(week):
            # 曜日: i=0→日, i=1→月, ... i=6→土
            if day == 0:
                row += '      <td class="empty"></td>\n'
                continue

            d = date(year, month, day)
            is_holiday = jpholiday.is_holiday(d)
            holiday_name = jpholiday.is_holiday_name(d) if is_holiday else None
            dow = d.weekday()  # 0=Mon..6=Sun
            is_sunday = dow == 6
            is_saturday = dow == 5

            # 日付のCSSクラス
            day_classes = []
            if is_sunday or is_holiday:
                day_classes.append("holiday")
            elif is_saturday:
                day_classes.append("saturday")

            day_class = " ".join(day_classes)

            # ゴミ情報
            items = get_garbage_info(d)

            # セル内容を組み立て
            cell_content = f'<div class="day-number {day_class}">{day}</div>\n'

            if holiday_name:
                cell_content += f'<div class="holiday-name">{holiday_name}</div>\n'

            for item in items:
                icon_html = ""
                if item["icon_key"] and item["icon_key"] in icons_b64 and icons_b64[item["icon_key"]]:
                    css = item["css_class"]
                    icon_html = f'<img src="{icons_b64[item["icon_key"]]}" class="icon {css}" alt="{item["label"]}">'

                label_lines = item["label"].replace("\n", "<br>")
                if item["css_class"] == "friday-img":
                    if icon_html:
                        cell_content += f'<div class="friday-img-wrap">{icon_html}</div>\n'
                    else:
                        cell_content += f'<div class="friday-items">{label_lines}</div>\n'
                elif item["css_class"] == "shushu-nashi":
                    if icon_html:
                        cell_content += f'<div class="item-wrap">{icon_html}</div>\n'
                    else:
                        cell_content += f'<div class="shushu-nashi-text">収集<br>なし</div>\n'
                else:
                    cell_content += f'<div class="item-wrap">{icon_html}<span class="item-label {item["css_class"]}-label">{label_lines}</span></div>\n'

            td_class = "sun" if i == 0 else ("sat" if i == 6 else "")
            row += f'      <td class="day-cell {td_class}">{cell_content}</td>\n'

        rows_html += f"    <tr>\n{row}    </tr>\n"

    # ヘッダー行（日〜土）
    dow_order = ["日", "月", "火", "水", "木", "金", "土"]
    dow_classes = ["sun-header", "", "", "", "", "", "sat-header"]
    header_cells = "".join(
        f'<th class="{cls}">{name}</th>' for name, cls in zip(dow_order, dow_classes)
    )

    month_html = f"""
  <div class="calendar-month">
    <h1 class="main-title">ゴミ出しカレンダー</h1>
    <h2 class="month-title">{year}年 <span class="month-num">{month}</span>月 <span class="month-en">{MONTH_NAMES_EN[month]}</span></h2>
    <table class="cal-table">
      <thead>
        <tr>{header_cells}</tr>
      </thead>
      <tbody>
{rows_html}
      </tbody>
    </table>
    <div class="notes">
      <p class="notes-title">※再生する紙・ビン・缶自主回収</p>
      <p class="notes-detail">ビン・缶は土曜午前8時までに各集積所へ出してください</p>
      <p class="notes-detail">再生する紙は日曜午前10時までに<span class="red-emphasis">縛って自宅前に出してください</span></p>
    </div>
    <div class="footer">秋山自治会 <span class="footer-sub">作成</span></div>
  </div>
"""
    return month_html


# ---------------------------------------------------------------------------
# 全体 HTML 組み立て
# ---------------------------------------------------------------------------
CSS = """
@charset "UTF-8";
@page {
  size: A4 portrait;
  margin: 6mm;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: "Kozuka Gothic Pro", "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Meiryo", sans-serif;
  font-size: 12px;
  color: #231f20;
  background: #fff;
}
.calendar-month {
  width: 210mm;
  max-width: 100%;
  margin: 0 auto;
  page-break-after: always;
  padding: 2mm 5mm;
}
.calendar-month:last-child {
  page-break-after: avoid;
}
h1.main-title {
  text-align: center;
  font-size: 46px;
  font-weight: bold;
  letter-spacing: 0.25em;
  margin-bottom: 0;
  color: #231f20;
}
h2.month-title {
  text-align: center;
  font-size: 16px;
  margin: 2px 0;
  border-bottom: 2px solid #231f20;
  padding-bottom: 3px;
  color: #231f20;
}
.month-num {
  font-size: 36px;
  font-weight: bold;
}
.month-en {
  font-size: 25px;
  font-weight: bold;
}
.cal-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.cal-table th, .cal-table td {
  border: 1.5px solid #555;
  text-align: center;
  vertical-align: top;
  padding: 2px;
}
.cal-table th {
  background: #ddd;
  font-size: 16px;
  font-weight: bold;
  padding: 5px 0;
}
.sun-header {
  background: #ffe066 !important;
  color: #ed1b24;
}
.sat-header {
  background: #ffe066 !important;
  color: #2e3191;
}
.day-cell {
  height: 128px;
  width: 14.28%;
  position: relative;
}
.day-cell.sun {
  background: #fffde6;
}
.day-cell.sat {
  background: #fffde6;
}
.empty {
  background: #f9f9f9;
}
.day-number {
  font-size: 25px;
  font-weight: bold;
  text-align: left;
  padding-left: 3px;
  line-height: 1.2;
}
.day-number.holiday {
  color: #ed1b24;
}
.day-number.saturday {
  color: #2e3191;
}
.holiday-name {
  font-size: 9px;
  color: #ed1b24;
  margin-top: -2px;
}
.icon {
  display: block;
  margin: 1px auto;
  max-width: 60px;
  max-height: 48px;
  object-fit: contain;
}
.icon.kanen-small {
  max-width: 30px;
  max-height: 26px;
  display: inline-block;
  vertical-align: middle;
}
.icon.kan-bin {
  max-width: 48px;
  max-height: 42px;
  display: inline-block;
  vertical-align: middle;
}
.item-wrap {
  margin-top: 0;
}
.item-label {
  font-size: 13px;
  font-weight: bold;
  display: block;
  line-height: 1.15;
}
.saisei-kami-label { color: #1c6434; }
.recycle-plastic-label { color: #3044a1; }
.kanen-gomi-label { color: #9b3d28; }
.gomu-gawa-label { color: #3044a1; }
.kanen-small-label {
  color: #9b3d28;
  font-size: 11px;
  font-weight: bold;
  display: inline;
  vertical-align: middle;
}
.kan-bin-label {
  color: #1c6434;
  font-size: 11px;
  font-weight: bold;
  display: inline;
  vertical-align: middle;
}
.friday-items {
  font-size: 12px;
  color: #782f99;
  text-align: left;
  padding-left: 2px;
  line-height: 1.15;
  margin-top: 0;
  font-weight: bold;
}
.friday-img-wrap {
  margin-top: 2px;
}
.icon.friday-img {
  max-width: 90px;
  max-height: 90px;
  display: block;
  margin: 0 auto;
}
.shushu-nashi-text {
  font-size: 31px;
  font-weight: bold;
  color: #231f20;
  margin-top: 8px;
  line-height: 1.2;
}
.notes {
  margin-top: 6px;
  padding: 6px 10px;
  border: 2px solid #231f20;
}
.notes .notes-title {
  font-size: 28px;
  font-weight: bold;
  text-align: center;
  margin-bottom: 2px;
  color: #231f20;
}
.notes .notes-detail {
  font-size: 19px;
  text-align: center;
  margin: 1px 0;
  color: #231f20;
  white-space: nowrap;
}
.notes .red-emphasis {
  border: 2px solid #ed1b24;
  padding: 0 3px;
}
.footer {
  text-align: center;
  font-size: 32px;
  font-weight: bold;
  margin-top: 4px;
  color: #231f20;
  font-family: "Kozuka Mincho Pro", "Yu Mincho", "Hiragino Mincho ProN", "Noto Serif JP", serif;
}
.footer .footer-sub {
  font-size: 22px;
  font-weight: normal;
}
@media print {
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .calendar-month { padding: 0; }
}
"""


def generate_full_html(year_start, month_start, year_end, month_end):
    icons_b64 = load_icons_base64()

    months_html = ""
    y, m = year_start, month_start
    while (y, m) <= (year_end, month_end):
        months_html += generate_month_html(y, m, icons_b64)
        m += 1
        if m > 12:
            m = 1
            y += 1

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ゴミ出しカレンダー {year_start}年{month_start}月〜{year_end}年{month_end}月</title>
  <style>
{CSS}
  </style>
</head>
<body>
{months_html}
</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def main():
    args = sys.argv[1:]

    if len(args) == 0:
        # 当年度 (4月〜翌3月)
        today = date.today()
        if today.month >= 4:
            fy = today.year
        else:
            fy = today.year - 1
        year_start, month_start = fy, 4
        year_end, month_end = fy + 1, 3
    elif len(args) == 1:
        # 指定年度
        fy = int(args[0])
        year_start, month_start = fy, 4
        year_end, month_end = fy + 1, 3
    elif len(args) == 2:
        # 指定年月のみ
        year_start = int(args[0])
        month_start = int(args[1])
        year_end, month_end = year_start, month_start
    elif len(args) == 4:
        # 範囲指定
        year_start, month_start = int(args[0]), int(args[1])
        year_end, month_end = int(args[2]), int(args[3])
    else:
        print("Usage: python3 generate_calendar.py [year] [month] [year_end month_end]")
        sys.exit(1)

    html = generate_full_html(year_start, month_start, year_end, month_end)

    out_name = f"gomi_calendar_{year_start}{month_start:02d}_{year_end}{month_end:02d}.html"
    out_path = SCRIPT_DIR / out_name
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generated: {out_path}")
    print(f"  Period: {year_start}/{month_start} ~ {year_end}/{month_end}")

    # 月数カウント
    count = 0
    y, m = year_start, month_start
    while (y, m) <= (year_end, month_end):
        count += 1
        m += 1
        if m > 12:
            m = 1
            y += 1
    print(f"  Total months: {count}")


if __name__ == "__main__":
    main()
