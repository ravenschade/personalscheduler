from google.cloud import speech_v1 as speech
from dotenv import dotenv_values
import io
from subprocess import Popen, PIPE, STDOUT

def speech_to_text(audio_file):
    #convert to flac
    cmd="./toflac \""+audio_file+"\""
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read().decode()
    print(output)

    envconfig = dotenv_values(".env")
    #encode audio file to 
    api_key_string=envconfig["google_api_token"]
    client = speech.SpeechClient(client_options={"api_key": api_key_string})
    with io.open("/tmp/audio.flac", "rb") as afile:
        content = afile.read()
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code="de-DE",
    )

    response = client.recognize(config=config, audio=audio)
    ret=""
    for result in response.results:
        best_alternative = result.alternatives[0]
        transcript = best_alternative.transcript
        ret=ret+transcript+". "
        confidence = best_alternative.confidence
        print(f"Transcript: {transcript}")
        print(f"Confidence: {confidence:.0%}")
    return ret

#speech_to_text("/home/robert/.local/share/signal-cli/attachments/k26MeUS1WzznKy1b4uR9.aac")
