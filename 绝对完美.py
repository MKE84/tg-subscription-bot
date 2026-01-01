
import os
import logging
import concurrent.futures
import socket
import base64
import requests
import yaml
import time
import datetime  
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    Defaults,
    filters
)
import re
from urllib.parse import unquote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
import warnings



# ---------------- 导入所有依赖模块 --------------------
import warnings
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import base64
from urllib.parse import unquote
import yaml
import logging

BOT_TOKEN = "8276665475:AAEH7ZF8GjijB1FLDuZOyBsX-2vtaV05Vig"  # 去@BotFather获取
AUTHORIZED_USER_IDS = {None}  # 去@userinfobot获取自己的ID
NODES_PER_PAGE = 100  # 每页显示节点数量
# ---------------- 初始化日志 --------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# ---------------- 用户相关全局状态 --------------------
nodes_cache = dict()
nodes_fold_status = dict()
user_filter_params = dict()

# ---------------- 定义国旗映射表 --------------------
COUNTRY_FLAGS = {
    # 按国家码首字母A-Z排序
    "AU": "🇦🇺",   # 澳大利亚
    "BD": "🇧🇩",   # 孟加拉国
    "BH": "🇧🇭",   # 巴林
    "BG": "🇧🇬",   # 保加利亚
    "BW": "🇧🇼",   # 博茨瓦纳
    "BY": "🇧🇾",   # 白俄罗斯
    "CA": "🇨🇦",   # 加拿大
    "CN": "🇨🇳",   # 中国
    "CO": "🇨🇴",   # 哥伦比亚
    "CU": "🇨🇺",   # 古巴
    "CY": "🇨🇾",   # 塞浦路斯
    "DE": "🇩🇪",   # 德国
    "DZ": "🇩🇿",   # 阿尔及利亚
    "EC": "🇪🇨",   # 厄瓜多尔
    "EE": "🇪🇪",   # 爱沙尼亚
    "EG": "🇪🇬",   # 埃及（原列表虽没提但补充常见国旗，可删除）
    "FJ": "🇫🇯",   # 斐济
    "FR": "🇫🇷",   # 法国
    "GB": "🇬🇧",   # 英国
    "GH": "🇬🇭",   # 加纳
    "GR": "🇬🇷",   # 希腊
    "HK": "🇭🇰",   # 香港
    "HR": "🇭🇷",   # 克罗地亚
    "IS": "🇮🇸",   # 冰岛
    "JM": "🇯🇲",   # 牙买加
    "JO": "🇯🇴",   # 约旦
    "JP": "🇯🇵",   # 日本
    "KE": "🇰🇪",   # 肯尼亚
    "KH": "🇰🇭",   # 柬埔寨
    "KR": "🇰🇷",   # 韩国
    "KZ": "🇰🇿",   # 哈萨克斯坦
    "LB": "🇱🇧",   # 黎巴嫩
    "LA": "🇱🇦",   # 老挝
    "LK": "🇱🇰",   # 斯里兰卡
    "LT": "🇱🇹",   # 立陶宛
    "LV": "🇱🇻",   # 拉脱维亚
    "MA": "🇲🇦",   # 摩洛哥
    "MG": "🇲🇬",   # 马达加斯加
    "MM": "🇲🇲",   # 缅甸
    "MO": "🇲🇴",   # 澳门
    "MT": "🇲🇹",   # 马耳他
    "MN": "🇲🇳",   # 蒙古
    "MY": "🇲🇾",   # 马来西亚
    "NA": "🇳🇦",   # 纳米比亚
    "NL": "🇳🇱",   # 荷兰
    "NZ": "🇳🇿",   # 新西兰
    "OM": "🇴🇲",   # 阿曼
    "PE": "🇵🇪",   # 秘鲁
    "PG": "🇵🇬",   # 巴布亚新几内亚
    "PY": "🇵🇾",   # 巴拉圭
    "RO": "🇷🇴",   # 罗马尼亚
    "RS": "🇷🇸",   # 塞尔维亚
    "SB": "🇸🇧",   # 所罗门群岛
    "SG": "🇸🇬",   # 新加坡
    "SI": "🇸🇮",   # 斯洛文尼亚
    "SK": "🇸🇰",   # 斯洛伐克
    "SY": "🇸🇾",   # 叙利亚
    "TH": "🇹🇭",   # 泰国
    "TN": "🇹🇳",   # 突尼斯
    "TZ": "🇹🇿",   # 坦桑尼亚
    "TW": "🇹🇼",   # 台湾
    "US": "🇺🇸",   # 美国
    "UY": "🇺🇾",   # 乌拉圭
    "UZ": "🇺🇿",   # 乌兹别克斯坦
    "VE": "🇻🇪",   # 委内瑞拉
    "ZA": "🇿🇦",   # 南非
    "ZM": "🇿🇲",   # 赞比亚
    "ZW": "🇿🇼"    # 津巴布韦
}
# ---------------- 定义缺失的extract_country_from_name函数 --------------------
def extract_country_from_name(name: str) -> str:
    """国家码提取函数：中文关键词前置，全条目带中文标记"""
    name_lower = name.lower()
    country_maps = {
        # 核心常用地区（汉字优先）
        "台湾": "TW", "tw": "TW", "taiwan": "TW",  # 台湾
        "香港": "HK", "hk": "HK", "hongkong": "HK",  # 香港
        "澳门": "MO", "mo": "MO", "macau": "MO",  # 澳门
        "新加坡": "SG", "sg": "SG", "singapore": "SG",  # 新加坡
        "日本": "JP", "jp": "JP", "japan": "JP",  # 日本
        "韩国": "KR", "kr": "KR", "korea": "KR",  # 韩国
        "马来西亚": "MY", "my": "MY", "malaysia": "MY",  # 马来西亚
        "泰国": "TH", "th": "TH", "thailand": "TH",  # 泰国
        "越南": "VN", "vn": "VN", "vietnam": "VN",  # 越南
        "印度": "IN", "in": "IN", "india": "IN",  # 印度
        "俄罗斯": "RU", "ru": "RU", "russia": "RU",  # 俄罗斯
        "美国": "US", "us": "US", "usa": "US",  # 美国
        "加拿大": "CA", "ca": "CA", "canada": "CA",  # 加拿大
        "英国": "GB", "gb": "GB", "uk": "GB",  # 英国
        "德国": "DE", "de": "DE", "germany": "DE",  # 德国
        "法国": "FR", "fr": "FR", "france": "FR",  # 法国
        "澳大利亚": "AU", "au": "AU", "australia": "AU",  # 澳大利亚
        "新西兰": "NZ", "nz": "NZ", "zealand": "NZ",  # 新西兰
        "菲律宾": "PH", "ph": "PH", "philippines": "PH",  # 菲律宾
        "印尼": "ID", "id": "ID", "indonesia": "ID",  # 印尼
        "阿联酋": "AE", "ae": "AE", "uae": "AE",  # 阿联酋
        "沙特阿拉伯": "SA", "sa": "SA", "saudi": "SA",  # 沙特阿拉伯
        "土耳其": "TR", "tr": "TR", "turkey": "TR",  # 土耳其
        "伊朗": "IR", "ir": "IR", "iran": "IR",  # 伊朗
        "以色列": "IL", "il": "IL", "israel": "IL",  # 以色列
        "哈萨克斯坦": "KZ", "kz": "KZ", "kazakhstan": "KZ",  # 哈萨克斯坦
        "巴基斯坦": "PK", "pk": "PK", "pakistan": "PK",  # 巴基斯坦
        "孟加拉国": "BD", "bd": "BD", "bangladesh": "BD",  # 孟加拉国
        "斯里兰卡": "LK", "lk": "LK", "lanka": "LK",  # 斯里兰卡
        "缅甸": "MM", "mm": "MM", "myanmar": "MM",  # 缅甸
        "柬埔寨": "KH", "kh": "KH", "cambodia": "KH",  # 柬埔寨
        "老挝": "LA", "la": "LA", "laos": "LA",  # 老挝
        "蒙古": "MN", "mn": "MN", "mongolia": "MN",  # 蒙古
        "卡塔尔": "QA", "qa": "QA", "qatar": "QA",  # 卡塔尔
        "科威特": "KW", "kw": "KW", "kuwait": "KW",  # 科威特
        "阿曼": "OM", "om": "OM", "oman": "OM",  # 阿曼
        "巴林": "BH", "bh": "BH", "bahrain": "BH",  # 巴林
        "荷兰": "NL", "nl": "NL", "netherlands": "NL",  # 荷兰
        "意大利": "IT", "it": "IT", "italy": "IT",  # 意大利
        "西班牙": "ES", "es": "ES", "spain": "ES",  # 西班牙
        "瑞士": "CH", "ch": "CH", "switzerland": "CH",  # 瑞士
        "瑞典": "SE", "se": "SE", "sweden": "SE",  # 瑞典
        "挪威": "NO", "no": "NO", "norway": "NO",  # 挪威
        "丹麦": "DK", "dk": "DK", "denmark": "DK",  # 丹麦
        "芬兰": "FI", "fi": "FI", "finland": "FI",  # 芬兰
        "比利时": "BE", "be": "BE", "belgium": "BE",  # 比利时
        "奥地利": "AT", "at": "AT", "austria": "AT",  # 奥地利
        "葡萄牙": "PT", "pt": "PT", "portugal": "PT",  # 葡萄牙
        "希腊": "GR", "gr": "GR", "greece": "GR",  # 希腊
        "波兰": "PL", "pl": "PL", "poland": "PL",  # 波兰
        "捷克": "CZ", "cz": "CZ", "czech": "CZ",  # 捷克
        "匈牙利": "HU", "hu": "HU", "hungary": "HU",  # 匈牙利
        "罗马尼亚": "RO", "ro": "RO", "romania": "RO",  # 罗马尼亚
        "保加利亚": "BG", "bg": "BG", "bulgaria": "BG",  # 保加利亚
        "乌克兰": "UA", "ua": "UA", "ukraine": "UA",  # 乌克兰
        "白俄罗斯": "BY", "by": "BY", "belarus": "BY",  # 白俄罗斯
        "爱沙尼亚": "EE", "ee": "EE", "estonia": "EE",  # 爱沙尼亚
        "拉脱维亚": "LV", "lv": "LV", "latvia": "LV",  # 拉脱维亚
        "立陶宛": "LT", "lt": "LT", "lithuania": "LT",  # 立陶宛
        "克罗地亚": "HR", "hr": "HR", "croatia": "HR",  # 克罗地亚
        "冰岛": "IS", "is": "IS", "iceland": "IS",  # 冰岛
        "墨西哥": "MX", "mx": "MX", "mexico": "MX",  # 墨西哥
        "巴西": "BR", "br": "BR", "brazil": "BR",  # 巴西
        "阿根廷": "AR", "ar": "AR", "argentina": "AR",  # 阿根廷
        "智利": "CL", "cl": "CL", "chile": "CL",  # 智利
        "哥伦比亚": "CO", "co": "CO", "colombia": "CO",  # 哥伦比亚
        "南非": "ZA", "za": "ZA", "africa": "ZA",  # 南非
        "埃及": "EG", "eg": "EG", "egypt": "EG",  # 埃及
        "尼日利亚": "NG", "ng": "NG", "nigeria": "NG",  # 尼日利亚
        "肯尼亚": "KE", "ke": "KE", "kenya": "KE",  # 肯尼亚
        "坦桑尼亚": "TZ", "tz": "TZ", "tanzania": "TZ",  # 坦桑尼亚
        "加纳": "GH", "gh": "GH", "ghana": "GH"  # 加纳
    }
    for keyword, code in country_maps.items():
        if keyword in name_lower:
            return code
    return "UNKNOWN"

