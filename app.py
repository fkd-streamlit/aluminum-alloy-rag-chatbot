# ------------------------------------------------------------
# アルミニウム合金 RAG ChatBot - 完全版フル機能 / 安全動作版（2025リビルド）
# ------------------------------------------------------------

import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Optional
from pathlib import Path

# ------------------------------------------------------------
# デフォルトExcelパス
# ------------------------------------------------------------
DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "temp_data.xlsx"

# ------------------------------------------------------------
# ページ設定
# ------------------------------------------------------------
st.set_page_config(
    page_title="アルミニウム合金 RAG ChatBot",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# CSS
# ------------------------------------------------------------
st.markdown(
    """
<style>
    .main { background-color: #f8f9fa; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# RAG クラス
# ============================================================
class AluminumAlloyRAG:
    def __init__(self, excel_path: str):
        self.data: Dict[str, pd.DataFrame] = {}
        self.series_info: Dict[int, Dict[str, str]] = {}
        self.all_alloys: Dict[str, List[Dict]] = {}
        self.mechanical_table: Optional[pd.DataFrame] = None
        self.heat_treatment_dict: Dict[str, Dict[str, str]] = {}

        self.temper_descriptions = {
            "T6": "溶体化処理後、人工時効硬化処理を施したもの。",
            "T651": "T6に加え、残留応力除去のため引張処理。",
            "T3": "溶体化→冷間加工→自然時効。",
            "T4": "溶体化→自然時効。",
            "T5": "高温加工後に人工時効硬化。",
            "O": "焼なまし材。",
            "H12": "1/4硬化",
            "H14": "1/2硬化",
            "H16": "3/4硬化",
            "H18": "完全硬化",
        }

        self.semantic_dict = {
            "耐食": ["耐食", "耐食性", "腐食"],
            "溶接": ["溶接", "溶接性"],
            "切削": ["切削", "加工"],
            "軽量": ["軽量", "軽い"],
            "航空": ["航空", "宇宙"],
        }

        self.load_data(excel_path)
        self.build_indexes()

    # --------------------------------------------------------
    def load_data(self, excel_path: str):
        try:
            xls = pd.ExcelFile(excel_path, engine="openpyxl")
            for sheet in xls.sheet_names:
                df = pd.read_excel(excel_path, sheet_name=sheet, engine="openpyxl")
                df.columns = df.columns.str.strip()
                self.data[sheet] = df
        except Exception as e:
            st.error(f"❌ Excel読み込みエラー: {e}")

    # --------------------------------------------------------
    def build_indexes(self):
        self.mechanical_table = self.data.get("aluminum_handbook_table")

        # 系列
        series_sheet = self.data.get("アルミニウム合金の特性")
        if series_sheet is not None:
            for _, r in series_sheet.iterrows():
                name = r.get("合金系")
                if isinstance(name, str) and "系" in name:
                    m = re.search(r"(\d{4})", name)
                    if m:
                        s = int(m.group(1)) // 1000 * 1000
                        self.series_info[s] = {
                            "name": name,
                            "overview": r.get("概要", ""),
                            "features": r.get("代表的な特性（強度、溶接性、耐食性）", ""),
                        }

        # 熱処理
        heat_sheet = self.data.get("熱処理")
        if heat_sheet is not None:
            for _, row in heat_sheet.iterrows():
                symbol = str(row.get("記号", "")).strip().upper()
                if symbol:
                    self.heat_treatment_dict[symbol] = {
                        "定義": str(row.get("定義", "")),
                        "意味": str(row.get("意味", "")),
                    }

    # --------------------------------------------------------
    def safe_alloy_format(self, alloy, temper) -> str:
        nums = re.findall(r"\d+", str(alloy))
        return f"A{int(nums[0]):04d}-{temper}" if nums else f"{alloy}-{temper}"

    # --------------------------------------------------------
    def get_heat_treatment_info(self, symbol: str) -> str:
        info = self.heat_treatment_dict.get(symbol.upper())
        if not info:
            return f"❌ 熱処理 {symbol} の情報が見つかりませんでした。"

        res = f"## 🔥 熱処理 {symbol}\n\n"
        if info["定義"]:
            res += f"- **定義**：{info['定義']}\n"
        if info["意味"]:
            res += f"- **意味**：{info['意味']}\n"
        return res

    # --------------------------------------------------------
    def get_alloy_by_strength(self, min_strength: int) -> str:
        if self.mechanical_table is None:
            return "データ未読み込み"

        res = f"## 🔍 引張強さ {min_strength} MPa 以上\n\n"
        hits = []

        for _, r in self.mechanical_table.iterrows():
            try:
                if float(r["引張強さ (MPa)"]) >= min_strength:
                    hits.append(r)
            except:
                continue

        if not hits:
            return res + "該当なし"

        for r in hits[:10]:
            res += f"- {self.safe_alloy_format(r['Alloy'], r['Temper'])} : {r['引張強さ (MPa)']} MPa\n"

        return res

    # --------------------------------------------------------
    def normalize_query(self, q: str) -> List[str]:
        ql = q.lower()
        out = set()
        for k, vals in self.semantic_dict.items():
            for v in vals:
                if v in ql:
                    out.add(k)
        return list(out)

    # --------------------------------------------------------
    def process_query(self, q: str) -> str:
        ql = q.lower()

        # 🔥 熱処理最優先
        m = re.search(r"\b(T\d+|O|H\d+)\b", q.upper())
        if m:
            return self.get_heat_treatment_info(m.group(1))

        # 強度
        if "引張" in ql:
            nums = re.findall(r"\d+", q)
            return self.get_alloy_by_strength(int(nums[0]) if nums else 400)

        return (
            "💡 質問例:\n"
            "- T6とは？\n"
            "- 引張強さ 500MPa 以上\n"
            "- A6061-T6 の詳細\n"
        )


# ============================================================
# Streamlit UI
# ============================================================
def main():
    st.title("🔧 アルミニウム合金 RAG ChatBot")
    st.markdown("### 材料選定支援システム")

    uploaded = st.sidebar.file_uploader("Excelアップロード", type=["xlsx"])

    excel_path = DEFAULT_DATA_PATH
    if uploaded:
        tmp = Path("uploaded.xlsx")
        tmp.write_bytes(uploaded.getbuffer())
        excel_path = tmp

    if "rag" not in st.session_state or st.session_state.get("excel_path") != str(excel_path):
        st.session_state.rag = AluminumAlloyRAG(str(excel_path))
        st.session_state.excel_path = str(excel_path)

    rag: AluminumAlloyRAG = st.session_state.rag

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "こんにちは！質問してください。"}
        ]

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    q = st.chat_input("質問を入力")
    if q:
        st.session_state.messages.append({"role": "user", "content": q})
        ans = rag.process_query(q)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()


if __name__ == "__main__":
    main()














