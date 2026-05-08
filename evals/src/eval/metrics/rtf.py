

def rtf(wall_s: float, audio_s: float) -> float:
    if audio_s <= 0:
        return 0.0
    return wall_s / audio_s