# ---------------- 定义辅助函数 --------------------
def bytes_to_human(size: float) -> str:
    """字节转人类可读格式（比如1024→1KB）"""
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024:
            return f"{round(size, 2)} {unit}"
        size /= 1024
    return f"{round(size, 2)} PB"

def auto_detect_traffic_display(used: str, total: str) -> tuple:
    """流量显示自动处理（根据你的需求简单实现）"""
    return used if used != "隐藏" else "0", total if total != "隐藏" else "0"

def auto_detect_time_display(expired: str) -> str:
    """过期时间自动处理（转成人类可读格式）"""
    if expired == "隐藏" or not expired.isdigit():
        return "未知"
    try:
        from datetime import datetime
        return datetime.fromtimestamp(int(expired)).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "未知"

# ---------------- 订阅解析主函数（完全沿用之前的最终版逻辑） --------------------
def parse_clash_subscription(sub_url: str) -> dict:
    """解析Clash订阅（支持base64编码、节点链接、更多协议，返回标准格式数据）"""
    try:
        warnings.filterwarnings("ignore", category=InsecureRequestWarning)
        session = requests.Session()
        session.mount("http://", HTTPAdapter(max_retries=Retry(3, backoff_factor=1, status_forcelist=[429,500,502,503,504])))
        session.mount("https://", HTTPAdapter(max_retries=Retry(3, backoff_factor=1, status_forcelist=[429,500,502,503,504])))
        
        # ========== 节点链接解析 ==========
        # 位置1：在SUPPORTED_PROTOCOLS集合中添加"socks5"
        SUPPORTED_PROTOCOLS = {"ss", "vmess", "trojan", "vless", "ssr", "trojan-go", "wireguard", "shadowsocksr", "socks5"}
        single_node_match = re.match(rf'^({"|".join(SUPPORTED_PROTOCOLS)})://[A-Za-z0-9+/=]+$', sub_url.strip(), re.IGNORECASE)
        if single_node_match:
            logger.info("检测到节点链接，开始解析...")
            proto = single_node_match.group(1).lower()
            encoded_part = sub_url.split("://")[1]
            padded = encoded_part + '=' * ((4 - len(encoded_part) % 4) % 4)
            
            try:
                decoded = base64.urlsafe_b64decode(padded).decode('utf-8', errors='replace')
                # 位置2：在这里添加socks5单独适配的代码块
                # 针对socks5单独适配名称提取规则
                if proto == "socks5":
                    name_match = re.search(r'name=([^&,]+)', decoded) or re.search(r'ps=([^&,]+)', decoded)
                    name = name_match.group(1) if name_match else f"{proto}节点"
                    # 提取socks5节点特有的服务器和端口信息
                    server_match = re.search(r'server=([^&,]+)', decoded)
                    port_match = re.search(r'port=(\d+)', decoded)
                    server = server_match.group(1) if server_match else "未知（节点提取）"
                    port = port_match.group(1) if port_match else "未知（节点提取）"
                else:
                    name_match = re.search(r'name=([^&,]+)', decoded) or re.search(r'"ps":"([^"]+)"', decoded) or re.search(r'ps=([^&,]+)', decoded)
                    name = name_match.group(1) if name_match else f"{proto}节点"
                    server = "未知（节点提取）"
                    port = "未知（节点提取）"
                
                country_code = extract_country_from_name(name)
                flag = COUNTRY_FLAGS.get(country_code, "🌐")
                
                # 防御性判断：确保COUNTRY_FLAGS是字典
                if not isinstance(COUNTRY_FLAGS, dict):
                    logger.warning("COUNTRY_FLAGS不是字典，使用默认地区")
                    country_name = "未知地区"
                else:
                    country_name = next((k for k, v in COUNTRY_FLAGS.items() if v == flag), "未知地区")
                
                return {
                    "subscription_url": "节点解析",
                    "traffic_used": "隐藏",
                    "traffic_total": "隐藏",
                    "expired": "隐藏",
                    "protocol": proto,
                    "total_nodes": 1,
                    "nodes": [
                        {
                            "name": name,
                            "protocol": proto,
                            "country": country_code,
                            "country_name": country_name,
                            "flag": flag,
                            "server": server,  # 这里会自动使用socks5提取的server值
                            "port": port       # 这里会自动使用socks5提取的port值
                        }
                    ],
                    "all_countries": [country_name]
                }
            except Exception as e:
                logger.warning(f"节点解析失败，fallback到原订阅逻辑：{str(e)}")


        # ========== 原有订阅请求逻辑 ==========
        response = session.get(
            sub_url,
            timeout=15,
            headers={"User-Agent": "Clash/1.17.0 (+https://clash.dev)"},
            allow_redirects=True,
            verify=False
        )
        response.raise_for_status()
        raw_content = response.text.strip()
        if not raw_content:
            return {"error": "❌ 订阅返回空内容"}
        
        # ========== 解码逻辑 ==========
        decoded_text = raw_content  # 确保这行存在！
        if raw_content.startswith("clash://subscribe?url="):
            raw_content = re.sub(r'^clash://subscribe\?url=|&.*$', '', raw_content)
            raw_content = unquote(raw_content)
        # 第一步：原有的3次循环解码
        for _ in range(1):
            try:
                padded = raw_content + '=' * ((4 - len(raw_content) % 4) % 4)
                decoded = base64.urlsafe_b64decode(padded).decode('utf-8', errors='replace')
                if re.match(r'^[A-Za-z0-9+/=]+$', decoded.strip()):
                    raw_content = decoded
                else:
                    decoded_text = decoded
                    break
            except:
                break
        
        # 第二步：字符串处理——只对非YAML格式的纯文本节点列表生效
        is_yaml = False
        if isinstance(decoded_text, str):
            yaml_keywords = ["proxies:", "proxy-groups:", "rules:", "port:", "socks-port:"]
            for keyword in yaml_keywords:
                if keyword in decoded_text[:500]:
                    is_yaml = True
                    break
        
        if isinstance(decoded_text, str) and not is_yaml:
            decoded_text = decoded_text.strip().splitlines()
            if len(decoded_text) == 1:
                decoded_text = decoded_text[0].split()
            if not decoded_text:
                decoded_text = "proxies: []"
            else:
                valid_links = [line for line in decoded_text if any(p in line.lower() for p in SUPPORTED_PROTOCOLS)]
                if valid_links:
                    proxy_lines = []
                    for idx, link in enumerate(valid_links, 1):
                        proxy_lines.append(f"- name: 节点{idx}")
                        proxy_lines.append(f"  type: custom")
                        proxy_lines.append(f"  url: {link}")
                    decoded_text = f"proxies:\n  {'\n  '.join(proxy_lines)}"
                else:
                    decoded_text = "proxies: []"

        # ========== 流量&过期时间提取 ==========
        traffic_used = None
        traffic_total = None
        expired = None
        
        info_headers = [
            response.headers.get("subscription-userinfo"),
            response.headers.get("X-Subscription-Userinfo"),
            response.headers.get("UserInfo")
        ]
        for header in info_headers:
            if header:
                upload = re.search(r'upload=(\d+)', header)
                download = re.search(r'download=(\d+)', header)
                total = re.search(r'total=(\d+)', header)
                expire_ts = re.search(r'expire=(\d+)', header)
                if upload and download and total:
                    total_used_bytes = float(upload.group(1)) + float(download.group(1))
                    traffic_used = bytes_to_human(total_used_bytes)
                    traffic_total = bytes_to_human(float(total.group(1)))
                if expire_ts:
                    expired = str(expire_ts.group(1))
                if traffic_used and expired:
                    break
        
        if not traffic_used and isinstance(decoded_text, str):
            traffic_used_match = re.search(r'traffic_used:\s*([^\n]+)', decoded_text)
            traffic_total_match = re.search(r'traffic_total:\s*([^\n]+)', decoded_text)
            if traffic_used_match and traffic_total_match:
                traffic_used = traffic_used_match.group(1).strip()
                traffic_total = traffic_total_match.group(1).strip()
        
        if not expired and isinstance(decoded_text, str):
            expired_match = re.search(r'expired:\s*([^\n]+)', decoded_text)
            if expired_match:
                expired = expired_match.group(1).strip()
        # ========== YAML解析节点 ==========
        try:
            config = yaml.safe_load(decoded_text)
            if not isinstance(config, dict):
                config = {"proxies": []}
        except yaml.YAMLError as e:
            logger.warning(f"YAML解析失败：{str(e)}，使用空节点列表")
            config = {"proxies": []}






        # ========== 节点处理（国旗优先识别） ==========
        # 确保proxies是列表
        proxies = config.get("proxies", []) if isinstance(config, dict) else []
        valid_nodes = []
    
        country_maps = {}  # 默认为字典

        for item in proxies:
            # 确保每个节点是字典
            if not isinstance(item, dict):
                logger.warning(f"节点不是字典，类型为：{type(item)}，跳过")
                continue
            
            name = item.get("name", f"节点{len(valid_nodes)+1}")
            proto = item.get("type", "未知")
            proto = proto.lower() if isinstance(proto, str) else "未知"
            if proto not in SUPPORTED_PROTOCOLS:
                proto = "未知"
 
            # 国旗优先识别逻辑
            flag = "❓"
            country_code = "UNKNOWN"
            country_name = "未知地区"
            
            # 确保COUNTRY_FLAGS是字典
            if isinstance(COUNTRY_FLAGS, dict):
                for emoji, info in COUNTRY_FLAGS.items():
                    if emoji in name:
                        flag = emoji
                        # 确保info是字典
                        country_code = info.get("code", "UNKNOWN") if isinstance(info, dict) else "UNKNOWN"
                        country_name = info.get("name", "未知地区") if isinstance(info, dict) else "未知地区"
                        break
            
            if country_code == "UNKNOWN" and isinstance(config, dict):
                country_code = item.get("country", extract_country_from_name(name))
                # 确保COUNTRY_FLAGS是字典
                if isinstance(COUNTRY_FLAGS, dict):
                    flag = COUNTRY_FLAGS.get(country_code, "❓")
                    country_name = next((k for k, v in COUNTRY_FLAGS.items() if v == flag), "未知地区")
            
            if country_code == "UNKNOWN" and isinstance(country_maps, dict):
                name_lower = name.lower() if isinstance(name, str) else ""
                for map_name, map_code in country_maps.items():
                    if map_name in name_lower:
                        country_code = map_code
                        # 确保COUNTRY_FLAGS是字典
                        if isinstance(COUNTRY_FLAGS, dict):
                            flag = COUNTRY_FLAGS.get(country_code, "❓")
                            country_name = next((k for k, v in COUNTRY_FLAGS.items() if v == flag), "未知地区")
                        break
            
            server = item.get("server", "未知")
            port = item.get("port", "未知")

            valid_nodes.append({
                "name": name,
                "protocol": proto,
                "country": country_code,
                "country_name": country_name,
                "flag": flag,
                "server": server,
                "port": port
            })

        # 最终参数处理——所有操作前都加类型判断
        final_traffic_used = traffic_used or ""
        final_traffic_total = traffic_total or ""
        final_expired = expired or ""
        
        if isinstance(config, dict):
            final_traffic_used = final_traffic_used or config.get("traffic_used", "隐藏")
            final_traffic_total = final_traffic_total or config.get("traffic_total", "隐藏")
            final_expired = final_expired or config.get("expired", "隐藏")

        auto_used, auto_total = auto_detect_traffic_display(final_traffic_used, final_traffic_total)
        auto_expired = auto_detect_time_display(final_expired)

        # 返回结果
        return {
            "subscription_url": sub_url,
            "traffic_used": auto_used,
            "traffic_total": auto_total,
            "expired": auto_expired,
            "protocol": ",".join(list(set(n["protocol"] for n in valid_nodes))) if valid_nodes else "未知",
            "total_nodes": len(valid_nodes),
            "nodes": valid_nodes,
            "all_countries": list(set(n["country_name"] for n in valid_nodes)) if valid_nodes else ["未知地区"]
        }
    except requests.exceptions.Timeout:
        return {"error": "❌ 订阅请求超时"}
    except requests.exceptions.RequestException as e:
        return {"error": f"❌ 订阅请求失败: {str(e)}"}
    except Exception as e:
        # 打印详细错误日志，包括出错变量类型
        import traceback
        logger.error(f"订阅解析失败：{str(e)}，详细栈信息：\n{traceback.format_exc()}")
        return {"error": f"❌ 订阅解析失败：{str(e)}"}









