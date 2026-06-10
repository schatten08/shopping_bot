import os
import subprocess
import urllib.request

def setup_ffmpeg():
    if not os.path.exists("ffmpeg_bin"):
        print("Downloading ffmpeg...")
        os.makedirs("ffmpeg_bin", exist_ok=True)
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        tar_path = "ffmpeg.tar.xz"
        
        try:
            urllib.request.urlretrieve(url, tar_path)
            print("Extracting ffmpeg...")
            subprocess.run(["tar", "xvf", tar_path, "-C", "ffmpeg_bin", "--strip-components=1"], check=True)
            os.remove(tar_path)
            print("FFmpeg setup complete.")
        except Exception as e:
            print(f"Error setting up ffmpeg: {e}")

if __name__ == "__main__":
    setup_ffmpeg()
