class FFmpegFilters:
    @staticmethod
    async def mp3_conversion_filter(filepath, converted_filepath):
        try:
            command = [
                "ffmpeg",
                "-y",                      
                "-i", str(filepath),     
                "-ac", "1",                
                "-ar", "16000",            
                "-c:a", "libmp3lame",   
                "-b:a", "48k",
                str(converted_filepath)
            ]
            return command
        except Exception:
            raise
        
    @staticmethod
    def audio_speedup(filepath):
        try:
            converted_filepath = filepath.with_name(filepath.stem + "_1_1_x.mp3")
            command = [
                "ffmpeg",
                "-y",
                "-i", str(filepath),
                "-filter:a", f"atempo={1.2}",
                "-vn",
                str(converted_filepath)
            ]
            return command
        except Exception:
            raise