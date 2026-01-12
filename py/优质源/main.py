import os
import re
import requests
import subprocess
from urllib.parse import urlparse
from ipaddress import ip_address, IPv4Address, IPv6Address
import concurrent.futures
import time
import threading
from collections import OrderedDict
import ssl
import socket

# 配置参数
CONFIG_DIR = 'py/优质源/config'
SUBSCRIBE_FILE = os.path.join(CONFIG_DIR, 'subscribe.txt')
DEMO_FILE = os.path.join(CONFIG_DIR, 'demo.txt')
LOCAL_FILE = os.path.join(CONFIG_DIR, 'local.txt')
BLACKLIST_FILE = os.path.join(CONFIG_DIR, 'blacklist.txt')
RUN_COUNT_FILE = os.path.join(CONFIG_DIR, 'run_count.txt')

OUTPUT_DIR = 'py/优质源/output'
IPV4_DIR = os.path.join(OUTPUT_DIR, 'ipv4')
IPV6_DIR = os.path.join(OUTPUT_DIR, 'ipv6')
SPEED_LOG = os.path.join(OUTPUT_DIR, 'sort.log')

SPEED_TEST_DURATION = 5
MAX_WORKERS = 10
HTTPS_VERIFY = False
SPEED_THRESHOLD = 120  
RESET_COUNT = 12       

# 全局变量
failed_domains = set()
log_lock = threading.Lock()
domain_lock = threading.Lock()
counter_lock = threading.Lock()

os.makedirs(IPV4_DIR, exist_ok=True)
os.makedirs(IPV6_DIR, exist_ok=True)

# --------------------------
# 工具函数
# --------------------------
def manage_run_count():
    try:
        if os.path.exists(RUN_COUNT_FILE):
            with open(RUN_COUNT_FILE, 'r') as f:
                current_count = int(f.read().strip())
        else:
            current_count = 0
        current_count += 1
        if current_count >= RESET_COUNT:
            if os.path.exists(BLACKLIST_FILE):
                with open(BLACKLIST_FILE, 'w') as f:
                    f.write('')
            current_count = 0
        with open(RUN_COUNT_FILE, 'w') as f:
            f.write(str(current_count))
        return current_count
    except Exception as e:
        return 1

