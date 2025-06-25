# regulations_moea.py

import streamlit as st
import email
from bs4 import BeautifulSoup
import html, re, base64

st.set_page_config(page_title="法規 MHTML 上傳工具", layout="wide")
st.title("📘 法規 MHTML 條文擷取與格式轉換工具")
st.markdown("請上傳從 [經濟部法規網站](https://law.moea.gov.tw) 下載的 `.mhtml` 檔案，系統會解析並生成互動版條文 HTML。")

uploaded_file = st.file_uploader("📂 上傳 .mhtml 檔案", type=["mhtml"])
if uploaded_file is None:
    st.stop()

# === 解 MHTML 檔案 ===
msg = email.message_from_bytes(uploaded_file.read())
html_parts = [part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
              for part in msg.walk() if part.get_content_type() == 'text/html']

if not html_parts:
    st.error("❌ 無法解析 MHTML，請確認上傳的是正確格式。")
    st.stop()

soup = BeautifulSoup(html_parts[0], 'lxml')

# === 擷取法規基本資料 ===
info = {
    '法規名稱': '',
    '公發布日': '',
    '修正日期': '',
    '發文字號': '',
    '法規體系': ''
}
table = soup.find('table')
if table:
    for tr in table.find_all('tr'):
        th = tr.find('th')
        td = tr.find('td')
        if th and td:
            k = th.get_text(strip=True)
            v = td.get_text(strip=True)
            for key in info:
                if key in k:
                    info[key] = v

# === 條文擷取（正確處理一～九十九條） ===
law_data = []
content_div = soup.find("div", id="ctl00_cp_content_divContent")
if content_div:
    raw_text = content_div.get_text("\n", strip=True)
    pattern = re.compile(r'\s*([一二三四五六七八九十百千〇]+)、')
    matches = list(pattern.finditer(raw_text))

    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        segment = raw_text[start:end].strip()
        if len(segment) >= 10:
            law_data.append({
                '章': '',
                '章節': '',
                '條': '',
                '條文內容': segment
            })

# === HTML 產出 ===
title = info['法規名稱']
meta = f"公布：{info['公發布日']} ／ 修正：{info['修正日期']} ／ 發文字號：{info['發文字號']} ／ 體系：{info['法規體系']}"
filename = f"{title}.html"

html_string = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: '微軟正黑體'; margin: 20px; }}
table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
th, td {{ border: 1px solid #aaa; padding: 8px; text-align: left; vertical-align: top; word-break: break-word; }}
thead th {{ background: #eee; position: sticky; top: 0; z-index: 1; }}
tbody tr:nth-child(even) {{ background-color: #f9f9f9; }}
tbody tr:hover {{ background-color: #eef; }}
textarea {{ width: 100%; height: 80px; padding: 4px; box-sizing: border-box; }}
select:disabled, textarea:disabled {{ background-color: #f5f5f5; color: #333; }}
.button {{ padding: 10px 15px; margin: 10px; background: #4CAF50; color: white; border: none; cursor: pointer; }}
</style>
<script>
let confirmed = false;
function toggleEdit() {{
  confirmed = false;
  document.querySelectorAll('select, textarea').forEach(el => el.disabled = false);
}}
function confirmEdit() {{
  confirmed = true;
  document.querySelectorAll('select, textarea').forEach(el => el.disabled = true);
}}
function downloadModifiedHTML() {{
  if (!confirmed) return alert('請先完成更新');
  document.querySelectorAll('tr').forEach((row) => {{
    row.querySelectorAll('select').forEach(sel => sel.setAttribute('data-selected', sel.value));
    const txt = row.querySelector('textarea');
    if (txt) txt.setAttribute('data-content', txt.value);
  }});
  const fileName = prompt('請輸入儲存檔名：', '{title}.html') || '{title}.html';
  const blob = new Blob(['<!DOCTYPE html>' + document.documentElement.outerHTML], {{ type: 'text/html' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}}
window.onload = () => {{
  document.querySelectorAll('tr').forEach((row) => {{
    row.querySelectorAll('select').forEach(sel => sel.value = sel.getAttribute('data-selected') || '否');
    const txt = row.querySelector('textarea');
    if (txt) txt.value = txt.getAttribute('data-content') || '';
  }});
}}
</script></head><body>
<h2>{title}</h2>
<p><strong>{meta}</strong></p>
<table><thead><tr><th>章</th><th>章節</th><th width="700wh">條文內容</th><th>定義條文</th><th>是否適用</th><th>是否符合</th><th width="300wh">說明</th></tr></thead><tbody>
'''

for row in law_data:
    content = html.escape(row['條文內容']).replace('\n', '<br>')
    html_string += f'''<tr>
    <td>{row['章']}</td><td>{row['章節']}</td><td>{content}</td>
    <td><select data-selected="否" disabled><option>否</option><option>是</option></select></td>
    <td><select data-selected=" " disabled><option> </option><option>適用</option><option>不適用</option></select></td>
    <td><select data-selected=" " disabled><option> </option><option>符合</option><option>不符合</option></select></td>
    <td><textarea data-content="" disabled></textarea></td></tr>'''

html_string += '''</tbody></table>
<div><button class="button" onclick="toggleEdit()">更新</button>
<button class="button" onclick="confirmEdit()">完成更新</button>
<button class="button" onclick="downloadModifiedHTML()">下載更新版本</button>
</div></body></html>'''

# 下載按鈕
b64 = base64.b64encode(html_string.encode()).decode()
st.success(f"✅ 已成功解析：{title}")
st.download_button("⬇️ 下載 HTML 檔案", data=html_string, file_name=filename, mime="text/html")
