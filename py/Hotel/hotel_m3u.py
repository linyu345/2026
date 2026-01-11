import os
import re
import requests
from datetime import datetime, timezone, timedelta

# 配置
INPUT_URL = "https://raw.githubusercontent.com/linyu345/2026/main/py/Hotel/hotel.txt"  # 远程 hotel.txt
OUTPUT_FILE = "hotel.m3u"  # 生成的 M3U 文件名

# 台标基础地址
LOGO_BASE = "https://gcore.jsdelivr.net/gh/kenye201/TVlog/img/"

# 频道分类（与 hotel.py 保持一致）
CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17",
        "风云剧场", "怀旧剧场", "第一剧场", "风云音乐", "兵器科技", "世界地理", "发现之旅", "风云足球",
        "央视台球", "高尔夫网球", "女性时尚", "央视文化精品", "卫生健康", "电视指南", "老故事", "中学生",
        "书法频道", "国学频道", "环球奇观", "CETV1", "CETV2", "CETV3", "CETV4"
    ],
    "卫视频道": [
        "北京卫视", "安徽卫视", "东方卫视", "浙江卫视", "江苏卫视", "江西卫视", "天津卫视", "深圳卫视",
        "广东卫视", "广西卫视", "东南卫视", "海南卫视", "三沙卫视", "厦门卫视", "河南卫视", "河北卫视",
        "湖南卫视", "湖北卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "山东卫视", "山东教育卫视",
        "辽宁卫视", "黑龙江卫视", "吉林卫视", "延边卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视",
        "农林卫视", "甘肃卫视", "青海卫视", "新疆卫视", "兵团卫视", "西藏卫视", "安多卫视", "康巴卫视",
        "大湾区卫视", "早期教育"
    ],
    # 其他分类可根据需要继续添加...
}

# 台标特殊映射（别名 -> 标准名）
CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV1-综合", "CCTV-1 综合", "CCTV-1综合", "CCTV1HD", "CCTV-1高清", "CCTV-1HD"],
    "CCTV2": ["CCTV-2", "CCTV2-财经", "CCTV-2 财经", "CCTV-2财经", "CCTV2HD", "CCTV-2高清"],
    "CCTV3": ["CCTV-3", "CCTV3-综艺", "CCTV-3 综艺", "CCTV-3综艺", "CCTV3HD", "CCTV-3高清"],
    "CCTV4": ["CCTV-4", "CCTV4-国际", "CCTV-4 中文国际", "CCTV-4中文国际", "CCTV4HD"],
    "CCTV5": ["CCTV-5", "CCTV5-体育", "CCTV-5 体育", "CCTV-5体育", "CCTV5HD", "CCTV-5高清"],
    # ... 其他映射可继续补充（从你的 hotel.py 里复制过来）
    # 示例补充
    "湖南卫视": ["湖南卫视高清"],
    "广东珠江": ["珠江高清"],
}

def get_logo_url(ch_name):
    """生成台标 URL"""
    name = ch_name.strip()
    # 去除常见后缀
    name = re.sub(r"[ -_]HD|高清|4K|超清|超高清", "", name, flags=re.IGNORECASE)
    name = name.replace(" ", "").replace("&", "")
    
    # 使用映射表取标准名
    target_name = ch_name
    for std_name, aliases in CHANNEL_MAPPING.items():
        if ch_name in aliases or name in [a.replace(" ", "") for a in aliases]:
            target_name = std_name
            break
    
    # 取第一个匹配的别名作为文件名
    filename = target_name + ".png"
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

    # 读取并解析 hotel.txt（假设格式为 频道名,URL）
    channels = []
    current_group = "未分类"
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ",#genre#" in line:
            # 分类标题行
            current_group = line.split(",")[0].strip()
            continue
        if "," in line:
            parts = line.split(",", 1)
            ch_name = parts[0].strip()
            url = parts[1].strip() if len(parts) > 1 else ""
            if url:
                channels.append((ch_name, url, current_group))

    if not channels:
        print("❌ 没有找到任何频道")
        return

    # 生成 M3U
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
        f.write(f'#EXTM3U x-tvg-url="https://live.fanmingming.cn/e.xml"\n')
        f.write(f'# 更新时间: {beijing_now} (北京时间)\n\n')

        current_group = "未分类"
        for ch_name, url, group in channels:
            if group != current_group:
                f.write(f"{group},#genre#\n")
                current_group = group

            logo = get_logo_url(ch_name)
            title = ch_name
            f.write(f'#EXTINF:-1 tvg-name="{ch_name}" tvg-logo="{logo}" group-title="{group}",{title}\n')
            f.write(f"{url}\n\n")

    print(f"✅ 已生成 {OUTPUT_FILE}，共 {len(channels)} 个频道")
    print(f" - 台标来源: {LOGO_BASE}")
    print(f" - 支持分组: {', '.join(CHANNEL_CATEGORIES.keys())}")

if __name__ == "__main__":
    main()
