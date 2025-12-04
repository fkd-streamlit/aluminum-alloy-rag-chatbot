# aluminum-alloy-rag-chatbot
"RAG-based material selection assistant for aluminum alloys."
# 🔧 アルミニウム合金 RAG ChatBot  
Material Selection Support System for Aluminum Alloys (RAG-based)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🌐 公開アプリ（Streamlit）
👉 **https://YOUR_APP_URL_HERE.streamlit.app/**

ブラウザだけで動作する、**アルミニウム合金の材料選定サポートシステム**です。  
Excel をアップロードすれば、独自データで材料検索・特性比較・シリーズ分析などができます。

---

## 🧠 主な機能

### 🔍 1. 合金特性の自動検索（RAG + Excel）
- 合金番号から詳細情報を検索  
- 系列情報（1000〜7000系）を自動整理  
- 機械特性（引張強さ・耐力・伸び・加工性など）をワンクリック表示  

### 🚀 2. クイック検索
- 純アルミの特徴  
- 引張強さ◯◯MPa以上  
- A6061-T6 などの詳細  
- T6 と T651 の違い  
- 耐食性・溶接性が良い材料  

### 📤 3. Excel アップロード対応
独自フォーマットでも読み込める柔軟なパーサーを搭載。  
業務データをそのまま使って検索できます。

---

## 🛠️ 技術構成
- **Python 3.10+**
- **Streamlit**
- **pandas**
- **RAG（Excel ベースの検索エンジン）**
- コンテナ内でも動作する**軽量構造**

---

## 📁 リポジトリ構成

