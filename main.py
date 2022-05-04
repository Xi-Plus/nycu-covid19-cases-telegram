import argparse
import re

import pymysql
import requests
from telethon import TelegramClient

from config import (DB_DATABASE, DB_HOST, DB_PASSWORD, DB_USER, tg_api_hash,
                    tg_api_id, tg_bot_token, tg_chat_id)

client = TelegramClient('bot', tg_api_id, tg_api_hash).start(bot_token=tg_bot_token)

parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true')
parser.set_defaults(dry_run=False)
args = parser.parse_args()


async def main():
    db = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASSWORD,
        db=DB_DATABASE,
        charset='utf8mb4'
    )
    cur = db.cursor()

    try:
        headers = {
            'User-Agent': 'nycu-covid19-cases-telegram 1.0',
        }
        req = requests.get('http://covid-news.nycu.edu.tw/total-cases/', headers=headers)
    except Exception as e:
        print(e)
        exit()
    page_html = req.text

    cur.execute("""SELECT `message` FROM `nycu_covid19_cases`""")
    rows = cur.fetchall()
    old_message = set()
    for row in rows:
        old_message.add(row[0])

    matches = re.findall(r'<td>(\d+\/\d+)<\/td>\s*<td>(.+?)<\/td>\s*<td>(.+?)<\/td>\s*<td>(.+?)<br \/>\s*(.+?)<\/td>', page_html)
    for match in matches:
        date, case, campus, detailzh, detailen = match
        case_list = case.split(' ')
        campus_list = campus.split(' ')

        if len(case_list) == 2 and len(campus_list) == 2:
            text = '{date} {campuszh}{casezh} {detailzh}\n{campusen} {caseen}: {detailen}'.format(
                date=date,
                campuszh=campus_list[0],
                casezh=case_list[0],
                detailzh=detailzh,
                campusen=campus_list[1],
                caseen=case_list[1],
                detailen=detailen,
            )
        else:
            text = '{date} {campus} {case} {detailzh}\n{detailen}'.format(
                date=date,
                campus=campus,
                case=case,
                detailzh=detailzh,
                detailen=detailen,
            )
        if text not in old_message:
            old_message.add(text)

            cur.execute("""INSERT INTO `nycu_covid19_cases` (`message`) VALUES (%s)""", (text))
            db.commit()

            if not args.dry_run:
                await client.send_message(
                    tg_chat_id,
                    text,
                    link_preview=False,
                )

with client:
    client.loop.run_until_complete(main())
