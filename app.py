# ------------------------------------------------------------
# アルミニウム合金 RAG ChatBot - 完全版フル機能 / 安全動作版
# ------------------------------------------------------------

import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Optional
from pathlib import Path

# GitHub に置くデフォルトデータのパス
DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "temp_data.xlsx"

# ページ設定
st.set_page_config(
    page_title="アルミニウム合金 RAG ChatBot",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ------------------------------------------------------------
# CSS
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
    h1 { color: #1976D2; }
    .info-box {
        background-color: #e8f4f8;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2196F3;
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# RAG クラス
# ------------------------------------------------------------
class AluminumAlloyRAG:

    def __init__(self, excel_path: str):
        self.data = {}
        self.all_alloys = {}
        self.series_info = {}
        self.mechanical_table = None

        # 調質の辞書
        self.temper_descriptions = {
            'T6': '溶体化処理後、人工時効硬化処理を施したもの。',
            'T651': 'T6に加え、残留応力除去のため引張処理。',
            'T3': '溶体化→冷間加工→自然時効。',
            'T4': '溶体化→自然時効。',
            'T5': '高温加工後に人工時効硬化。',
            'O': '焼なまし材で最も柔らかい。',
            'H': '加工硬化材。H12〜H18など。',
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
        """数値以外の Alloy（例：6N01(6005C)）にも対応する安全な合金名生成"""
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
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                df.columns = df.columns.str.strip()
                self.data[sheet_name] = df
        except Exception as e:
            st.error(f"❌ ファイル読み込みエラー: {e}")

    # --------------------------------------------------------
    # 全シート走査
    # --------------------------------------------------------
    def parse_all_sheets(self):
        for sheet_name, df in self.data.items():
            cols = df.columns.tolist()
            alloy_col = None
            for col in cols:
                if any(k in str(col).lower() for k in ['合金', 'alloy', '材料']):
                    alloy_col = col
                    break
            if alloy_col:
                for _, row in df.iterrows():
                    name = str(row.get(alloy_col, '')).strip()
                    if name and name.lower() != 'nan':
                        if name not in self.all_alloys:
                            self.all_alloys[name] = []
                        self.all_alloys[name].append({
                            'sheet': sheet_name,
                            'data': row.to_dict()
                        })

    # --------------------------------------------------------
    # 系列情報 & 機械特性テーブル
    # --------------------------------------------------------
    def build_indexes(self):
        self.mechanical_table = self.data.get("aluminum_handbook_table")

        series_sheet = self.data.get("アルミニウム合金の特性")
        if series_sheet is not None:
            for _, row in series_sheet.iterrows():
                name = row.get('合金系')
                if isinstance(name, str) and '系' in name:
                    m = re.search(r'(\d{4})', name)
                    if m:
                        series = int(m.group(1)) // 1000 * 1000
                        self.series_info[series] = {
                            'name': name.replace('\n', ' '),
                            'overview': row.get('概要', ''),
                            'features': row.get('代表的な特性（強度、溶接性、耐食性）', '')
                        }

    # --------------------------------------------------------
    # 引張強さ検索
    # --------------------------------------------------------
    def get_alloy_by_strength(self, min_strength: float):
        response = f"## 🔍 引張強さ {min_strength} MPa 以上の合金\n\n"
        results = []

        if self.mechanical_table is not None:
            df = self.mechanical_table
            for _, row in df.iterrows():
                try:
                    strength = float(row['引張強さ (MPa)'])
                    if strength >= min_strength:
                        results.append({
                            'alloy': self.safe_alloy_format(row['Alloy'], row['Temper']),
                            'strength': strength,
                            'series': row['系列'],
                            'row': row
                        })
                except:
                    continue

        if not results:
            return response + "該当する合金が見つかりませんでした。"

        results.sort(key=lambda x: x['strength'], reverse=True)

        for r in results[:10]:
            response += f"### ✨ {r['alloy']}\n"
            response += f"- 引張強さ: {r['strength']} MPa\n"
            for key, val in r['row'].items():
                if pd.notna(val) and key not in ['Alloy', 'Temper', '引張強さ (MPa)']:
                    response += f"- **{key}**: {val}\n"
            response += "\n"

        return response

    # --------------------------------------------------------
    # 純アルミ
    # --------------------------------------------------------
    def get_pure_aluminum_info(self):
        response = "## 🥈 純アルミニウム（1000系）\n\n"

        info = self.series_info.get(1000)
        if info:
            response += f"### {info['name']}\n"
            if info['overview']:
                response += f"- 概要: {info['overview']}\n"
            if info['features']:
                response += f"- 特性: {info['features']}\n"
            response += "\n"

        if self.mechanical_table is not None:
            df = self.mechanical_table[self.mechanical_table['系列'] == 1000]
            if not df.empty:
                response += "### 代表的な純アルミ合金\n"
                for _, row in df.iterrows():
                    response += f"- {self.safe_alloy_format(row['Alloy'], row['Temper'])}\n"

        return response

    # --------------------------------------------------------
    # 特定合金の詳細表示
    # --------------------------------------------------------
    def get_alloy_detailed_info(self, alloy: str):
        """特定の合金の詳細情報（系列説明 + 機械特性）"""
        import re
        response = f"## 📋 {alloy.upper()} の詳細\n\n"

        # 質問から「合金番号」と「指定された調質（あれば）」を抽出
        # 例: A6061-T6 -> num = "6061", req_temper = "T6"
        m = re.match(r'[Aa]?(\d{4})(?:-?([A-Z]\d+))?', alloy.upper())
        if m:
            alloy_num = m.group(1)          # "6061"
            req_temper = m.group(2) or ""   # "T6" または ""
        else:
            alloy_num = alloy.upper().replace("A", "").replace("-", "")
            req_temper = ""

        found = False

        # まずは aluminum_handbook_table から検索
        if self.mechanical_table is not None:
            for _, row in self.mechanical_table.iterrows():
                if str(row['Alloy']).zfill(4) != alloy_num:
                    continue

                # 質問に調質が指定されている場合は Temper も一致させる
                if req_temper and str(row['Temper']).upper() != req_temper:
                    continue

                found = True
                series = row['系列']

                response += "### 📊 機械的性質（aluminum_handbook_table）\n"
                response += f"- 合金記号: A{int(row['Alloy']):04d}\n"
                response += f"- 調質: {row['Temper']}\n"
                response += f"- 引張強さ: {row['引張強さ (MPa)']} MPa\n"
                response += f"- 耐力: {row['耐力 (MPa)']} MPa\n"
                response += f"- 伸び: {row['伸び (%)']} %\n"
                response += f"- 疲れ強さ: {row['疲れ強さ (MPa)']} MPa\n"
                response += f"- 強度ランク: {row['強度ランク']}\n"
                response += (
                    f"- 耐食性: {row['耐食性']} / 溶接性: {row['溶接性']} / "
                    f"切削性: {row['切削性']} / 成形性: {row['成形性']}\n"
                )
                if pd.notna(row.get('備考', '')):
                    response += f"- 備考: {row['備考']}\n"
                response += "\n"

                # 系列説明
                if series in self.series_info:
                    info = self.series_info[series]
                    response += f"### 🧾 系列 {series} の概要\n"
                    response += f"- 系列名: {info['name']}\n"
                    if info['overview']:
                        response += f"- 概要: {info['overview']}\n"
                    if info['features']:
                        response += f"- 特性の要点: {info['features']}\n"
                    response += "\n"

            # 調質指定がある場合は、ここまでで十分なので
            if found and req_temper:
                return response

        # 他シートも走査（従来どおり）
        for sheet_name, df in self.data.items():
            for _, row in df.iterrows():
                row_text = " ".join([str(v) for v in row.values if pd.notna(v)]).upper()
                if alloy_num in row_text:
                    found = True
                    response += f"### 📄 {sheet_name}\n"
                    for col, value in row.items():
                        if pd.notna(value) and str(value).strip() and str(value) != 'nan':
                            response += f"- **{col}**: {value}\n"
                    response += "\n"

        if not found:
            response += "⚠️ 該当する合金の詳細情報が見つかりませんでした。\n"

        return response


    # --------------------------------------------------------
    # 調質比較
    # --------------------------------------------------------
    def compare_tempers(self, t1, t2):
        t1, t2 = t1.upper(), t2.upper()
        response = f"## 🔄 {t1} と {t2} の違い\n\n"

        # 説明文
        for t in [t1, t2]:
            response += f"### {t}\n"
            if t in self.temper_descriptions:
                response += f"- {self.temper_descriptions[t]}\n\n"

        return response

    # --------------------------------------------------------
    # 切削加工が難しい材料
    # --------------------------------------------------------
    def get_difficult_machining_alloys(self):
        if self.mechanical_table is None:
            return "切削性データがありません。"

        df = self.mechanical_table
        target = df[(df['強度ランク'] == '高') & (df['切削性'] != 'A')]

        if target.empty:
            return "難加工材は見つかりませんでした。"

        response = "## 🔍 切削加工が難しい合金\n\n"

        for _, row in target.iterrows():
            a = self.safe_alloy_format(row['Alloy'], row['Temper'])
            response += f"- {a} | 切削性: {row['切削性']}\n"

        return response

    # --------------------------------------------------------
    # search_by_properties（安全版）
    # --------------------------------------------------------
    def search_by_properties(self, keywords: list):
        response = "## 🔎 検索結果\n\n"

        # 系列
        series_hit = set()
        for series, info in self.series_info.items():
            text = f"{info['name']} {info['overview']} {info['features']}".lower()
            if all(k.lower() in text for k in keywords):
                series_hit.add(series)

        # 合金
        alloy_hit = []
        if self.mechanical_table is not None:
            for _, row in self.mechanical_table.iterrows():
                text = " ".join([str(v) for v in row.values]).lower()
                if all(k.lower() in text for k in keywords):
                    alloy_hit.append(row)

        if not series_hit and not alloy_hit:
            return response + "❌ 該当する合金がありません。"

        # 系列レベル
        for series in sorted(series_hit):
            info = self.series_info[series]
            response += f"### {info['name']}\n"
            if info['overview']:
                response += f"- 概要: {info['overview']}\n"
            if info['features']:
                response += f"- 特性: {info['features']}\n"

            df_s = self.mechanical_table[self.mechanical_table['系列'] == series]
            sample = ", ".join(sorted([
                self.safe_alloy_format(a, t)
                for a, t in zip(df_s['Alloy'], df_s['Temper'])
            ]))
            response += f"- 代表合金: {sample}\n\n"

        # 合金レベル
        if alloy_hit:
            response += "### 🔧 該当する代表合金\n"
            for row in alloy_hit[:10]:
                label = self.safe_alloy_format(row['Alloy'], row['Temper'])
                response += f"- {label} | 耐食性: {row['耐食性']} / 溶接性: {row['溶接性']} / 切削性: {row['切削性']}\n"
            response += "\n"

        return response

    # --------------------------------------------------------
    # メイン振り分け
    # --------------------------------------------------------
    def process_query(self, query: str):
        q = query.lower()

        # 純アルミ
        if "純アルミ" in q or "1000系" in q:
            return self.get_pure_aluminum_info()

        # 引張強さ
        if "引張" in q or ("強度" in q and "切削" not in q):
            nums = re.findall(r"\d+", query)
            val = int(nums[0]) if nums else 400
            return self.get_alloy_by_strength(val)

        # 切削
        if "切削" in q:
            if any(w in q for w in ["難", "むずか", "悪い", "困難"]):
                return self.get_difficult_machining_alloys()
            return self.search_by_properties(["切削"])

        # 耐食性 / 溶接性
        if "耐食" in q or "溶接" in q:
            keys = []
            if "耐食" in q:
                keys.append("耐食")
            if "溶接" in q:
                keys.append("溶接")
            return self.search_by_properties(keys)

        # 調質 T6-T651
        temps = re.findall(r"[TH]\d+", query.upper())
        if len(temps) >= 2:
            return self.compare_tempers(temps[0], temps[1])

        # 合金記号
        pat = r"A?\d{4}-?[HT]?\d*"
        m = re.findall(pat, query)
        if m:
            return self.get_alloy_detailed_info(m[0])

        # デフォルト案内
        return """
## 💡 使い方の例
- 純アルミの特徴を教えて
- 引張強さが400MPa以上の合金
- 耐食性と溶接性が良い合金
- A6061-T6 の詳細
- T6 と T651 の違い
"""


# ------------------------------------------------------------
# Streamlit アプリ
# ------------------------------------------------------------
def main():
    st.title("🔧 アルミニウム合金 RAG ChatBot")
    st.markdown("### 材料選定支援システム")

    uploaded_file = st.sidebar.file_uploader(
        "Excelファイルをアップロードしてください",
        type=["xlsx", "xls"]
    )

    if uploaded_file is not None:

        with open("temp_data.xlsx", "wb") as f:
            f.write(uploaded_file.getbuffer())

        if "rag" not in st.session_state:
            with st.spinner("データを読み込んでいます..."):
                st.session_state.rag = AluminumAlloyRAG("temp_data.xlsx")
        # シート一覧を表示
        st.sidebar.markdown("---")
        st.sidebar.subheader("📄 シート一覧")

        with st.sidebar.expander("シート一覧を表示"):
            for sheet_name in st.session_state.rag.data.keys():
                st.write(f"- {sheet_name}")

        st.sidebar.markdown("---")

        st.sidebar.success("📁 データ読み込み完了")

        st.sidebar.markdown("---")

        # クイック検索
        st.sidebar.subheader("🚀 クイック検索")
        queries = [
            "純アルミの特徴を教えて",
            "引張強さが500MPa以上",
            "A6061-T6 の詳細",
            "T6 と T651 の違い",
            "耐食性と溶接性が良い合金"
        ]

        for q in queries:
            if st.sidebar.button(q):
                st.session_state.messages.append({"role": "user", "content": q})
                res = st.session_state.rag.process_query(q)
                st.session_state.messages.append({"role": "assistant", "content": res})
                st.rerun()

    else:
        st.warning("Excelファイルをアップロードしてください")

    # チャット
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "こんにちは！アルミニウム合金の材料選定をお手伝いします。"
        }]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if uploaded_file is not None:
        query = st.chat_input("質問を入力してください")
        if query:
            st.session_state.messages.append({"role": "user", "content": query})
            res = st.session_state.rag.process_query(query)
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.rerun()


if __name__ == "__main__":
    main()


