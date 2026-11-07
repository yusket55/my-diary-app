import csv
import datetime
from io import BytesIO, StringIO
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
  selected_date = st.date_input("記録する日付を選択", value=today, key="date_input")
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
    latest_record = existing_data[-1]
    current_content = latest_record.get("content", "")
    
    img_urls_raw = latest_record.get("image_urls")
    if img_urls_raw:
      if isinstance(img_urls_raw, list):
        current_image_urls = img_urls_raw
      else:
        current_image_urls = [img_urls_raw]
    else:
      single_img = latest_record.get("image_url")
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
      if st.button("🗑️ この写真を削除する", key=f"del_{date_str}_{i}"):
        to_remove = url

    if to_remove:
      updated_image_urls.remove(to_remove)
      try:
        supabase.table("diaries").update({
            "image_urls": updated_image_urls
        }).eq("diary_date", date_str).execute()
        
        st.success("写真を削除しました！")
        st.reron = st.rerun() # type: ignore
      except Exception as e:
        st.error("写真の削除に失敗しました:")
        st.exception(e)
  else:
      st.info("この日の写真はまだ登録されていません。")

  # --- CSVデータ書き出しセクション ---
  st.markdown("---")
  st.markdown("**⚙️ データ管理（バックアップ）**")
  try:
    all_res = supabase.table("diaries").select("*").execute()
    all_data = all_res.data
    if all_data:
      output = StringIO()
      writer = csv.writer(output)
      writer.writerow(["diary_date", "content", "image_urls"])
      for row in all_data:
        d_date = row.get("diary_date", "")
        d_content = row.get("content", "").replace("\n", " ")
        d_urls = row.get("image_urls", [])
        urls_str = ",".join(d_urls) if isinstance(d_urls, list) else str(d_urls)
        writer.writerow([d_date, d_content, urls_str])
      
      csv_data = output.getvalue()
      st.download_button(
          label="📥 全日記データをCSVでダウンロード",
          data=csv_data,
          file_name=f"diary_backup_{datetime.date.today().strftime('%Y%m%d')}.csv",
          mime="text/csv",
      )
    else:
      st.caption("まだ保存された日記データがありません。")
  except Exception as e:
    st.caption("CSVエクスポートの準備中...")

with col_right:
  st.subheader(f"✍️ {date_str} の日記")

  content_input = st.text_area(
      "今日の出来事や気持ちを書いてください",
      value=current_content,
      height=300,
      key=f"content_{date_str}"
  )

  # 複数ファイルのアップロード
  uploaded_files = st.file_uploader(
      "写真を複数選択してアップロード（PNG, JPGなど）",
      type=["png", "jpg", "jpeg"],
      accept_multiple_files=True,
      key=f"uploader_{date_str}"
  )

  if st.button("💾 この内容で保存する", type="primary"):
    new_image_urls = list(current_image_urls)

    if uploaded_files:
      for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.read()
        file_name = f"{date_str}_{datetime.datetime.now().strftime('%H%M%S_%f')}_{uploaded_file.name}"
        storage_path = f"diary_images/{file_name}"

        try:
          supabase.storage.from_("diary-images").upload(
              path=storage_path,
              file=file_bytes,
              file_options={"content-type": uploaded_file.type},
          )
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

    try:
      check_res = (
          supabase.table("diaries")
          .select("id")
          .eq("diary_date", date_str)
          .execute()
      )

      if check_res.data and len(check_res.data) > 0:
        supabase.table("diaries").update({
            "content": content_input,
            "image_urls": new_image_urls,
        }).eq("diary_date", date_str).execute()
      else:
        # 修正箇所：ここを正しいコロンに変更しました
        supabase.table("diaries").insert({
            "diary_date": date_str,
            "content": content_input,
            "image_urls": new_image_urls,
        }).execute()

      st.success("日記と写真を保存しました！")
      st.rerun()
    except Exception as e:
      st.error("データベースへの保存に失敗しました:")
      st.exception(e)
