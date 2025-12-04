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
    def get_alloy_by_strength(self, min_strength):
        res = f"## 引張強さ {min_strength} MPa 以上の合金\n\n"
        hits = []

        if self.mechanical_table is not None:
            for _, r in self.mechanical_table.iterrows():
                try:
                    s = float(r["引張強さ (MPa)"])
                    if s >= min_strength:
                        hits.append((s, r))
                except:
                    pass

        if not hits:
            return res + "該当合金なし"

        hits.sort(reverse=True)
        for s, r in hits[:10]:
            name = self.safe_alloy_format(r["Alloy"], r["Temper"])
            res += f"### {name}\n- 引張強さ: {s} MPa\n\n"

        return res

    def get_pure_aluminum_info(self):
        res = "## 🥈 純アルミ（1000系）\n\n"
        info = self.series_info.get(1000)
        if info:
            res += f"- {info['name']}\n- 概要: {info['overview']}\n- 特性: {info['features']}\n\n"
        return res

    def get_alloy_detailed_info(self, alloy):
        res = f"## 📋 {alloy.upper()} の詳細\n\n"
        alloy_num = re.findall(r"\d{4}", alloy)
        if not alloy_num:
            return res + "番号を認識できませんでした。"
        alloy_num = alloy_num[0]

        found = False
        if self.mechanical_table is not None:
            for _, r in self.mechanical_table.iterrows():
                if str(r["Alloy"]).zfill(4) == alloy_num:
                    found = True
                    name = self.safe_alloy_format(r["Alloy"], r["Temper"])
                    res += f"### {name}\n"
                    for k, v in r.items():
                        if pd.notna(v):
                            res += f"- **{k}**: {v}\n"
                    res += "\n"

        if not found:
            res += "該当データなし\n"

        return res

    def compare_tempers(self, t1, t2):
        res = f"## 🔄 {t1} と {t2} の違い\n\n"
        for t in [t1, t2]:
            res += f"### {t}\n- {self.temper_descriptions.get(t, '情報なし')}\n\n"
        return res

    def search_by_properties(self, keys):
        res = "## 特性検索\n\n"
        hits = []
        df = self.mechanical_table
        if df is None:
            return "データなし"

        for _, r in df.iterrows():
            text = " ".join([str(v) for v in r.values]).lower()
            if all(k.lower() in text for k in keys):
                hits.append(r)

        if not hits:
            return res + "該当合金なし"

        for r in hits[:10]:
            name = self.safe_alloy_format(r["Alloy"], r["Temper"])
            res += f"- {name}\n"

        return res

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





