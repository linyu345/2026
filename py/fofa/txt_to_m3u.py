import os
import re
import requests

# 输入输出文件（改为远程 GitHub Raw URL）
INPUT_URL = "https://raw.githubusercontent.com/linyu345/2026/refs/heads/main/py/fofa/IPTV.txt"
OUTPUT_FILE = "IPTV.m3u"

# 台标和 EPG（保持不变）
LOGO_BASE = "https://gcore.jsdelivr.net/gh/kenye201/TVlog/img/"
EPG_URL = "https://live.fanmingming.cn/e.xml"

# 完整频道分类（与 fofa_fetch.py 保持一致）
CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "CCTV4K", "CCTV8K",
        "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球",
        "央视文化精品", "卫生健康", "电视指南", "中学生", "发现之旅", "书法频道", "国学频道", "环球奇观"
    ],
    "卫视频道": [
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视",
        "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视",
        "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视",
        "新疆卫视", "西藏卫视", "三沙卫视", "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视",
        "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"
    ],
    "数字频道": [
        "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘精彩", "淘剧场", "淘4K", "淘娱乐", "淘BABY", "淘萌宠", "重温经典",
        "星空卫视", "CHANNEL[V]", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", "凤凰卫视电影台", "求索纪录", "求索科学",
        "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "睛彩青少", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育",
        "劲爆体育", "快乐垂钓", "茶频道", "先锋乒羽", "天元围棋", "汽摩", "梨园频道", "文物宝库", "武术世界", "哒啵赛事", "哒啵电竞", "黑莓电影", "黑莓动画",
        "乐游", "生活时尚", "都市剧场", "欢笑剧场", "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通",
        "中国交通", "中国天气", "华数4K", "华数星影", "华数动作影院", "华数喜剧影院", "华数家庭影院", "华数经典电影", "华数热播剧场", "华数碟战剧场",
        "华数军旅剧场", "华数城市剧场", "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "华数少儿动画", "华数动画", "iHOT爱喜剧", "iHOT爱科幻",
        "iHOT爱院线", "iHOT爱悬疑", "iHOT爱历史", "iHOT爱谍战", "iHOT爱旅行", "iHOT爱幼教", "iHOT爱玩具", "iHOT爱体育", "iHOT爱赛车", "iHOT爱浪漫",
        "iHOT爱奇谈", "iHOT爱科学", "iHOT爱动漫",
    ],
    "湖北": [
        "湖北公共新闻", "湖北经视频道", "湖北综合频道", "湖北垄上频道", "湖北影视频道", "湖北生活频道", "湖北教育频道", "武汉新闻综合", "武汉电视剧", "武汉科技生活",
        "武汉文体频道", "武汉教育频道", "阳新综合", "房县综合", "蔡甸综合",
    ],
    "安徽": [
       "安徽经济生活","安徽公共频道","安徽国际频道","安徽农业科教","安徽影视频道","安徽综艺体育","安庆经济生活","安庆新闻综合","蚌埠生活频道","蚌埠新闻综合","亳州农村频道",
        "亳州综合频道","池州文教生活","池州新闻综合","滁州公共频道","滁州科教频道","滁州新闻综合","枞阳电视台","繁昌新闻综合","肥西新闻综合","阜南新闻综合","阜阳都市文艺",
        "阜阳教育频道","阜阳生活频道","阜阳新闻综合","固镇新闻综合","广德生活频道","广德新闻综合","合肥新闻频道","淮北经济生活","淮北新闻综合","淮南民生频道","淮南新闻综合",
        "黄山区融媒","黄山文旅频道","黄山新闻综合","徽州新闻频道","霍邱新闻综合","霍山综合频道","界首综合频道","金寨综合频道","旌德新闻综合","郎溪新闻频道","利辛新闻综合",
        "临泉新闻频道","六安社会生活","六安综合频道","马鞍山科教生活","马鞍山新闻综合","蒙城新闻频道","南陵新闻综合","宁国新闻综合","祁门综合频道","潜山综合频道",
       "歙县综合频道","寿县新闻综合","泗县新闻频道","宿州公共频道","宿州科教频道","宿州新闻综合","濉溪新闻频道","太湖新闻综合","桐城综合频道","铜陵教育科技","铜陵新闻综合",
        "屯溪融媒频道","湾沚综合频道","涡阳新闻综合","无为新闻频道","芜湖生活频道","芜湖新闻综合","五河新闻综合","萧县新闻综合","休宁新闻综合","宣城文旅生活","宣城综合频道",
        "黟县新闻综合","义安新闻综合",
    ],
    "山西": [
        "山西黄河HD", "山西经济与科技HD", "山西影视HD", "山西社会与法治HD", "山西文体生活HD"
    ],
    "福建": [
        "福建综合", "福建新闻", "福建经济", "福建电视剧", "福建公共", "福建少儿", "泉州电视台", "福州电视台"
    ],
    "大湾区": [
        "广东珠江","广东体育","广东新闻","广东民生","广东影视","广东综艺","岭南戏曲","广东经济科教",
        "广州综合","广州新闻","广州影视","广州竞赛","广州法治","广州南国都市","佛山综合"
    ],
}

