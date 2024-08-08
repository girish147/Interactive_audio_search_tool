import subprocess
import speech_recognition as sr
from os import path
from pydub import AudioSegment
import threading
import tempfile
import keyboard

def extract_audio(video_path, output_path):
    try:
        subprocess.run(['ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', output_path], check=True)
    except subprocess.CalledProcessError as e:
        print("Error extracting audio:", e)

STARTING_SEGMENT = '<s>'
ENDING_SEGMENT = '</s>'
SYLLABLE_SEGMENT = '<sil>'
NON_TEXT_SEGMENTS = [STARTING_SEGMENT, ENDING_SEGMENT, SYLLABLE_SEGMENT]

def get_audio_Data(audio_file_name):
    r = sr.Recognizer()
    with sr.AudioFile(audio_file_name) as source:
        audioData = r.record(source)
        duration = source.DURATION
    return audioData, duration

def get_audio_segments(audioData, segmentSize, duration):
    r = sr.Recognizer()
    cur = 0
    segments = {}
    while cur < duration:
        next_segment = cur + segmentSize
        print(f"retrieving segment from {cur} of size - {segmentSize}")
        segment_audio = audioData.get_segment(cur, next_segment)
        text = get_text_from_audio(segment_audio)
        segments[text] = cur
        cur = next_segment
    return segments

def get_text_segments_from_audio(audioData):
    r = sr.Recognizer()
    segments = {}
    try:
        decoder = r.recognize_sphinx(audioData, show_all=True)
        for seg in decoder.seg():
            print(f"Checking segment [{seg.word}] begins at {seg.start_frame / 100} & ends at {seg.end_frame / 100} seconds")
            if seg.word not in NON_TEXT_SEGMENTS:
                time_frame = (seg.start_frame / 100, seg.end_frame / 100)
                if seg.word in segments:
                    segments[seg.word].append(time_frame)
                else:
                    segments[seg.word] = [time_frame]
            else:
                print(f"Skipping segment - {seg.word}")
    except sr.UnknownValueError:
        print("Sphinx could not understand audio")
    except sr.RequestError as e:
        print(f"Sphinx error; {e}")
    return segments

def get_text_from_audio(audioData):
    r = sr.Recognizer()
    text = ''
    try:
        text = r.recognize_sphinx(audioData)
        print("Sphinx thinks you said \n" + text)
    except sr.UnknownValueError:
        print("Sphinx could not understand audio")
    except sr.RequestError as e:
        print(f"Sphinx error; {e}")
    return text

def play_segment(audio_file_path, start_time, stop_event, finished_event):
    audio = AudioSegment.from_wav(audio_file_path)
    segment = audio[start_time * 1000:]  # pydub works in milliseconds
    stop_event.clear()
    
    # Create a temporary file for the segment
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
        segment.export(tmpfile.name, format="wav")
        tmp_audio_path = tmpfile.name

    def play_audio():
        subprocess.run(['ffplay', '-nodisp', '-autoexit', tmp_audio_path])

    play_thread = threading.Thread(target=play_audio)
    play_thread.start()

    while play_thread.is_alive():
        if stop_event.is_set():
            play_thread.join()
            break
        continue

    finished_event.set()

def stop_audio_on_keypress(stop_event, finished_event):
    keyboard.wait('enter')
    stop_event.set()
    finished_event.set()

if __name__ == '__main__':
    video_name = input("Enter the name of the video file: ")
    video_path = path.join(path.realpath("C:\\Users\\dsgir\\OneDrive\\Desktop\\mini_project\\Proj\\Proj"), video_name + ".mp4")
    audio_path = path.join(path.realpath("C:\\Users\\dsgir\\OneDrive\\Desktop\\mini_project\\Proj\\Proj"), video_name + ".wav")
    extract_audio(video_path, audio_path)
    audioData, duration = get_audio_Data(audio_path)
    entire_text = get_text_from_audio(audioData)
    print(f'Entire text for the audio file - {audio_path} : {entire_text}')
    segments = get_text_segments_from_audio(audioData)
    
    print("Enter text to see the occurrence: ")
    
    key = input()
    if key in segments:
        frames = segments[key]
        num_times = len(frames)
        if num_times > 1:
            print(f"The text [{key}] repeated {num_times} times in the audio file as shown below:")
            for i, frame in enumerate(frames):
                print(f"{i + 1}. Starts at {frame[0]} and ends at {frame[1]}")
            
            print("Enter the number of the segment you want to play: ")
            segment_number = int(input())
            if 1 <= segment_number <= num_times:
                start_time, _ = frames[segment_number - 1]
                
                stop_event = threading.Event()
                finished_event = threading.Event()
                audio_thread = threading.Thread(target=play_segment, args=(audio_path, start_time, stop_event, finished_event))
                audio_thread.start()
                
                stop_audio_on_keypress(stop_event, finished_event)
                if audio_thread.is_alive():
                    stop_event.set()
                    audio_thread.join()
        else:
            print(f"The text [{key}] occurred once starting at {frames[0][0]} and ends at {frames[0][1]}")
            start_time, _ = frames[0]
            
            stop_event = threading.Event()
            finished_event = threading.Event()
            audio_thread = threading.Thread(target=play_segment, args=(audio_path, start_time, stop_event, finished_event))
            audio_thread.start()
            
            stop_audio_on_keypress(stop_event, finished_event)
            if audio_thread.is_alive():
                stop_event.set()
                audio_thread.join()
    else:
        print(f"The text [{key}] not found in the given audio file. Please check the input.")
    
    # Wait for audio playback to finish or be stopped
    finished_event.wait()
    print("Exiting program.")
