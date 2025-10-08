import os
import time
import requests
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC, TIT2, TPE1, TALB
from mutagen.id3._util import ID3NoHeaderError
from Songs_url import get_songs_url_list
from Lyrics import merge_lyrics
import random


class MusicDownloader:
    def __init__(self, base_dir="C:/Users/"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        # 设置更友好的请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        
    def download_binary_file(self, url, filepath, max_retries=3):
        """下载二进制文件，带有重试机制"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                filepath = Path(filepath)
                filepath.parent.mkdir(parents=True, exist_ok=True)
                
                with open(filepath, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                
                print(f"✓ 文件已保存: {filepath}")
                return True
                
            except requests.exceptions.RequestException as e:
                print(f"✗ 下载失败 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # 递增等待时间
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    return False
    
    def get_song_data(self, song_url, max_retries=3):
        """获取歌曲数据，带有重试机制"""
        api_url = f"https://api.kxzjoker.cn/api/163_music?url={song_url}&userid=8719916627&dlt=0846&level=standard&type=json"
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(api_url, timeout=30)
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                print(f"✗ 获取歌曲数据失败 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # 递增等待时间
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    return None
    
    def embed_metadata_to_mp3(self, mp3_path, cover_path, title, artist, album):
        """将元数据嵌入MP3文件"""
        try:
            # 确保文件存在
            mp3_path = Path(mp3_path)
            cover_path = Path(cover_path)
            
            if not mp3_path.exists():
                print(f"✗ MP3文件不存在: {mp3_path}")
                return False
                
            if not cover_path.exists():
                print(f"✗ 封面文件不存在: {cover_path}")
                return False
            
            # 读取图片数据
            with open(cover_path, 'rb') as f:
                cover_data = f.read()
            
            # 处理MP3文件 - 使用字符串路径而不是Path对象
            try:
                audio = MP3(str(mp3_path), ID3=ID3)
            except ID3NoHeaderError:
                audio = MP3(str(mp3_path))
                audio.add_tags()
            
            # 确保tags存在
            if audio.tags is None:
                audio.add_tags()
            
            # 清除可能存在的旧标签
            try:
                audio.tags.delete()
            except:
                pass  # 如果删除失败，继续
            
            # 添加标题 (TIT2)
            audio.tags.add(TIT2(encoding=3, text=title))
            
            # 添加艺术家 (TPE1)
            audio.tags.add(TPE1(encoding=3, text=artist))
            
            # 添加专辑 (TALB)
            audio.tags.add(TALB(encoding=3, text=album))
            
            # 添加封面
            audio.tags.add(
                APIC(
                    encoding=3,
                    mime='image/png',
                    type=3,  # 封面图片
                    desc='Cover',
                    data=cover_data
                )
            )
            
            # 保存文件
            audio.save()
            print(f"✓ 元数据嵌入成功: {mp3_path}")
            return True
            
        except Exception as e:
            print(f"✗ 元数据嵌入失败: {e}")
            return False
    
    def create_unique_directory(self, base_name):
        """创建唯一的目录名"""
        base_path = self.base_dir / base_name
        path = base_path
        counter = 1
        
        while path.exists():
            path = base_path.parent / f"{base_path.name}({counter})"
            counter += 1
        
        path.mkdir(parents=True)
        return path
    
    def process_song(self, song_url):
        """处理单首歌曲下载"""
        try:
            # 获取歌曲信息
            song_data = self.get_song_data(song_url)
            if song_data is None:
                return False
            
            # 验证必要字段
            required_fields = ["name", "ar_name", "al_name", "url", "pic", "lyric", "tlyric"]
            for field in required_fields:
                if field not in song_data:
                    raise KeyError(f"缺少必要字段: {field}")
            
            # 创建安全文件名和目录
            song_name = self.sanitize_filename(song_data["name"])
            artist_name = self.sanitize_filename(song_data["ar_name"])
            album_name = self.sanitize_filename(song_data["al_name"])
            folder_name = f"{song_name}-{artist_name}"
            
            # 创建目录
            song_dir = self.create_unique_directory(folder_name)
            
            # 文件路径
            mp3_path = song_dir / f"{folder_name}.mp3"
            cover_path = song_dir / f"{folder_name}.png"
            lrc_path = song_dir / f"{folder_name}.lrc"
            
            print(f"开始下载: {song_name} - {artist_name} - {album_name}")
            
            # 下载文件
            if not self.download_binary_file(song_data["url"], mp3_path):
                return False
                
            if not self.download_binary_file(song_data["pic"], cover_path):
                return False
            
            # 等待文件完全写入
            time.sleep(1)
            
            # 嵌入元数据
            if not self.embed_metadata_to_mp3(
                mp3_path, 
                cover_path, 
                title=song_name,
                artist=artist_name,
                album=album_name
            ):
                return False
            
            # 删除临时封面文件
            try:
                cover_path.unlink()
            except OSError:
                pass  # 如果文件不存在或无法删除，忽略错误
            
            # 保存歌词
            lyrics_content = merge_lyrics(song_data["lyric"], song_data["tlyric"])
            with open(lrc_path, "w", encoding="utf-8") as f:
                f.write("".join(lyrics_content))
            
            print(f"✓ 歌曲处理完成: {folder_name}")
            return True
            
        except KeyError as e:
            print(f"✗ 歌曲信息不完整 {song_url}: {e}")
            return False
        except Exception as e:
            print(f"✗ 处理歌曲失败 {song_url}: {e}")
            return False
    
    def sanitize_filename(self, filename):
        """清理文件名中的非法字符"""
        if not filename:
            return "unknown"
            
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, ',')
        return filename.strip()
    
    def download_playlist(self, playlist_url, base_delay=1, jitter=1):
        """下载整个歌单，带有随机延迟"""
        print(f"开始处理歌单: {playlist_url}")
        song_urls = get_songs_url_list(playlist_url)
        
        if not song_urls:
            print("未获取到歌曲列表")
            return
        
        print(f"找到 {len(song_urls)} 首歌曲")
        
        success_count = 0
        for i, song_url in enumerate(song_urls, 1):
            print(f"\n[{i}/{len(song_urls)}] 处理歌曲...")
            if self.process_song(song_url):
                success_count += 1
            
            # 在歌曲之间添加随机延迟，避免请求过于频繁
            if i < len(song_urls):  # 最后一首歌曲后不需要延迟
                delay = base_delay + random.uniform(0, jitter)
                print(f"等待 {delay:.1f} 秒后处理下一首歌曲...")
                time.sleep(delay)
        
        print(f"\n🎉 下载完成! 成功: {success_count}/{len(song_urls)}")


def main():
    base_dir = input("请输入保存目录 ").strip()
    downloader = MusicDownloader(base_dir=base_dir)
    playlist_url = input("请输入歌单链接: ").strip()
    downloader.download_playlist(playlist_url, base_delay=0.2, jitter=0.1)
   


if __name__ == "__main__":
    main()