# 台标特殊映射（保持原样）
LOGO_SPECIAL_MAP = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
    # ...（其余保持原样，省略以节省篇幅）
    "华数4K": ["华数低于4K", "华数4K电影", "华数爱上4K"],
}

def get_logo_url(ch_name):
    name = ch_name.strip()
    name = re.sub(r"[ -_]HD|高清|4K|超清|超高清|8K|plus|\+|Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ", "", name, flags=re.IGNORECASE)
    name = name.replace(" ", "").replace("&", "")
    target_name = LOGO_SPECIAL_MAP.get(ch_name, name)
    if isinstance(target_name, list):
        target_name = target_name[0]  # 如果是列表，取第一个元素
    filename = str(target_name) + ".png"
    return LOGO_BASE + filename

def main():
    print(f"正在从远程下载 IPTV.txt: {INPUT_URL}")
    
    try:
        response = requests.get(INPUT_URL, timeout=30)
        response.raise_for_status()
        content = response.text
        print("远程文件下载成功，行数:", len(content.splitlines()))
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return

    # 收集所有有效行（保留更新时间、免责和符合分类的频道）
    valid_lines = []
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if not line or ",#genre#" in line:
            continue
        if "更新时间" in line or "Disclaimer" in line:
            valid_lines.append(line)
            continue
        if "," in line and "$" in line:
            ch_name = line.split(",", 1)[0].strip()
            if any(ch_name in chans for chans in CHANNEL_CATEGORIES.values()):
                valid_lines.append(line)

    if not valid_lines:
        print("❌ 没有找到任何有效频道行，跳过生成 M3U")
        return

    # 生成 M3U
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f'#EXTM3U x-tvg-url="{EPG_URL}"\n\n')
        current_group = "未分类"
        for line in valid_lines:
            # 更新时间和免责视频
            if "更新时间" in line or "Disclaimer" in line:
                parts = line.split(",", 1)
                if len(parts) == 2:
                    title, url = parts
                    out.write(f'#EXTINF:-1 group-title="更新时间",{title.strip()}\n{url.strip()}\n\n')
                continue

            # 正常频道行：CCTV1,http://...$广东电信
            ch_name, rest = line.split(",", 1)
            ch_name = ch_name.strip()
            url_with_operator = rest.strip()  # 直接保留 http://...$运营商

            # 确定分类
            for cat, chans in CHANNEL_CATEGORIES.items():
                if ch_name in chans:
                    current_group = cat
                    break

            # 标题只写纯频道名
            title = ch_name
            logo = get_logo_url(ch_name)
            out.write(f'#EXTINF:-1 tvg-name="{ch_name}" tvg-logo="{logo}" group-title="{current_group}",{title}\n')
            out.write(f"{url_with_operator}\n\n")  # 直接写带 $运营商 的完整字符串

    print(f"✅ {OUTPUT_FILE} 生成成功！")
    print(f" - 输入来源: {INPUT_URL}")
    print(f" - URL 行直接带 $运营商（如 http://...$广东电信）")
    print(f" - 标题只显示纯频道名")
    print(f" - 每个源独立一条目，严格兼容所有播放器")

if __name__ == "__main__":
    main()
