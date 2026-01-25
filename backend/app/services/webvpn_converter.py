"""
WebVPN URL Converter for USTB (北京科技大学)

Based on: https://github.com/lcandy2/webvpn-converter
Encryption method: AES-128-CFB
"""
from Crypto.Cipher import AES
from urllib.parse import urlparse


# 北京科技大学 WebVPN 配置
VPN_HOST = "elib.ustb.edu.cn"
VPN_KEY = b"wrdvpnisthebest!"
VPN_IV = b"wrdvpnisthebest!"
PROTOCOLS = ["http", "https", "ftp"]


def text_right_append(text: str, mode: str = "utf8") -> str:
    """
    右侧填充文本到AES块大小的倍数

    Args:
        text: 要填充的文本
        mode: 模式 ('utf8' 或其他)

    Returns:
        填充后的文本
    """
    segment_byte_size = 16 if mode == "utf8" else 32
    append_length = segment_byte_size - (len(text) % segment_byte_size)
    if append_length == segment_byte_size:
        return text
    return text + "0" * append_length


def encrypt_host(host: str, key: bytes = VPN_KEY, iv: bytes = VPN_IV) -> str:
    """
    加密主机名

    Args:
        host: 主机名 (如 "202.204.60.7")
        key: AES密钥
        iv: AES初始化向量

    Returns:
        加密后的十六进制字符串
    """
    # 填充文本
    padded_text = text_right_append(host, "utf8")

    # 创建AES-CFB加密器
    cipher = AES.new(key, AES.MODE_CFB, iv, segment_size=128)

    # 加密
    encrypted = cipher.encrypt(padded_text.encode('utf-8'))

    # 返回: IV的十六进制 + 加密数据的十六进制（截取到原始文本长度）
    iv_hex = iv.hex()
    encrypted_hex = encrypted.hex()[:len(host) * 2]

    return iv_hex + encrypted_hex


def decrypt_host(encrypted_host: str, key: bytes = VPN_KEY, iv: bytes = VPN_IV) -> str:
    """
    解密主机名

    Args:
        encrypted_host: 加密的十六进制字符串
        key: AES密钥
        iv: AES初始化向量

    Returns:
        解密后的主机名
    """
    # 提取IV和加密数据
    iv_length = len(iv) * 2  # 十六进制长度是字节长度的2倍
    encrypted_hex = encrypted_host[iv_length:]

    # 计算原始文本长度
    text_length = len(encrypted_hex) // 2

    # 填充加密数据
    padded_encrypted_hex = text_right_append(encrypted_hex, "hex")
    encrypted_bytes = bytes.fromhex(padded_encrypted_hex)

    # 创建AES-CFB解密器
    cipher = AES.new(key, AES.MODE_CFB, iv, segment_size=128)

    # 解密
    decrypted = cipher.decrypt(encrypted_bytes)

    # 返回原始长度的文本
    return decrypted[:text_length].decode('utf-8')


def extract_url_parts(url: str) -> dict:
    """
    提取URL的各个部分

    Args:
        url: 完整URL或主机名

    Returns:
        包含protocol, host, port, path的字典
    """
    url = url.strip()
    protocol = "http"
    host = ""
    port = ""
    path = ""

    # 提取协议
    for proto in PROTOCOLS:
        prefix = f"{proto}://"
        if url.lower().startswith(prefix):
            protocol = proto
            url = url[len(prefix):]
            break

    # 提取端口
    segments = url.split("?")[0].split(":")
    if len(segments) > 1:
        port = segments[1].split("/")[0]
        url = segments[0] + url[len(segments[0]) + len(port) + 1:]

    # 提取主机和路径
    path_start = url.find("/")
    if path_start != -1:
        host = url[:path_start]
        path = url[path_start:]
    else:
        host = url
        path = ""

    return {
        "protocol": protocol,
        "host": host,
        "port": port,
        "path": path
    }