# ---------------- 接收订阅链接的处理函数 --------------------
async def handle_subscription_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户发送的订阅链接（清除延迟测试残留）"""
    user_id = update.effective_user.id
    sub_url = update.message.text.strip()

    await update.message.reply_text("🔍 正在解析订阅链接...请稍等～")

    try:
        parse_result = parse_clash_subscription(sub_url)
        if parse_result.get("error"):
            await update.message.reply_text(f"解析失败：{parse_result['error']}")
            return

        nodes_cache[user_id] = parse_result
        user_filter_params.setdefault(user_id, {"country": None})
        nodes_fold_status.setdefault(user_id, True)

        await send_nodes_page(update, context, user_id, page=0)
    except Exception as e:
        logger.error(f"处理订阅失败：{str(e)}")
        await update.message.reply_text(f"处理失败：{str(e)}")


async def send_nodes_page(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, page: int, show_nodes=None, message_to_edit=None):
    try:
        data = nodes_cache[user_id]
        
        filter_country = user_filter_params.get(user_id, {}).get("country")
        filtered_nodes = data["nodes"]
        if filter_country and filter_country != "未知地区": 
            filtered_nodes = [n for n in filtered_nodes if n["country_name"] == filter_country]
        print(f"filtered_nodes长度: {len(filtered_nodes)}，内容预览: {[n.get('name') for n in filtered_nodes[:3]]}")
        
        nodes_per_page = NODES_PER_PAGE
        total_nodes = len(filtered_nodes)
        total_pages = (total_nodes - 1) // nodes_per_page + 1 if total_nodes > 0 else 1
        page = max(0, min(page, total_pages - 1))

        node_flags = []
        for n in filtered_nodes:
            flag = n.get("flag")
            if flag and flag not in node_flags:
                node_flags.append(flag)
        node_range = ",".join(node_flags) if node_flags else "🌐"
        # ---------------- 新增：生成流量使用进度条 ----------------
        traffic_used = data.get('traffic_used', '隐藏')
        traffic_total = data.get('traffic_total', '隐藏')
        progress_bar = "——"  # 默认占位符
        progress_percent = "未知"

        try:
            # 提取数值（处理类似"1.2GB / 10GB"或直接数值的情况）
            def extract_bytes(traffic_str):
                """把流量字符串转成字节数"""
                if not isinstance(traffic_str, str) or "隐藏" in traffic_str:
                    return None
                # 匹配数值+单位（比如1.5GB、200MB）
                match = re.search(r'(\d+\.?\d*)\s*([A-Za-z]+)', traffic_str.strip())
                if not match:
                    return None
                num = float(match.group(1))
                unit = match.group(2).upper()
                # 单位转字节
                unit_map = {
                    "B": 1,
                    "KB": 1024,
                    "MB": 1024**2,
                    "GB": 1024**3,
                    "TB": 1024**4
                }
                return num * unit_map.get(unit, 1)

            used_bytes = extract_bytes(traffic_used)
            total_bytes = extract_bytes(traffic_total)

            if used_bytes and total_bytes and total_bytes > 0:
                progress_percent = round((used_bytes / total_bytes) * 100, 1)
                # 生成进度条（共12个格子，方便排版）
                bar_length = 12
                filled = int(round(bar_length * (progress_percent / 100)))
                empty = bar_length - filled
                progress_bar = f"[{'⬢'*filled}{'⬡'*empty}]"
        except Exception as e:
            logging.warning(f"生成进度条出错：{str(e)}")
            # 出错也不影响，保持默认占位符


        # ---------------- 修改后：加入进度条的头部文本 ----------------
        header_text = (
            f"╭─━━━━━💠━订阅 信息━💠━━━━━╮\n"
            f"┃ 订阅链接: <code>{data['subscription_url'][:20]}</code>\n"
            f"┃ 流量详情: {traffic_used[:20]} / {traffic_total[:15]}\n"
            f"┃ 使用进度: {progress_bar} {progress_percent}%\n"  
            f"┃ 剩余时间: {data.get('expired','隐藏')[:30]}\n"
            f"┃ 协议类型: {data.get('protocol','未知')[:100]}\n"
            f"┃ 节点数量: {total_nodes}\n"
            f"┃ 国家范围: {node_range[:100]}\n"
            f"╰━━━━━━━━━━━━━━━━━━━━╯\n"
        )

        nodes_text = ""
        if show_nodes is None:
            show_nodes = nodes_fold_status.get(user_id, True)
        nodes_fold_status[user_id] = show_nodes

        if show_nodes and total_nodes > 0:
            start = page * nodes_per_page
            end = start + nodes_per_page
            chunk_nodes = filtered_nodes[start:end]
            node_lines = []
            for idx, node in enumerate(chunk_nodes, start=start+1):
                name = node.get("name","未知")[:15]
                flag = node.get("flag","") 
                node_lines.append(f"{name:<20} | {flag:2}")
            nodes_text = f" ╭──━━━🌐节点列表页 {page + 1}/{total_pages}🌐━━━──╮\n <pre>{'\n '.join(node_lines)}</pre>\n ╰━━━━━━━━━━━━━━━━━━━╯"

        elif show_nodes and total_nodes == 0:
            nodes_text = f" ╭─━━─━🌐节点列表🌐━─━━─╮\n <pre>⚠️ 该地区暂无节点哦～</pre>\n ╰━━━━━━━━━━━━━━━━╯"


        # ---------------- 按钮组try块内部！----------------
        keyboard = []
        page_buttons = []
        if page > 0:
            page_buttons.append(InlineKeyboardButton(" 上一页", callback_data=f"nodepage_{page-1}"))
        if page < total_pages - 1:
            page_buttons.append(InlineKeyboardButton("下一页 »", callback_data=f"nodepage_{page+1}"))
        page_buttons.append(InlineKeyboardButton(
            "展开节点" if not show_nodes else "收起节点",
            callback_data=f"toggle_nodes_{page}"
        ))
        keyboard.append(page_buttons)

        func_buttons = [
            InlineKeyboardButton("📥 下载节点配置", callback_data=f"download_nodes_{page}")
        ]
        keyboard.append(func_buttons)

        # ---------------- try块内部try-except结构 ----------------
        full_message = header_text + (nodes_text if show_nodes else "")
        print(f"header_text: {header_text}")
        print(f"nodes_text: {nodes_text}")
        try:
            if message_to_edit:
                await message_to_edit.edit_text(full_message, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            elif update.callback_query:
                await update.callback_query.edit_message_text(full_message, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(full_message, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as msg_err:
            prompt = "网络有点卡，稍后试试～" if "timed out" in str(msg_err).lower() else "稍后再试试吧～"
            logging.warning(f"发送消息出错：{str(msg_err)}")
            if update.callback_query:
                await update.callback_query.edit_message_text(prompt)
            else:
                await update.message.reply_text(prompt)


    # ---------------- 外层except和try配对 ----------------
    except Exception as e:
        logging.warning(f"加载页面出错: {str(e)}")
        prompt = f"⚠️ 页面加载失败：{str(e)}"
        if update.callback_query:
            await update.callback_query.edit_message_text(prompt)
        else:
            await update.message.reply_text(prompt)


# ---------------- 回调处理 --------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in nodes_cache:
        await query.edit_message_text("⚠️ 请先发送订阅链接哦～")
        return

    callback_data = query.data

    if callback_data.startswith("nodepage_"):
        parts = callback_data.split("_")
        page = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
        await send_nodes_page(update, context, user_id, page=page, message_to_edit=query.message)

    elif callback_data.startswith("toggle_nodes_"): 
        parts = callback_data.split("_")
        page = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else 0
        current_show = nodes_fold_status.get(user_id, False)
        new_show_status = not current_show
        nodes_fold_status[user_id] = new_show_status
        await send_nodes_page(update, context, user_id, page=page, show_nodes=new_show_status, message_to_edit=query.message)

    elif callback_data.startswith("download_nodes_"):
        parts = callback_data.split("_")
        page = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else 0
        try:
            import json
            import time
            from io import BytesIO

            data = nodes_cache[user_id]
            filter_country = user_filter_params.get(user_id, {}).get("country")
            filtered_nodes = data["nodes"]
            if filter_country and filter_country != "未知地区": 
                filtered_nodes = [n for n in filtered_nodes if n["country_name"] == filter_country]
            
            # 生成JSON格式配置内容
            config_content = json.dumps(filtered_nodes, ensure_ascii=False, indent=2)
            # 创建内存文件对象
            file = BytesIO(config_content.encode("utf-8"))
            file.name = f"节点配置_{filter_country or '全部地区'}_{time.strftime('%Y%m%d')}.json"

            # 发送配置文件给用户
            await query.message.reply_document(
                document=file,
                caption=f"✅ 已为您导出{len(filtered_nodes)}个节点配置\n📄 文件名：{file.name}"
            )
            await query.answer("配置文件已生成，正在发送～")
        except Exception as e:
            logging.warning(f"下载节点配置出错：{str(e)}")
            await query.answer("⚠️ 配置导出失败，请稍后重试")


# ---------------- 回调处理 --------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in nodes_cache:
        await query.edit_message_text("⚠️ 请先发送订阅链接哦～")
        return

    callback_data = query.data

    if callback_data.startswith("nodepage_"):
        parts = callback_data.split("_")
        page = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
        await send_nodes_page(update, context, user_id, page=page, message_to_edit=query.message)

    elif callback_data.startswith("toggle_nodes_"): 
        parts = callback_data.split("_")
        page = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else 0
        current_show = nodes_fold_status.get(user_id, False)
        new_show_status = not current_show
        nodes_fold_status[user_id] = new_show_status
        await send_nodes_page(update, context, user_id, page=page, show_nodes=new_show_status, message_to_edit=query.message)

    elif callback_data.startswith("download_nodes_"):
        parts = callback_data.split("_")
        page = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else 0
        try:
            import json
            import time
            from io import BytesIO

            data = nodes_cache[user_id]
            filter_country = user_filter_params.get(user_id, {}).get("country")
            filtered_nodes = data["nodes"]
            if filter_country and filter_country != "未知地区": 
                filtered_nodes = [n for n in filtered_nodes if n["country_name"] == filter_country]
            
            # 生成JSON格式配置内容
            config_content = json.dumps(filtered_nodes, ensure_ascii=False, indent=2)
            # 创建内存文件对象
            file = BytesIO(config_content.encode("utf-8"))
            file.name = f"节点配置_{filter_country or '全部地区'}_{time.strftime('%Y%m%d')}.json"

            # 发送配置文件给用户
            await query.message.reply_document(
                document=file,
                caption=f"✅ 已为您导出{len(filtered_nodes)}个节点配置\n📄 文件名：{file.name}"
            )
            await query.answer("配置文件已生成，正在发送～")
        except Exception as e:
            logging.warning(f"下载节点配置出错：{str(e)}")
            await query.answer("⚠️ 配置导出失败，请稍后重试")



# ---------------- 可选：订阅链接接收与解析函数 --------------------
async def handle_subscription_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """接收用户发送的订阅链接，解析后存入缓存并展示节点页面"""
    user_id = update.message.from_user.id
    subscription_url = update.message.text.strip()

    # 模拟从订阅链接获取数据（实际需根据订阅协议解析，如Base64解码等）
    try:
        # 示例：假设通过请求订阅链接获取JSON数据
        import requests
        resp = requests.get(subscription_url, timeout=10)
        resp.encoding = "utf-8"
        subscription_data = resp.json()

        # 整理数据存入缓存
        nodes_cache[user_id] = {
            "subscription_url": subscription_url,
            "nodes": subscription_data.get("nodes", []),
            "traffic_used": subscription_data.get("traffic_used", "隐藏"),
            "traffic_total": subscription_data.get("traffic_total", "隐藏"),
            "expired": subscription_data.get("expired", "隐藏"),
            "protocol": subscription_data.get("protocol", "未知")
        }
        # 初始化过滤参数
        user_filter_params[user_id] = {"country": "未知地区"}
        nodes_fold_status[user_id] = True

        # 首次展示节点页面
        await send_nodes_page(update, context, user_id, page=0)

    except Exception as e:
        logging.error(f"解析订阅链接出错：{str(e)}")
        await update.message.reply_text("⚠️ 订阅链接解析失败，请检查链接是否有效或稍后重试")


# ---------------- 可选：地区过滤按钮回调（拓展功能） --------------------
async def handle_country_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理地区过滤选择的回调"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in nodes_cache:
        await query.edit_message_text("⚠️ 请先发送订阅链接哦～")
        return

    callback_data = query.data
    if callback_data.startswith("filter_country_"):
        selected_country = callback_data.split("_")[-1]
        user_filter_params[user_id]["country"] = selected_country
        # 切换过滤条件后回到第一页
        await send_nodes_page(update, context, user_id, page=0, message_to_edit=query.message)






# ---------------- 命令 & 消息处理 --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start 命令处理"""
    await update.message.reply_text(
        "👋 欢迎使用【订阅工具】！\n"
        "直接发送订阅链接即可查看节点信息～\n"
    )






