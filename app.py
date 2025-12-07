# ------------------------------------------------------------
# アルミニウム合金 RAG ChatBot - 完全版フル機能 / 安全動作版（2025リビルド）
# ------------------------------------------------------------

import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Optional
from pathlib import Path

# GitHub に置くデフォルトデータのパス
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
# CSS デザイン
# ------------------------------------------------------------
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# RAG クラス
# ------------------------------------------------------------


class AluminumAlloyRAG:
    def __init__(self, excel_path: str):
        self.data: Dict[str, pd.DataFrame] = {}
        self.series_info: Dict[int, Dict[str, str]] = {}
        self.all_alloys: Dict[str, List[Dict]] = {}
        self.mechanical_table: Optional[pd.DataFrame] = None
        self.heat_treatment_dict = {}


        # 調質の概要
        self.temper_descriptions = {
            "T6": "溶体化処理後、人工時効硬化処理を施したもの。",
            "T651": "T6に加え、残留応力除去のため引張処理。",
            "T3": "溶体化→冷間加工→自然時効。",
            "T4": "溶体化→自然時効。",
            "T5": "高温加工後に人工時効硬化。",
            "O": "焼なまし材で最も柔らかい。",
            "H12": "1/4硬化",
            "H14": "1/2硬化",
            "H16": "3/4硬化",
            "H18": "完全硬化",
        }

        self.load_data(excel_path)
        self.parse_all_sheets()
        self.build_indexes()
        # ---------------------------
        # 曖昧検索用・同義語辞書
        # ---------------------------
        self.semantic_dict = {
            "8000系": ["8000", "al-li", "アルミリチウム", "aluminum lithium", "al li"],
            "7000系": ["超高強度", "航空機", "7075", "7050"],
            "6000系": ["汎用", "押出", "6061", "6063"],
            "1000系": ["純アルミ", "純アルミニウム"],

            "軽量": ["軽い", "低密度", "軽量化"],
            "高強度": ["強い", "高強度", "引張"],
            "耐食": ["耐食", "耐食性", "腐食"],
            "溶接": ["溶接", "溶接性"],
            "切削": ["切削", "加工しやすい"],

            "航空": ["航空", "宇宙", "ロケット", "機体"],
            "構造材": ["構造", "フレーム", "骨組み"]
        }


    # --------------------------------------------------------
    # 安全な合金名フォーマット
    # --------------------------------------------------------
    def safe_alloy_format(self, alloy_value, temper) -> str:
        s = str(alloy_value)
        nums = re.findall(r"\d+", s)
        if nums:
            n = int(nums[0])
            return f"A{n:04d}-{temper}"
        return f"{s}-{temper}"

    # --------------------------------------------------------
    # Excel 読み込み
    # --------------------------------------------------------
    def load_data(self, excel_path: str):
        try:
            xls = pd.ExcelFile(excel_path, engine="openpyxl")
            for sheet in xls.sheet_names:
                df = pd.read_excel(excel_path, sheet_name=sheet, engine="openpyxl")
                df.columns = df.columns.str.strip()
                self.data[sheet] = df
        except Exception as e:
            st.error(f"❌ ファイル読み込みエラー: {e}")

    # --------------------------------------------------------
    # 全シート走査して合金名インデックス作成
    # --------------------------------------------------------
    def parse_all_sheets(self):
        for sheet, df in self.data.items():
            for col in df.columns:
                if any(k in str(col).lower() for k in ["合金", "alloy"]):
                    for _, row in df.iterrows():
                        name = str(row[col]).strip()
                        if name and name.lower() != "nan":
                            self.all_alloys.setdefault(name, []).append(
                                {"sheet": sheet, "data": row.to_dict()}
                            )

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
                    m = re.search(r"(\d{4})", name)
                    if m:
                        s = int(m.group(1)) // 1000 * 1000
                        self.series_info[s] = {
                            "name": name.replace("\n", " "),
                            "overview": r.get("概要", ""),
                            "features": r.get(
                                "代表的な特性（強度、溶接性、耐食性）", ""
                            ),
                        }
        # -----------------------------
        # 熱処理（調質）ワークシート
        # -----------------------------
        heat_sheet = self.data.get("熱処理")
        if heat_sheet is not None:
            for _, row in heat_sheet.iterrows():
                symbol = str(row.get("記号", "")).strip().upper()
                if symbol:
                    self.heat_treatment_dict[symbol] = {
                        "定義": str(row.get("定義", "")),
                        "意味": str(row.get("意味", ""))
                    }

    # --------------------------------------------------------
    # 熱処理（調質）情報
    # --------------------------------------------------------
    def get_heat_treatment_info(self, symbol: str) -> str:
        symbol = symbol.upper()
        info = self.heat_treatment_dict.get(symbol)

        if not info:
            return f"❌ 熱処理 {symbol} の情報が見つかりませんでした。"

        res = f"## 🔥 熱処理 {symbol}\n\n"
        if info.get("定義"):
            res += f"- **定義**：{info['定義']}\n"
        if info.get("意味"):
            res += f"- **意味**：{info['意味']}\n"

        return res




    
    # --------------------------------------------------------
    # 純アルミ情報
    # --------------------------------------------------------
    def get_pure_aluminum_info(self) -> str:
        resp = "## 🥈 純アルミニウム（1000系）\n\n"

        info = self.series_info.get(1000)
        if info:
            resp += f"### {info['name']}\n"
            if info["overview"]:
                resp += f"- 概要: {info['overview']}\n"
            if info["features"]:
                resp += f"- 特性の要点: {info['features']}\n"
            resp += "\n"

        if self.mechanical_table is not None:
            df1000 = self.mechanical_table[
                self.mechanical_table["系列"] == 1000
            ]
            if not df1000.empty:
                resp += "### 代表的な純アルミ合金\n"
                for _, row in df1000.iterrows():
                    resp += (
                        f"- {self.safe_alloy_format(row['Alloy'], row['Temper'])}\n"
                    )

        return resp

    # --------------------------------------------------------
    # 引張強さで検索
    # --------------------------------------------------------
    def get_alloy_by_strength(self, min_strength: float) -> str:
        response = f"## 🔍 引張強さ {min_strength} MPa 以上の合金\n\n"
        results = []

        if self.mechanical_table is None:
            return response + "データが読み込まれていません。"

        df = self.mechanical_table

        for _, row in df.iterrows():
            raw_strength = row.get("引張強さ (MPa)", None)

            try:
                strength = float(raw_strength)
            except Exception:
                continue  # 数値でなければスキップ

            if strength >= min_strength:
                results.append(
                    {
                        "alloy": self.safe_alloy_format(
                            row.get("Alloy", ""), row.get("Temper", "")
                        ),
                        "strength": strength,
                        "series": row.get("系列", ""),
                        "row": row,
                    }
                )

        if not results:
            return response + "該当する合金が見つかりませんでした。"

        results.sort(key=lambda x: x["strength"], reverse=True)

        for r in results[:10]:
            response += f"### ✨ {r['alloy']}\n"
            response += f"- 引張強さ: {r['strength']} MPa\n"
            for key, val in r["row"].items():
                if pd.notna(val) and key not in ["Alloy", "Temper", "引張強さ (MPa)"]:
                    response += f"- **{key}**: {val}\n"
            response += "\n"

        return response

    # --------------------------------------------------------
    # 特定合金の詳細表示
    # --------------------------------------------------------
    def get_alloy_detailed_info(self, alloy: str) -> str:
        response = f"## 📋 {alloy.upper()} の詳細\n\n"
        alloy_clean = alloy.upper().replace("A", "").replace("-", "")

        found = False

        # 機械的特性テーブル
        if self.mechanical_table is not None:
            for _, row in self.mechanical_table.iterrows():
                if str(row["Alloy"]).zfill(4) == alloy_clean[:4]:
                    found = True
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
                    if pd.notna(row.get("備考", "")):
                        response += f"- 備考: {row['備考']}\n"
                    response += "\n"
                    # 系列の概要
                    series = row.get("系列", None)
                    if series in self.series_info:
                        info = self.series_info[series]
                        response += f"### 🧾 系列 {series} の概要\n"
                        response += f"- 系列名: {info['name']}\n"
                        if info["overview"]:
                            response += f"- 概要: {info['overview']}\n"
                        if info["features"]:
                            response += f"- 特性の要点: {info['features']}\n"
                        response += "\n"
                    break

        # 他シートも走査
        for sheet, df in self.data.items():
            for _, row in df.iterrows():
                row_text = " ".join(
                    [str(v) for v in row.values if pd.notna(v)]
                ).upper()
                if alloy_clean in row_text:
                    found = True
                    response += f"### 📄 {sheet}\n"
                    for col, val in row.items():
                        if pd.notna(val) and str(val).strip() and str(val) != "nan":
                            response += f"- **{col}**: {val}\n"
                    response += "\n"

        if not found:
            response += "⚠️ 該当する合金の詳細情報が見つかりませんでした。\n"

        return response

    # --------------------------------------------------------
    # 調質比較
    # --------------------------------------------------------
    def compare_tempers(self, t1: str, t2: str) -> str:
        t1, t2 = t1.upper(), t2.upper()
        response = f"## 🔄 {t1} と {t2} の違い\n\n"

        for t in [t1, t2]:
            response += f"### {t}\n"
            if t in self.temper_descriptions:
                response += f"- {self.temper_descriptions[t]}\n"
            response += "\n"

        return response

    # --------------------------------------------------------
    # 特性ベース検索
    # --------------------------------------------------------
    def search_by_properties(self, keywords: List[str]) -> str:
        response = "## 🔎 検索結果\n\n"

        series_hit = set()
        for series, info in self.series_info.items():
            text = f"{info['name']} {info['overview']} {info['features']}".lower()
            if all(k.lower() in text for k in keywords):
                series_hit.add(series)

        alloy_hit = []
        if self.mechanical_table is not None:
            for _, row in self.mechanical_table.iterrows():
                text = " ".join([str(v) for v in row.values]).lower()
                if all(k.lower() in text for k in keywords):
                    alloy_hit.append(row)

        if not series_hit and not alloy_hit:
            return response + "❌ 該当する合金がありません。"

        for series in sorted(series_hit):
            info = self.series_info[series]
            response += f"### {info['name']}\n"
            if info["overview"]:
                response += f"- 概要: {info['overview']}\n"
            if info["features"]:
                response += f"- 特性の要点: {info['features']}\n"

            if self.mechanical_table is not None:
                df_s = self.mechanical_table[self.mechanical_table["系列"] == series]
                sample = ", ".join(
                    sorted(
                        [
                            self.safe_alloy_format(a, t)
                            for a, t in zip(df_s["Alloy"], df_s["Temper"])
                        ]
                    )
                )
                response += f"- 代表合金: {sample}\n\n"

        if alloy_hit:
            response += "### 🔧 該当する代表合金\n"
            for row in alloy_hit[:10]:
                label = self.safe_alloy_format(row["Alloy"], row["Temper"])
                response += (
                    f"- {label} | 耐食性: {row['耐食性']} / "
                    f"溶接性: {row['溶接性']} / 切削性: {row['切削性']}\n"
                )
            response += "\n"

        return response
        
    #--------------------------------------------------------
    # 曖昧検索ワードの正規化
    # --------------------------------------------------------
    def normalize_query(self, query: str) -> List[str]:
        query_l = query.lower()
        keywords = set()

        for canonical, variants in self.semantic_dict.items():
            for v in variants:
                if v.lower() in query_l:
                    keywords.add(canonical)

        tokens = re.findall(r'[一-龥A-Za-z0-9\-]+', query)
        keywords.update(tokens)

        return list(keywords)

    
    # --------------------------------------------------------
    # クエリ振り分け
    # --------------------------------------------------------
    def process_query(self, q: str) -> str:
        text = q.lower()
        expanded_keywords = self.normalize_query(q)

        # --- 熱処理（T6 / T651 / O / H18 など）---
        m = re.search(r"(T\d{1,3}|O|H\d{1,2})", q.upper())
        if m:
            return self.get_heat_treatment_info(m.group(1))

        # 純アルミ
        if "純アルミ" in text or "1000系" in text:
            return self.get_pure_aluminum_info()

        # 引張強さ
        if "引張" in text or ("強度" in text and "切削" not in text):
            nums = re.findall(r"\d+", text)
            val = int(nums[0]) if nums else 400
            return self.get_alloy_by_strength(val)

        # 耐食性 / 溶接性など
        if any(k in expanded_keywords for k in ["耐食", "溶接", "軽量", "高強度", "航空"]):
            return self.search_by_properties(expanded_keywords)

        # 調質比較
        temps = re.findall(r"[TH]\d+", q.upper())
        if len(temps) >= 2:
            return self.compare_tempers(temps[0], temps[1])

        # 特定合金
        alloy = re.findall(r"A?\d{4}-?[HT]?\d*", q.upper())
        if alloy:
            return self.get_alloy_detailed_info(alloy[0])

        # デフォルト
        return (
            "質問の例:\n"
            "- 純アルミの特徴を教えて\n"
            "- 引張強さ 400MPa 以上の合金\n"
            "- 耐食性と溶接性が良い合金\n"
            "- A6061-T6 の詳細\n"
            "- T6 と T651 の違い\n"
        )