def write_log(message):
    with log_lock:
        with open(SPEED_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def get_domain(url):
    try:
        netloc = urlparse(url).netloc
        return netloc.split(':')[0] if ':' in netloc else netloc
    except:
        return None

def update_blacklist(domain):
    if domain:
        with domain_lock:
            failed_domains.add(domain)

def get_ip_type(url):
    try:
        host = urlparse(url).hostname
        if not host: return 'ipv4'
        ip = ip_address(host)
        return 'ipv6' if isinstance(ip, IPv6Address) else 'ipv4'
    except:
        return 'ipv4'

def get_protocol(url):
    try:
        return urlparse(url).scheme.lower()
    except:
        return 'unknown'

def test_https_certificate(domain, port=443):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                return True, "Success"
    except:
        return False, "Failed"

# --------------------------
# 核心逻辑
# --------------------------
def parse_demo_file():
    alias_map, group_map, group_order = {}, {}, []
    channel_order = OrderedDict()
    current_group = None
    try:
        with open(DEMO_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                if line.endswith(',#genre#'):
                    current_group = line.split(',', 1)[0]
                    group_order.append(current_group)
                    channel_order[current_group] = []
                elif current_group:
                    parts = [p.strip() for p in line.split('|')]
                    std_name = parts[0]
                    channel_order[current_group].append(std_name)
                    for alias in parts: alias_map[alias] = std_name
                    group_map[std_name] = current_group
        return alias_map, group_map, group_order, channel_order
    except:
        return {}, {}, [], OrderedDict()

def fetch_sources():
    sources = []
    try:
        with open(SUBSCRIBE_FILE, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        for url in urls:
            try:
                response = requests.get(url, timeout=15, verify=HTTPS_VERIFY)
                content = response.text
                if '#EXTM3U' in content:
                    sources.extend(parse_m3u(content))
                else:
                    sources.extend(parse_txt(content))
            except: pass
    except: pass
    return sources

def parse_m3u(content):
    channels, current = [], {}
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('#EXTINF'):
            match = re.search(r'tvg-name="([^"]*)"', line)
            current = {'name': match.group(1) if match else '未知', 'urls': []}
        elif line and not line.startswith('#'):
            if current:
                current['urls'].append(line)
                channels.append(current)
                current = {}
    return [{'name': c['name'], 'url': u} for c in channels for u in c['urls']]

def parse_txt(content):
    channels = []
    for line in content.split('\n'):
        line = line.strip()
        if ',' in line:
            name, urls = line.split(',', 1)
            for url in urls.split('#'):
                clean_url = url.split('$')[0].strip()
                if clean_url: channels.append({'name': name.strip(), 'url': clean_url})
    return channels

def parse_local():
    sources = []
    try:
        with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ',' in line:
                    name, urls = line.split(',', 1)
                    for url in urls.split('#'):
                        parts = url.split('$', 1)
                        sources.append({'name': name.strip(), 'url': parts[0].strip(), 'whitelist': len(parts)>1})
    except: pass
    return sources

def read_blacklist():
    try:
        with open(BLACKLIST_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except: return []

def filter_sources(sources, blacklist):
    filtered, bl_lower = [], [kw.lower() for kw in blacklist]
    for s in sources:
        if not urlparse(s['url']).scheme: continue
        if s.get('whitelist', False): 
            filtered.append(s)
            continue
        if any(kw in s['url'].lower() for kw in bl_lower): continue
        filtered.append(s)
    return filtered

def test_speed(url):
    try:
        protocol = get_protocol(url)
        if protocol in ['rtmp', 'rtmps']:
            result = subprocess.run(['ffmpeg', '-i', url, '-t', '1', '-v', 'error', '-f', 'null', '-'], timeout=10)
            return 100 if result.returncode == 0 else 0
        
        with requests.Session() as session:
            response = session.get(url, stream=True, timeout=(3, 5), verify=False)
            total_bytes, data_start = 0, time.time()
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk: total_bytes += len(chunk)
                if (time.time() - data_start) >= SPEED_TEST_DURATION: break
            duration = max(time.time() - data_start, 0.001)
            return (total_bytes / 1024) / duration
    except:
        update_blacklist(get_domain(url))
        return 0

def process_sources(sources):
    processed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(lambda s: (s['name'], s['url'], test_speed(s['url']), get_ip_type(s['url']), get_protocol(s['url'])), s): s for s in sources}
        for future in concurrent.futures.as_completed(futures):
            try:
                name, url, speed, ip_type, protocol = future.result()
                if speed > SPEED_THRESHOLD:
                    processed.append((name, url, speed, ip_type, protocol))
            except: pass
    
    if failed_domains:
        with open(BLACKLIST_FILE, 'a') as f:
            for d in failed_domains: f.write(f"{d}\n")
    return processed

def organize_channels(processed, alias_map, group_map):
    organized = {'ipv4': OrderedDict(), 'ipv6': OrderedDict()}
    for name, url, speed, ip_type, protocol in processed:
        std_name = alias_map.get(name, name)
        group = group_map.get(std_name, '其他')
        if group not in organized[ip_type]: organized[ip_type][group] = OrderedDict()
        if std_name not in organized[ip_type][group]: organized[ip_type][group][std_name] = []
        organized[ip_type][group][std_name].append((url, speed, protocol))
    return organized

# --------------------------
# 修改后的生成结果文件函数
# --------------------------
def finalize_output(organized, group_order, channel_order):
    print("\n📂 正在生成纯净版结果文件...")
    
    for ip_type in ['ipv4', 'ipv6']:
        txt_lines = []
        m3u_lines = ['#EXTM3U x-tvg-url="https://gh.catmak.name/https://raw.githubusercontent.com/Guovin/iptv-api/refs/heads/master/output/epg/epg.gz"']
        total_sources = 0
        speed_stats = []

        # 1. 按模板顺序处理分组
        for group in group_order:
            if group not in organized[ip_type]: continue
            txt_lines.append(f"{group},#genre#")

            for channel in channel_order[group]:
                if channel not in organized[ip_type][group]: continue
                
                # 获取并排序源
                urls = sorted(organized[ip_type][group][channel], key=lambda x: x[1], reverse=True)
                
                # 生成 TXT 与 M3U
                for url, speed, protocol in urls:
                    txt_lines.append(f"{channel},{url}")
                    # M3U 仅保留频道名，去掉图标变量、速度和竖线
                    m3u_lines.append(f'#EXTINF:-1 tvg-name="{channel}" tvg-logo="https://gh.catmak.name/https://raw.githubusercontent.com/fanmingming/live/main/tv/{channel}.png" group-title="{group}",{channel}')
                    m3u_lines.append(url)
                    total_sources += 1
                    speed_stats.append(speed)

            # 2. 处理该分组下不在模板里的额外频道
            extra = sorted([c for c in organized[ip_type][group] if c not in channel_order[group]], key=lambda x: x.lower())
            for channel in extra:
                urls = sorted(organized[ip_type][group][channel], key=lambda x: x[1], reverse=True)
                for url, speed, protocol in urls:
                    txt_lines.append(f"{channel},{url}")
                    m3u_lines.append(f'#EXTINF:-1 tvg-name="{channel}" tvg-logo="https://gh.catmak.name/https://raw.githubusercontent.com/fanmingming/live/main/tv/{channel}.png" group-title="{group}",{channel}')
                    m3u_lines.append(url)
                    total_sources += 1
                    speed_stats.append(speed)

        # 3. 处理“其他”分组
        if '其他' in organized[ip_type]:
            txt_lines.append("其他,#genre#")
            for channel in sorted(organized[ip_type]['其他'].keys(), key=lambda x: x.lower()):
                urls = sorted(organized[ip_type]['其他'][channel], key=lambda x: x[1], reverse=True)
                for url, speed, protocol in urls:
                    txt_lines.append(f"{channel},{url}")
                    m3u_lines.append(f'#EXTINF:-1 tvg-name="{channel}" tvg-logo="https://gh.catmak.name/https://raw.githubusercontent.com/fanmingming/live/main/tv/{channel}.png" group-title="其他",{channel}')
                    m3u_lines.append(url)
                    total_sources += 1
                    speed_stats.append(speed)

        # 写入文件
        dir_path = IPV4_DIR if ip_type == 'ipv4' else IPV6_DIR
        with open(os.path.join(dir_path, 'result.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(txt_lines))
        with open(os.path.join(dir_path, 'result.m3u'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_lines))

        print(f"✅ {ip_type.upper()} 生成完毕，共 {total_sources} 个源")

if __name__ == '__main__':
    run_count = manage_run_count()
    alias_map, group_map, group_order, channel_order = parse_demo_file()
    sources = fetch_sources() + parse_local()
    blacklist = read_blacklist()
    filtered = filter_sources(sources, blacklist)
    processed = process_sources(filtered)
    organized = organize_channels(processed, alias_map, group_map)
    finalize_output(organized, group_order, channel_order)
    print(f"🎉 处理完成！当前运行次数: {run_count}")
