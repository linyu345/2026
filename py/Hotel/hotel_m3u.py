import os
import re
import requests
from datetime import datetime, timezone, timedelta

# 配置
INPUT_URL = "https://raw.githubusercontent.com/linyu345/2026/main/py/Hotel/hotel.txt"  # 远程 hotel.txt
OUTPUT_DIR = "py/Hotel"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "hotel.m3u")  # 生成的 M3U 文件路径

# 台标基础地址
LOGO_BASE = "https://gcore.jsdelivr.net/gh/kenye201/TVlog/img/"

def get_logo_url(ch_name):
    """直接根据频道名生成台标 URL（无预设映射）"""
    name = ch_name.strip()
    
    # 去除常见后缀和干扰词
    name = re.sub(r"[ -_]?(HD|高清|4K|超清|超高清|PLUS|\+|综合|财经|综艺|体育|国际|电影|少儿|戏曲|音乐|纪录|科教|新闻|奥运)", 
                  "", name, flags=re.IGNORECASE)
    
    # 清理空格、特殊字符
    name = name.replace(" ", "").replace("&", "").replace("-", "").replace("（", "").replace("）", "").replace("(", "").replace(")", "")
    
    # 对于 CCTV 开头的频道，尝试提取数字（如 CCTV1综合 -> CCTV1）
    if name.startswith("CCTV"):
        match = re.search(r"CCTV(\d+)", name)
        if match:
            name = "CCTV" + match.group(1)
    
    filename = name + ".png"
    return LOGO_BASE + filename

def main():
    print(f"正在下载 hotel.txt: {INPUT_URL}")
    
    try:
        response = requests.get(INPUT_URL, timeout=30)
        response.raise_for_status()
        content = response.text
        print(f"下载成功，行数: {len(content.splitlines())}")
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return

    # 解析 hotel.txt
    channels = []
    current_group = "未分类"
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ",#genre#" in line:
            current_group = line.split(",")[0].strip()
            continue
        if "," in line:
            parts = line.split(",", 1)
            ch_name = parts[0].strip()
            url = parts[1].strip()
            if url:
                channels.append((ch_name, url, current_group))

    if not channels:
        print("❌ 没有找到任何频道")
        return

    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 生成 M3U
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
        f.write('#EXTM3U x-tvg-url="https://live.fanmingming.cn/e.xml"\n')
        f.write(f'# 更新时间: {beijing_now} (北京时间)\n\n')

        current_group = None
        for ch_name, url, group in channels:
            if group != current_group:
                f.write(f"{group},#genre#\n")
                current_group = group

            logo = get_logo_url(ch_name)
            f.write(f'#EXTINF:-1 tvg-name="{ch_name}" tvg-logo="{logo}" group-title="{group}",{ch_name}\n')
            f.write(f"{url}\n\n")

    print(f"✅ 已生成 {OUTPUT_FILE}，共 {len(channels)} 个频道")
    print(f" - 台标来源: {LOGO_BASE}（直接拼接，无预设映射）")

if __name__ == "__main__":
    main()
