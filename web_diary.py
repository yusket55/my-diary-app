import datetime
from io import BytesIO
import os
from dotenv import load_dotenv
import streamlit as st
from supabase import create_client

# ページの基本設定（ワイドモードに設定）
st.set_page_config(
    page_title="マイ日記アプリ", page_icon="📖", layout="wide"
)

# --- 接続情報の読み込み ---
try:
  SUPABASE_URL = st.secrets["SUPABASE_URL"]
  SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
  load_dotenv()
  SUPABASE_URL = os.getenv("SUPABASE_URL")
  SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabaseクライアントの初期化
@st.cache_resource
def init_supabase():
  return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()

# --- タイトル ---
st.title("📖 マイ日記アプリ（2カラムレイアウト）")

# --- メインレイアウト：2カラム構成 ---
col_left, col_right = st.columns([1, 1.5], gap="large")

today = datetime.date.today()

with col_left:
  st.subheader("📅 日付と写真")
  selected_date = st.date_input("記録する日付を選択", value=today)
  date_str = selected_date.strftime("%Y-%m-%d")

  # データベースから選択した日付のデータを取得
  try:
    response = (
        supabase.table("diaries")
        .select("*")
        .eq("diary_date", date_str)
        .execute()
    )
    existing_data = response.data
  except Exception as e:
    st.error("データベースからのデータ取得に失敗しました:")
    st.exception(e)
    existing_data = []

  current_content = ""
  current_image_urls = []

  if existing_data:
    current_content = existing_data[0].get("content", "")
    # image_urls (配列) または古い互換性のための image_url を取得
    img_urls_raw = existing_data[0].get("image_urls")
    if img_urls_raw:
      if isinstance(img_urls_raw, list):
        current_image_urls = img_urls_raw
      else:
        current_image_urls = [img_urls_raw]
    else:
      single_img = existing_data[0].get("image_url")
      if single_img:
        current_image_urls = [single_img]

  st.markdown("---")
  st.markdown("**📸 登録されている写真**")

  # 登録済み写真を縦に並べて表示 ＆ 個別削除ボタン機能
  if current_image_urls:
    updated_image_urls = list(current_image_urls)
    to_remove = None

    for i, url in enumerate(current_image_urls):
      st.image(url, use_container_width=True)
      if st.button("🗑️ この写真を削除する", key=f"del_img_{i}"):
        to_remove = url

    if to_remove:
      updated_image_urls.remove(to_remove)
      try:
        supabase.table("diaries").upsert({
            "diary_date": date_str,
            "content": current_content,
            "image_urls": updated_image_urls
        }).execute()
        st.success("写真を削除しました！")
        st.rerun()
      except Exception as e:
        st.error("写真の削除に失敗しました:")
        st.exception(e)
  else:
      st.info("この日の写真はまだ登録されていません。")

with col_right:
  st.subheader(f"✍️ {date_str} の日記")

  with st.form("diary_form"):
    content_input = st.text_area(
        "今日の出来事や気持ちを書いてください",
        value=current_content,
        height=300,
    )

    # 複数ファイルのアップロード（accept_multiple_files=True で複数選択が可能）
    uploaded_files = st.file_uploader(
        "写真を複数選択してアップロード（PNG, JPGなど）",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )

    submitted = st.form_submit_button("💾 この内容で保存する")

    if submitted:
      # 既存の写真をベースにする
      new_image_urls = list(current_image_urls)

      # 新しくアップロードされたファイルがある場合、順番にSupabase Storageへ保存
      if uploaded_files:
        for uploaded_file in uploaded_files:
          file_bytes = uploaded_file.read()
          # ファイル名が被らないように日付と日時・ファイル名を結合
          file_name = f"{date_str}_{datetime.datetime.now().strftime('%H%M%S_%f')}_{uploaded_file.name}"
          storage_path = f"diary_images/{file_name}"

          try:
            # Supabase Storageへアップロード
            supabase.storage.from_("diary-images").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": uploaded_file.type},
            )
            # 公開URLを取得
            url_data = supabase.storage.from_("diary-images").get_public_url(
                storage_path
            )
            if isinstance(url_data, dict):
              public_url = url_data.get("publicUrl") or url_data.get(
                  "public_url"
              )
            else:
              public_url = url_data

            if public_url:
              new_image_urls.append(public_url)
          except Exception as e:
            st.error(f"写真のアップロードに失敗しました ({uploaded_file.name}):")
            st.exception(e)

      # データベースに保存（upsert）
      upsert_data = {
          "diary_date": date_str,
          "content": content_input,
          "image_urls": new_image_urls,
      }

      try:
        supabase.table("diaries").upsert(upsert_data).execute()
        st.success("日記と写真を保存しました！")
        st.rerun()
      except Exception as e:
        st.error("データベースへの保存に失敗しました:")
        st.exception(e)