def convert_to_webvpn(url: str, vpn_host: str = VPN_HOST, key: bytes = VPN_KEY, iv: bytes = VPN_IV) -> str:
    """
    将普通URL转换为WebVPN URL

    Args:
        url: 原始URL (如 "http://202.204.60.7/")
        vpn_host: WebVPN主机 (默认: elib.ustb.edu.cn)
        key: AES密钥
        iv: AES初始化向量

    Returns:
        WebVPN URL (如 "https://elib.ustb.edu.cn/http/77726476706e69737468656265737421a2a713d275603c1e2a50c7face/")

    Examples:
        >>> convert_to_webvpn("http://202.204.60.7/")
        'https://elib.ustb.edu.cn/http/77726476706e69737468656265737421a2a713d275603c1e2a50c7face/'

        >>> convert_to_webvpn("http://202.204.48.66:801/eportal/portal/visitor/loadUserFlow")
        'https://elib.ustb.edu.cn/http-801/77726476706e69737468656265737421a2a713d275603c1e2a50c7face/eportal/portal/visitor/loadUserFlow'
    """
    parts = extract_url_parts(url)

    # 加密主机名
    encrypted_host = encrypt_host(parts["host"], key, iv)

    # 构建WebVPN URL
    if parts["port"]:
        return f"https://{vpn_host}/{parts['protocol']}-{parts['port']}/{encrypted_host}{parts['path']}"
    else:
        return f"https://{vpn_host}/{parts['protocol']}/{encrypted_host}{parts['path']}"


def convert_from_webvpn(webvpn_url: str, key: bytes = VPN_KEY, iv: bytes = VPN_IV) -> str:
    """
    将WebVPN URL转换回普通URL

    Args:
        webvpn_url: WebVPN URL
        key: AES密钥
        iv: AES初始化向量

    Returns:
        原始URL
    """
    parts = extract_url_parts(webvpn_url)
    path_segments = parts["path"].split("/")

    if len(path_segments) < 3:
        raise ValueError("Invalid WebVPN URL format")

    # 提取协议和端口
    protocol_part = path_segments[1]
    if "-" in protocol_part:
        protocol, port = protocol_part.split("-", 1)
    else:
        protocol = protocol_part
        port = ""

    # 提取加密的主机名
    encrypted_host = path_segments[2]

    # 解密主机名
    decrypted_host = decrypt_host(encrypted_host, key, iv)

    # 重建路径
    remaining_path = "/".join(path_segments[3:])
    if remaining_path:
        remaining_path = "/" + remaining_path

    # 构建原始URL
    if port:
        return f"{protocol}://{decrypted_host}:{port}{remaining_path}"
    else:
        return f"{protocol}://{decrypted_host}{remaining_path}"


# 预定义的常用校园网地址
COMMON_URLS = {
    "auth": "http://202.204.60.7/",  # 校园网认证页
    "flow_api": "http://202.204.48.66:801/eportal/portal/visitor/loadUserFlow",  # 流量查询API
}


def get_webvpn_url(name: str) -> str:
    """
    获取预定义的WebVPN URL

    Args:
        name: 预定义名称 ('auth' 或 'flow_api')

    Returns:
        WebVPN URL
    """
    if name not in COMMON_URLS:
        raise ValueError(f"Unknown URL name: {name}. Available: {list(COMMON_URLS.keys())}")

    return convert_to_webvpn(COMMON_URLS[name])


if __name__ == "__main__":
    # 测试加密
    print("Testing WebVPN URL Converter for USTB")
    print("=" * 60)

    # 测试1: 校园网认证页
    test_url1 = "http://202.204.60.7/"
    vpn_url1 = convert_to_webvpn(test_url1)
    print(f"\n1. 校园网认证页:")
    print(f"   原始URL: {test_url1}")
    print(f"   WebVPN:  {vpn_url1}")

    # 测试2: 流量查询API
    test_url2 = "http://202.204.48.66:801/eportal/portal/visitor/loadUserFlow"
    vpn_url2 = convert_to_webvpn(test_url2)
    print(f"\n2. 流量查询API:")
    print(f"   原始URL: {test_url2}")
    print(f"   WebVPN:  {vpn_url2}")

    # 测试3: 解密
    print(f"\n3. 解密测试:")
    decrypted = convert_from_webvpn(vpn_url1)
    print(f"   WebVPN:  {vpn_url1}")
    print(f"   解密后:  {decrypted}")
    print(f"   匹配:    {decrypted == test_url1}")

    # 测试4: 使用预定义URL
    print(f"\n4. 预定义URL:")
    print(f"   auth:     {get_webvpn_url('auth')}")
    print(f"   flow_api: {get_webvpn_url('flow_api')}")
