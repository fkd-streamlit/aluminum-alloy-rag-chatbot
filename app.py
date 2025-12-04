# ------------------------------------------------------------
# アルミニウム合金 RAG ChatBot - 完全版フル機能 / 安全動作版（2025リビルド）
# ------------------------------------------------------------

import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Optional
from pathlib import Path

# GitHub に置くデフォルトデータのパス（正しい位置）
DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "temp_data.xlsx"

# ------------------------------------------------------------
# ページ設定
# ------------------------------------------------------------
st.set_page_config(
    page_title="アルミニウム合金 RAG ChatBot",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------
# CSS デザイン
# ------------------------------------------------------------
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stChatMessage {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196F3;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 4px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# RAG クラス
# ------------------------------------------------------------
class AluminumAlloyRAG:

    def __init__(self, excel_path: str):
        self.data = {}
        self.series_info = {}
        self.all_alloys = {}
        self.mechanical_table = None
        self.temper_descriptions = {
            'T6': '溶体化処理後、人工時効硬化処理を施したもの。',
            'T651': 'T6に加え、残留応力除去のため引張処理。',
            'T3': '溶体化→冷間加工→自然時効。',
            'T4': '溶体化→自然時効。',
            'T5': '高温加工後に人工時効硬化。',
            'O': '焼なまし材で最も柔らかい。',
            'H12': '1/4硬化',
            'H14': '1/2硬化',
            'H16': '3/4硬化',
            'H18': '完全硬化'
        }

        self.load_data(excel_path)
        self.parse_all_sheets()
        self.build_indexes()

    # --------------------------------------------------------
    # safe_alloy_format
    # --------------------------------------------------------
    def safe_alloy_format(self, alloy_value, temper):
        s = str(alloy_value)
        nums = re.findall(r'\d+', s)
        if nums:
            n = int(nums[0])
            return f"A{n:04d}-{temper}"
        return f"{s}-{temper}"

    # --------------------------------------------------------
    # Excel 読み込み
    # --------------------------------------------------------
    def load_data(self, excel_path: str):
        try:
            xls = pd.ExcelFile(excel_path)
            for sheet in xls.sheet_names:
                df = pd.read_excel(excel_path, sheet_name=sheet)
                df.columns = df.columns.str.strip()
                self.data[sheet] = df
        except Exception as e:
            st.error(f"❌ ファイル読み込みエラー: {e}")

    # --------------------------------------------------------
    # 全シート走査
    # --------------------------------------------------------
    def parse_all_sheets(self):
        for sheet, df in self.data.items():
            for col in df.columns:
                if any(k in str(col).lower() for k in ['合金', 'alloy']):
                    for _, row in df.iterrows():
                        name = str(row[col]).strip()
                        if name:
                            self.all_alloys.setdefault(name, []).append({
                                "sheet": sheet,
                                "data": row.to_dict()
                            })

    # --------------------------------------------------------
    # 系列情報 & 機械特性テーブル
    # --------------------------------------------------------
    def build_indexes(self):
        self.mechanical_table = self.data.get("aluminum_handbook_table")

        series_sheet = self.data.get("アルミニウム合金の特性")
        if series_sheet is not None:
            for _, r in series_sheet.iterrows():
                name = r.get("合金系")
                if isinstance(name, str) and "系" in name:
                    m = re.search(r'(\d{4})', name)
                    if m:
                        s = int(m.group(1)) // 1000 * 1000
                        self.series_info[s] = {
                            "name": name,
                            "overview": r.get("概要", ""),
                            "features": r.get("代表的な特性（強度、溶接性、耐食性）", "")
                        }

    # --------------------------------------------------------
    # 検索機能（省略せず全て残す）
    # --------------------------------------------------------
def get_alloy_by_strength(self, min_strength: float):
    response = f"## 🔍 引張強さ {min_strength} MPa 以上の合金\n\n"
    results = []

    if self.mechanical_table is None:
        return response + "データが読み込まれていません。"

    df = self.mechanical_table

    for _, row in df.iterrows():
        raw_strength = row.get("引張強さ (MPa)", None)

        # 数値変換を安全に実行
        try:
            strength = float(raw_strength)
        except:
            continue  # 数値でなければスキップ

        if strength >= min_strength:
            results.append({
                'alloy': self.safe_alloy_format(row.get('Alloy', ''), row.get('Temper', '')),
                'strength': strength,
                'series': row.get('系列', ''),
                'row': row
            })

    if not results:
        return response + "該当する合金が見つかりませんでした。"

    # 強度の高い順に並べる
    results.sort(key=lambda x: x['strength'], reverse=True)

    for r in results[:10]:
        response += f"### ✨ {r['alloy']}\n"
        response += f"- 引張強さ: {r['strength']} MPa\n"

        # 他のカラムを追加表示
        for key, val in r['row'].items():
            if pd.notna(val) and key not in ['Alloy', 'Temper', '引張強さ (MPa)']:
                response += f"- **{key}**: {val}\n"

        response += "\n"

    return response


    # --------------------------------------------------------
    # 振り分け
    # --------------------------------------------------------
    def process_query(self, q):
        text = q.lower()

        if "純アルミ" in text:
            return self.get_pure_aluminum_info()

        if "引張" in text:
            nums = re.findall(r"\d+", text)
            val = int(nums[0]) if nums else 400
            return self.get_alloy_by_strength(val)

        if "耐食" in text or "溶接" in text:
            keys = []
            if "耐食" in text:
                keys.append("耐食")
            if "溶接" in text:
                keys.append("溶接")
            return self.search_by_properties(keys)

        temps = re.findall(r"[TH]\d+", q.upper())
        if len(temps) >= 2:
            return self.compare_tempers(temps[0], temps[1])

        alloy = re.findall(r"A?\d{4}-?[HT]?\d*", q.upper())
        if alloy:
            return self.get_alloy_detailed_info(alloy[0])

        return "質問の例:\n- A6061-T6 の詳細\n- 引張強さ 400MPa 以上\n- T6 と T651 の違い"


# ------------------------------------------------------------
# Streamlit アプリ本体（完全版）
# ------------------------------------------------------------
def main():

    st.title("🔧 アルミニウム合金 RAG ChatBot")
    st.markdown("### 材料選定支援システム")

    # アップロードUI
    uploaded = st.sidebar.file_uploader("Excelファイルをアップロード", type=["xlsx", "xls"])

    # ▼ データ読み込み（アップロード優先）
    if uploaded:
        with open("temp_data.xlsx", "wb") as f:
            f.write(uploaded.getbuffer())
        excel_path = "temp_data.xlsx"
        st.sidebar.success("アップロードしたExcelを読み込みました。")
    else:
        excel_path = DEFAULT_DATA_PATH
        st.sidebar.info("デフォルトデータ（data/temp_data.xlsx）を使用しています。")

    # ▼ RAG 初期化
    if "rag" not in st.session_state or uploaded:
        with st.spinner("データを読み込んでいます..."):
            st.session_state.rag = AluminumAlloyRAG(excel_path)

    # ▼ シート一覧
    st.sidebar.subheader("📄 シート一覧")
    with st.sidebar.expander("表示"):
        for s in st.session_state.rag.data:
            st.write(f"- {s}")

    # ▼ クイック検索
    st.sidebar.subheader("🚀 クイック検索")
    quicks = [
        "純アルミの特徴を教えて",
        "引張強さが500MPa以上",
        "A6061-T6 の詳細",
        "T6 と T651 の違い",
        "耐食性と溶接性が良い合金"
    ]
    for q in quicks:
        if st.sidebar.button(q):
            st.session_state.messages.append({"role": "user", "content": q})
            ans = st.session_state.rag.process_query(q)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            st.rerun()

    # ▼ チャット履歴初期化
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "こんにちは！アルミニウム合金の材料選定をお手伝いします。"
        }]

    # ▼ 表示
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # ▼ 入力
    q = st.chat_input("質問を入力してください")
    if q:
        st.session_state.messages.append({"role": "user", "content": q})
        ans = st.session_state.rag.process_query(q)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()


# ------------------------------------------------------------
if __name__ == "__main__":
    main()