# ------------------------------------------------------------
# Streamlit アプリ本体
# ------------------------------------------------------------


def main():
    st.title("🔧 アルミニウム合金 RAG ChatBot")
    st.markdown("### 材料選定支援システム")

    # -------------------------------
    # Excel ファイル選択（アップロード or デフォルト）
    # -------------------------------
    uploaded = st.sidebar.file_uploader(
        "Excelファイルをアップロード", type=["xlsx", "xls"]
    )

    if uploaded is not None:
        # アップロードされたファイルを一時保存
        temp_path = Path("temp_data_uploaded.xlsx")
        with open(temp_path, "wb") as f:
            f.write(uploaded.getbuffer())
        excel_path = str(temp_path)
        st.sidebar.success("アップロードした Excel を読み込みます。")
    else:
        excel_path = str(DEFAULT_DATA_PATH)
        st.sidebar.info("デフォルトデータ（data/temp_data.xlsx）を使用しています。")

    # -------------------------------
    # RAG 初期化（パスが変わったら再読み込み）
    # -------------------------------
    need_reload = False
    if "excel_path" not in st.session_state:
        need_reload = True
    elif st.session_state.excel_path != excel_path:
        need_reload = True

    if need_reload:
        try:
            with st.spinner("データを読み込んでいます..."):
                st.session_state.rag = AluminumAlloyRAG(excel_path)
                st.session_state.excel_path = excel_path
        except Exception as e:
            st.error(f"❌ データ読み込みに失敗しました: {e}")
            return

    rag: AluminumAlloyRAG = st.session_state.rag

    # -------------------------------
    # サイドバー：シート一覧
    # -------------------------------
    st.sidebar.subheader("📄 シート一覧")
    with st.sidebar.expander("表示"):
        for s in rag.data.keys():
            st.write(f"- {s}")

    # -------------------------------
    # サイドバー：クイック検索
    # -------------------------------
    st.sidebar.subheader("🚀 クイック検索")
    quick_queries = [
        "純アルミの特徴を教えて",
        "引張強さが500MPa以上",
        "A6061-T6 の詳細",
        "T6 と T651 の違い",
        "耐食性と溶接性が良い合金",
    ]
    for q in quick_queries:
        if st.sidebar.button(q):
            st.session_state.messages.append({"role": "user", "content": q})
            ans = rag.process_query(q)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            st.rerun()

    # -------------------------------
    # チャット履歴の初期化
    # -------------------------------
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "こんにちは！アルミニウム合金の材料選定をお手伝いします。",
            }
        ]

    # 履歴表示
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # -------------------------------
    # 入力欄
    # -------------------------------
    q = st.chat_input("質問を入力してください")
    if q:
        st.session_state.messages.append({"role": "user", "content": q})
        ans = rag.process_query(q)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()


# ------------------------------------------------------------
if __name__ == "__main__":
    main()





