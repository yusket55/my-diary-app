import datetime
import requests
import streamlit as st

# 秘密の金庫（Streamlit Cloudの設定画面）からURLとキーを安全に取得します
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

st.set_page_config(page_title="マイ・カレンダー日記", page_icon="📖", layout="centered")

st.title("📖 カレンダー付きクラウド日記")
st.write("日付を選んで、その日の日記を読んだり書いたりできます。")

# 日付選択ピッカー
selected_date = st.date_input("日付を選んでください", datetime.date.today())
date_str = str(selected_date)

def fetch_diary(target_date):
    db_url = f"{SUPABASE_URL}/rest/v1/diaries?diary_date=eq.{target_date}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    response = requests.get(db_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0].get("content", "")
    return ""

def save_diary(target_date, content):
    db_url = f"{SUPABASE_URL}/rest/v1/diaries"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    data = {
        "diary_date": target_date,
        "content": content,
        "image_url": None
    }
    response = requests.post(db_url, headers=headers, json=data)
    return response.status_code in [200, 201], response.text

existing_content = fetch_diary(date_str)

st.subheader(f"📅 {date_str} の日記")
diary_content = st.text_area("今日の出来事や思い出:", value=existing_content, height=200)

if st.button("💾 この内容で保存する"):
    if not diary_content.strip():
        st.warning("本文が空です。")
    else:
        success, error_detail = save_diary(date_str, diary_content)
        if success:
            st.success(f"🎉 {date_str} の日記をクラウドに保存しました！")
        else:
            st.error(f"保存に失敗しました。詳細: {error_detail}")