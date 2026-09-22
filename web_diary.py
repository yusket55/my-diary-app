import datetime
import requests
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET_NAME = "diary-images"

st.set_page_config(page_title="マイ・カレンダー日記", page_icon="📖", layout="centered")

st.title("📖 カレンダー付きクラウド日記（写真対応版）")
st.write("日付を選んで、日記の文章と写真を発行・保存できます。")

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
            return data[0]
    return {}

def upload_image_to_supabase(uploaded_file, target_date):
    file_ext = uploaded_file.name.split(".")[-1]
    file_name = f"{target_date}.{file_ext}"
    storage_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{file_name}"
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": uploaded_file.type,
        "x-upsert": "true" # 既に画像がある場合は上書き
    }
    response = requests.post(storage_url, headers=headers, data=uploaded_file.getvalue())
    if response.status_code in [200, 201]:
        return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_name}"
    return None

def save_diary(target_date, content, image_url):
    db_url = f"{SUPABASE_URL}/rest/v1/diaries"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    # 既存データがあるか確認してupsert（存在すれば更新、なければ挿入）するための処理
    payload = {
        "diary_date": target_date,
        "content": content,
    }
    if image_url:
        payload["image_url"] = image_url

    response = requests.post(db_url, headers=headers, json=payload)
    return response.status_code in [200, 201], response.text

# データの読み込み
existing_data = fetch_diary(date_str)
existing_content = existing_data.get("content", "")
existing_image_url = existing_data.get("image_url", None)

st.subheader(f"📅 {date_str} の日記")
diary_content = st.text_area("今日の出来事や思い出:", value=existing_content, height=200)

# 写真アップロード用ウィジェット
uploaded_file = st.file_uploader("写真をえらぶ（Googleフォトや端末の画像）", type=["jpg", "jpeg", "png"])

# 既に保存されている画像があれば表示
if uploaded_file is not None:
    st.image(uploaded_file, caption="選択中の写真", use_column_width=True)
elif existing_image_url:
    st.image(existing_image_url, caption="保存済みの写真", use_column_width=True)

if st.button("💾 この内容で保存する"):
    if not diary_content.strip() and not uploaded_file:
        st.warning("本文または写真を入力してください。")
    else:
        image_url = existing_image_url
        if uploaded_file is not None:
            with st.spinner("写真をアップロード中..."):
                image_url = upload_image_to_supabase(uploaded_file, date_str)
        
        success, error_detail = save_diary(date_str, diary_content, image_url)
        if success:
            st.success(f"🎉 {date_str} の日記と写真をクラウドに保存しました！")
        else:
            st.error(f"保存に失敗しました。詳細: {error_detail}")