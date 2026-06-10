import os
import subprocess
import tarfile
import urllib.request

def setup():
    print("Installing requirements...")
    subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)

    if not os.path.exists("ffmpeg_bin"):
        print("Downloading ffmpeg...")
        os.makedirs("ffmpeg_bin", exist_ok=True)
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        tar_path = "ffmpeg.tar.xz"
        
        urllib.request.urlretrieve(url, tar_path)
        
        print("Extracting ffmpeg...")
        # Note: tarfile module might have issues with .xz in older python, 
        # but Render has 3.11+, so it should be fine.
        # However, calling 'tar' via subprocess is even safer in Linux.
        subprocess.run(["tar", "xvf", tar_path, "-C", "ffmpeg_bin", "--strip-components=1"], check=True)
        os.remove(tar_path)
        print("FFmpeg setup complete.")

if __name__ == "__main__":
    setup()