# ========== handle_subscription函数==========
async def handle_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理订阅/节点/混发（分栏显示解析中+实时进度数字）"""
    sub_content = update.message.text.strip()
    SUBSCRIPTION_PROTOS = {"http", "https"} 
    NODE_PROTOS = {
        "ss", "vmess", "trojan", "vless", "ssr ", "socks5",
        "trojan-go", "wireguard", "shadowsocksr", "tuic", "hysteria"
    }  
    ALL_PROTOS = SUBSCRIPTION_PROTOS.union(NODE_PROTOS)

    # ========== 1. 提取完整==========
    node_link_pattern = re.compile(
        rf'(?:{"|".join(ALL_PROTOS)})://[A-Za-z0-9+/=_\-./?&%#]+',
        re.IGNORECASE | re.MULTILINE
    )
    all_links = node_link_pattern.findall(sub_content)
    unique_links = list(dict.fromkeys(all_links))  # 严格去重+保序

    if not unique_links:
        await update.message.reply_text(
            "❌ 没检测到任何有效内容哦～\n请发送订阅链接"
        )
        return

    # 分组：订阅组 + 节点组
    sub_links = [link for link in unique_links if link.split("://")[0].lower() in SUBSCRIPTION_PROTOS]
    node_links = [link for link in unique_links if link.split("://")[0].lower() in NODE_PROTOS]
    sub_count = len(sub_links)
    node_count = len(node_links)

    # ========== 2. 初始化分栏进度提示 ==========
    # 构造分栏显示文本，比如“订阅解析中 0/2 | 节点解析中 0/3”
    def get_progress_text(sub_done, node_done):
        sub_part = f"📥 订阅解析中 {sub_done}/{sub_count}" if sub_count > 0 else ""
        node_part = f"🔗 节点解析中 {node_done}/{node_count}" if node_count > 0 else ""
        return " | ".join(filter(None, [sub_part, node_part]))

    loading_msg = await update.message.reply_text(get_progress_text(0, 0))

    # ========== 3. 分栏解析+实时更新进度数字 ==========
    valid_nodes = []
    fail_details = []
    sub_done = 0
    node_done = 0

    # 解析订阅组
    if sub_count > 0:
        for link in sub_links:
            try:
                parse_result = parse_clash_subscription(link)
                if parse_result.get("error"):
                    fail_details.append(f"- 订阅[{link[:30]}...]：{parse_result['error']}")
                else:
                    valid_nodes.extend(parse_result["nodes"])
                sub_done += 1
                # 实时更新订阅进度数字
                await loading_msg.edit_text(get_progress_text(sub_done, node_done))
            except Exception as e:
                fail_details.append(f"- 订阅[{link[:30]}...]：未知异常：{str(e)}")
                sub_done += 1
                await loading_msg.edit_text(get_progress_text(sub_done, node_done))

    # 解析节点组
    if node_count > 0:
        for link in node_links:
            try:
                parse_result = parse_clash_subscription(link)
                if parse_result.get("error"):
                    fail_details.append(f"- 节点[{link[:30]}...]：{parse_result['error']}")
                else:
                    valid_nodes.extend(parse_result["nodes"])
                node_done += 1
                # 实时更新节点进度数字
                await loading_msg.edit_text(get_progress_text(sub_done, node_done))
            except Exception as e:
                fail_details.append(f"- 节点[{link[:30]}...]：未知异常：{str(e)}")
                node_done += 1
                await loading_msg.edit_text(get_progress_text(sub_done, node_done))

    # ========== 4. 结果处理 ==========
    if not valid_nodes:
        error_msg = "失败原因如下：\n" + "\n".join(fail_details)
        await loading_msg.edit_text(error_msg)
        return

    seen_node_keys = set()
    final_nodes = []
    # 新增：缓存成功订阅的解析结果，用于后续取流量信息
    success_sub_results = []
    for link in sub_links:
        try:
            res = parse_clash_subscription(link)
            if "error" not in res:
                success_sub_results.append(res)
        except:
            pass

    # 去重节点（保持原逻辑）
    for node in valid_nodes:
        node_key = f"{node['name']}_{node['protocol']}_{node['server']}_{node['port']}"
        if node_key not in seen_node_keys:
            seen_node_keys.add(node_key)
            final_nodes.append(node)


    user_id = update.effective_user.id
    # 取第一个成功的订阅结果的信息，没有则用默认值
    default_sub_info = {
        "subscription_url": "内容",
        "traffic_used": "隐藏",
        "traffic_total": "隐藏",
        "expired": "隐藏"
    }
    selected_sub = success_sub_results[0] if success_sub_results else default_sub_info

    merged_result = {
        "subscription_url": selected_sub["subscription_url"],
        "traffic_used": selected_sub["traffic_used"],
        "traffic_total": selected_sub["traffic_total"],
        "expired": selected_sub["expired"],
        "protocol": ",".join(list(set(n["protocol"] for n in final_nodes))),
        "total_nodes": len(final_nodes),
        "nodes": final_nodes,
        "all_countries": list(set(n["country_name"] for n in final_nodes)) if final_nodes else ["未知地区"]
    }

    nodes_cache[user_id] = merged_result
    nodes_fold_status[user_id] = False
    user_filter_params[user_id] = {"country": None}
    await send_nodes_page(update, context, user_id, page=0, message_to_edit=loading_msg)

# 分栏提示结果
    sub_success = sub_count - sum(1 for d in fail_details if '订阅' in d)
    node_success = node_count - sum(1 for d in fail_details if '节点' in d)



    # ---------------- 放进字符串里显示 ----------------
    tip_msg = f"📥 订阅：{sub_success}/{sub_count} 成功\n"
    tip_msg += f"🔗 节点：{node_success}/{node_count} 成功\n"

    if fail_details:
        tip_msg += "\n💡 失败原因：\n" + "\n".join(fail_details)

    await update.message.reply_text(tip_msg)







# ---------------- 主函数 --------------------
def main() -> None:
    defaults = Defaults(parse_mode="HTML")
    application = ApplicationBuilder().token(BOT_TOKEN).defaults(defaults).build()

    # 注册处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_subscription))
    application.add_handler(CallbackQueryHandler(handle_callback))

    print("🚀 机器人启动成功了～")
    application.run_polling()


if __name__ == "__main__":
    main()