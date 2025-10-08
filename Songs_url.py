import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from html.entities import name2codepoint
import ssl
#import chardet
from typing import List, Dict, Optional


class SongParser(HTMLParser):
    """HTML解析器，用于提取网易云音乐歌单中的歌曲信息"""
    
    def __init__(self):
        super().__init__()
        self.in_song_list = False
        self.current_song: Optional[Dict] = None
        self.song_links: List[Dict] = []
    
    def handle_starttag(self, tag: str, attrs: List[tuple]):
        # 检查是否进入歌曲列表区域
        if tag == "ul":
            for attr, value in attrs:
                if attr == "class" and "f-hide" in value:
                    self.in_song_list = True
                    break
        
        # 在歌曲列表区域内提取歌曲链接
        if self.in_song_list and tag == "a":
            href = self._get_attr_value(attrs, "href")
            if href and href.startswith("/song"):
                self.current_song = {"href": href}
    
    def handle_data(self, data: str):
        # 提取歌曲名称
        if self.in_song_list and self.current_song:
            cleaned_data = data.strip()
            if cleaned_data:
                self.current_song["name"] = cleaned_data
    
    def handle_endtag(self, tag: str):
        if tag == "a" and self.current_song:
            # 保存完整的歌曲信息
            if self.current_song.get("name"):
                self.song_links.append(self.current_song)
            self.current_song = None
        
        if tag == "ul" and self.in_song_list:
            self.in_song_list = False
    
    def _get_attr_value(self, attrs: List[tuple], target_attr: str) -> Optional[str]:
        """从属性列表中获取指定属性的值"""
        for attr, value in attrs:
            if attr == target_attr:
                return value
        return None


class SongExtractor:
    """歌曲信息提取器"""
    
    def __init__(self, cookie: str = ""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://music.163.com/',
            'Cookie': cookie,
        }
        self.ssl_context = self._create_ssl_context()
    
    def _create_ssl_context(self):
        """创建SSL上下文"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    
    def _detect_encoding(self, content):
        """检测内容的编码（简化版，无需chardet）"""
        common_encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5']
    
        for encoding in common_encodings:
            try:
                content.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
    
    # 如果所有编码都失败，使用UTF-8并忽略错误
        return 'utf-8'
    
    def get_song_links(self, playlist_url: str) -> List[Dict]:
        """
        提取网易云音乐歌单中的所有歌曲链接
        
        Args:
            playlist_url: 歌单URL
            
        Returns:
            包含歌曲信息的字典列表
        """
        # 预处理URL
        effective_url = playlist_url.replace('/#', '')
        
        try:
            # 创建请求
            req = urllib.request.Request(effective_url, headers=self.headers)
            
            # 发送请求
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=30) as response:
                html_content_bytes = response.read()
            
            # 检测编码并解码
            encoding = self._detect_encoding(html_content_bytes)
            try:
                html_content = html_content_bytes.decode(encoding)
            except UnicodeDecodeError:
                # 如果检测的编码失败，尝试UTF-8和GBK
                try:
                    html_content = html_content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    html_content = html_content_bytes.decode('gbk', errors='replace')
            
            # 解析HTML
            parser = SongParser()
            parser.feed(html_content)
            
            return parser.song_links
            
        except urllib.error.URLError as e:
            print(f"网络请求错误: {e}")
        except Exception as e:
            print(f"提取过程中出现错误: {e}")
        
        return []
    
    def get_songs_url_list(self, playlist_url: str) -> List[str]:
        """
        获取歌单中所有歌曲的完整URL列表
        
        Args:
            playlist_url: 歌单URL
            
        Returns:
            歌曲URL列表
        """
        songs = self.get_song_links(playlist_url)
        
        if not songs:
            print("未能提取到歌曲信息")
            return []
        
        song_urls = []
        base_url = "https://music.163.com"
        
        for song in songs:
            if song.get("href") and song.get("name"):
                song_url = base_url + song["href"]
                song_urls.append(song_url)
                print(f"✓ 找到歌曲: {song['name']}")
        
        print(f"共找到 {len(song_urls)} 首歌曲")
        return song_urls

cookie = input("请输入cookie: ").strip()
extractor = SongExtractor(cookie=cookie)
# 保持向后兼容的全局函数
def get_songs_url_list(playlist_url: str) -> List[str]:
    """获取歌曲URL列表（兼容旧版本）"""
    return extractor.get_songs_url_list(playlist_url)


def get_song_links(playlist_url: str) -> List[Dict]:
    """获取歌曲链接信息（兼容旧版本）"""
    return extractor.get_song_links(playlist_url)


if __name__ == "__main__":
    # 测试功能
    test_url = "https://music.163.com/#/playlist?id=13216355356"
    urls = get_songs_url_list(test_url)
    print(f"获取到 {len(urls)} 个歌曲URL")