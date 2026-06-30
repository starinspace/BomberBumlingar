import json
import math
import random
import argparse
import io
import zipfile
import zlib
import struct
from pathlib import Path
from array import array

import pygame
from pic_decoder import load_pic_surface

TILE = 16
MAP_W, MAP_H = 80, 25

VIEW_W = 20
VIEW_H = 13

HUD_H = 16
SCREEN_W = VIEW_W * TILE
SCREEN_H = VIEW_H * TILE + HUD_H
SCALE = 3
MIN_SCREEN_W = SCREEN_W
BASE_WINDOW_W = SCREEN_W * SCALE
BASE_WINDOW_H = SCREEN_H * SCALE

fullscreen_enabled = False
windowed_size = (BASE_WINDOW_W, BASE_WINDOW_H)
canvas = None
window = None

MAP_SIZE = MAP_W * MAP_H
LEVEL_SIZE = 2002

# Första LVL-posten är prövbana. Riktig bana 1 ligger alltså på index 1.
PRACTICE_LEVEL_INDEX = 0
FIRST_REAL_LEVEL_INDEX = 1

LEVEL_CODES = {
    "312": 10,
    "171": 20,
    "716": 30,
}

LEVEL_TO_CODE = {
    10: "312",
    20: "171",
    30: "716",
}

LVL_FILE = "LVLS.LVL"
OBJECTS_FILE = "OBJECTS.PIC"
TITLE_TOP_FILE = "3DTOP.PIC"
TITLE_INTRO_FILE = "INTRO.PIC"
TITLE_NAMES_FILE = "NAMES.PIC"
TITLE_EOF_FILE = "EOF.PIC"
DEMO_BADGE_FILE = "DEM.PIC"
DEMO_BADGE_X = 232
DEMO_BADGE_Y = 66
DEMO_BADGE_W = 57
DEMO_BADGE_H = 21
TOPTEN_FILE = "TOPTEN.DAT"
MACRO_FILE = "MACRO"
SPRITE_MAP_FILE = "sprite_map.json"
BITMAP_FONT_FILE = "font.json"

data = Path(LVL_FILE).read_bytes()
level_count = len(data) // LEVEL_SIZE

level_index = 0
grid = []
player_x = 0
player_y = 0

diamonds = 0
required_diamonds = 0
alive = True
MAX_LIVES = 5
lives = MAX_LIVES
death_restart_time = None
DEATH_RESTART_MS = 900
death_waiting_for_key = False
death_fade_active = False
death_fade_start = 0
DEATH_FADE_MS = 250
sound_enabled = True
sound_available = False
sound_cache = {}
last_sound_time = {}

SOUND_MODE_SOUNDBLASTER = "soundblaster"
SOUND_MODE_SPEAKER = "speaker"
SOUND_MODE_ORIGINAL = "original"
sound_mode = SOUND_MODE_ORIGINAL
sound_cycle_index = {}
debug_mode = False
demo_only_mode = False

AUDIO_RATE = 22050
SOUND_MASTER_VOLUME = 0.32

# Experimentellt musikstöd. MUSIC.OUT är ett litet eventformat skapat från MIDI.
# Ljudläge "auto" följer spelets ljudläge:
#   speaker      -> enkanalig PC-speaker/arpeggio
#   soundblaster -> enkel polyfon sampled synth
#   original     -> soundblaster-lik musik, så att de packade effekterna kan mixas
MUSIC_FILE = "MUSIC.OUT"
MUSIC_MODE_AUTO = "auto"
MUSIC_MODE_SOUNDBLASTER = "soundblaster"
MUSIC_MODE_SPEAKER = "speaker"
MUSIC_MODE_C64 = "c64"
music_file = MUSIC_FILE
music_mode = MUSIC_MODE_AUTO
music_enabled = False
music_available = False
music_channel = None
music_sound = None
music_intro_sound = None
music_loop_sound = None
music_loop_started = False
music_loop_switch_at = 0
music_current_key = None
music_runtime_mode = None
music_volume = 0.18
music_duck_until = 0


keys = {"$": 0, "%": 0, "^": 0, "&": 0}

falling_items = set()
enemy_dirs = {}
enemy_tick = 0

fall_timer = 0
enemy_timer = 0

FALL_MS = 95
ENEMY_MS = 260

MOVE_REPEAT_DELAY = 220
MOVE_REPEAT_MS = 95

held_dx = 0
held_dy = 0
held_source = None
next_move_time = 0

joysticks = {}
joystick_dig_buttons = {0, 1}
joystick_axis_centers = {}
joystick_deadzone = 0.45
joystick_remap_active = False
joystick_remap_started = 0
joystick_config_file = "joystick.json"

code_mode = False
code_text = ""
message = ""

topten_screen = False

highscore_entry = False
highscore_name = ""
highscore_level = 0
highscore_insert_index = None
HIGHSCORE_NAME_MAX = 25
restart_from_beginning_after_topten = False

level_intro = True
level_intro_start_time = 0
level_intro_closing = False
level_intro_closing_start = 0
LEVEL_INTRO_CLOSE_MS = 250

# När spelaren går in i utgången ska originalet först göra en slumpad
# fade/wipe över den färdiga banan innan nästa nivå-titel visas.
level_complete_transition = False
level_complete_transition_start = 0
level_complete_transition_target = 0
level_complete_transition_mode = 0

level_code_intro = False
level_code_intro_closing = False
level_code_intro_closing_start = 0
LEVEL_CODE_INTRO_CLOSE_MS = 250

startup_sequence = True
startup_start_time = 0
startup_closing = False
startup_closing_start = 0
startup_close_target = "demo"
STARTUP_CLOSE_MS = 250

demo_mode = False
demo_macro = []
demo_macro_index = 0
demo_next_step_time = 0
demo_closing = False
demo_closing_start = 0
DEMO_STEP_MS = 110
DEMO_AFTER_END_MS = 2500
demo_end_time = 0
startup_surfaces = {}
startup_names_shadow_surface = None
demo_badge_surface = None
original_bitmap_font = None
last_presented_canvas = None

game_complete_sequence = False
game_complete_start_time = 0
game_complete_snapshot = None
game_complete_closing = False
game_complete_closing_start = 0
game_complete_score_level = 0
GAME_COMPLETE_CLOSE_MS = 250
GAME_COMPLETE_WAIT_MS = 1000
GAME_COMPLETE_WIPE_MS = 250
GAME_COMPLETE_BLACK_MS = 1000
GAME_COMPLETE_SHOW_MS = 3850
GAME_COMPLETE_END_WIPE_MS = 250
topten_entries = []
# Introsekvensens tider från originalet, Ghidra FUN_1000_3066.
# Originalet väntar i BIOS-ticks via FUN_1000_2fd7().
# 1 tick ≈ 54.925 ms:
#   3DTOP.PIC        0x28 ticks ≈ 2197 ms
#   INTRO.PIC innan NAMES-crop 0x14 ticks ≈ 1099 ms
#   INTRO + NAMES    0x78 ticks ≈ 6591 ms
#   Hjälpsida 1      0xb4 ticks ≈ 9887 ms
#   Hjälpsida 2      0xb4 ticks ≈ 9887 ms
#   Tio-i-topp       0x50 ticks ≈ 4394 ms
STARTUP_TOP_MS = 2197
STARTUP_INTRO_ONLY_MS = 1099
STARTUP_INTRO_NAMES_MS = 6591
STARTUP_HELP_1_MS = 9887
STARTUP_HELP_2_MS = 9887
STARTUP_TOPTEN_MS = 4394

last_dir_name = "right"
player_moving = False
player_walk_phase = 0

tile_sprites = {}
animations = {}
animation_meta = {}
default_exit_sprite = None
blue_exit_sprite = None

explosion_effects = []
pending_explosions = []
scheduled_bombs = set()
reserved_bombs = set()
bomb_hit_queue = []
queued_bombs = set()
chain_next_trigger_time = 0
bomb_exploded_this_frame = False

# När en bomb träffas av en annan bombexplosion väntar den så här länge.
# 400 ms = 0,4 sekunder.
BOMB_HIT_DELAY_MS = 300

BOULDER_TILES = {"B"}
DIAMOND_TILES = {"D"}
BOMB_TILES = {"Z"}
ENEMY_TILES = {"M", "2", "3"}
KEY_TILES = {"$", "%", "^", "&"}
DOOR_TILES = {"!", "@", "#"}
DOOR_TO_KEY = {"!": "$", "@": "%", "#": "^"}

PUSHABLE_TILES = BOULDER_TILES | BOMB_TILES
MOVING_TILES = BOULDER_TILES | DIAMOND_TILES | BOMB_TILES
# Objekt ska rulla från bumling/diamant, men inte från bomb eller snö.
ROUNDED_TILES = BOULDER_TILES | DIAMOND_TILES | BOMB_TILES

# Källkodskollen i Ghidra-exporten visar att fallande objekt hanteras i
# FUN_1000_0eda: explosion/burst arbetar med 3 kolumner och 3 rader,
# från objektets nuvarande rad och två rader nedåt.
DIGGABLE_TILES = {"G", "O", "D"}
WALKABLE_TILES = {" ", "G", "O", "D", "E"}
PRESERVE_TILES = {"X", "E", "H"}
DEBUG_TILE_LETTERS = False

UP = (0, -1)
RIGHT = (1, 0)
DOWN = (0, 1)
LEFT = (-1, 0)

colors = {
    " ": (0, 0, 0),
    "X": (80, 80, 80),
    "G": (160, 80, 20),
    "W": (70, 70, 70),
    "B": (150, 150, 150),
    "D": (120, 255, 255),
    "Z": (120, 120, 120),
    "E": (0, 255, 0),
    "M": (0, 255, 0),
    "2": (255, 120, 0),
    "3": (255, 0, 255),
    "$": (255, 255, 255),
    "%": (255, 0, 0),
    "^": (0, 255, 0),
    "!": (255, 255, 255),
    "@": (255, 0, 0),
    "#": (0, 255, 0),
    "H": (120, 0, 255),
    "O": (200, 200, 0),
    "I": (0, 180, 120),
}


def set_message(text):
    global message
    message = text

    if text:
        print(text)


def parse_cli_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-D",
        "--debug",
        action="store_true",
        help="Aktivera debugknappar.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Starta spelbart demo-läge: intro -> demo/prövbana -> 1..8 -> 11 -> slutbild.",
    )
    parser.add_argument(
        "--sound",
        "--audio",
        choices=[SOUND_MODE_SOUNDBLASTER, SOUND_MODE_SPEAKER, SOUND_MODE_ORIGINAL],
        default=SOUND_MODE_ORIGINAL,
        help="Välj ljudläge: soundblaster, speaker eller original.",
    )
    parser.add_argument(
        "--music",
        default=MUSIC_FILE,
        help="Experimentellt: spela MUSIC.OUT skapat från MIDI om filen finns.",
    )
    parser.add_argument(
        "--music-mode",
        choices=[MUSIC_MODE_AUTO, MUSIC_MODE_SOUNDBLASTER, MUSIC_MODE_SPEAKER, MUSIC_MODE_C64],
        default=MUSIC_MODE_AUTO,
        help="Experimentellt musikläge: auto, soundblaster, speaker eller c64/arpeggio.",
    )
    parser.add_argument(
        "--music-volume",
        type=float,
        default=0.18,
        help="Musikvolym 0.0-1.0.",
    )
    parser.add_argument(
        "--music-on",
        action="store_true",
        help="Starta med experimentell musik aktiverad. Standard är av; F4 togglar i spelet.",
    )
    parser.add_argument(
        "--no-music",
        action="store_true",
        help="Tvinga av experimentell musik även om --music-on används.",
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Starta i fullscreen. F11 eller Alt+Enter växlar under körning.",
    )
    return parser.parse_args()


# Originalets ljud går via PC speaker:
#   FUN_1000_0b5b(sound_id)  = spelhändelse-ljud
#   FUN_1000_ac44(freq)      = skriv frekvens till PIT/PC speaker
#   FUN_1000_ac70()          = stäng av speaker
#   FUN_1000_a694(n)         = kort delay
#
# Här renderas samma sound-id-strukturer till pygame.mixer-samples.

def _append_silence(samples, ms):
    samples.extend([0] * int(AUDIO_RATE * ms / 1000))


def _append_square(samples, freq, ms, volume=0.35, end_freq=None, decay=0.0):
    if freq <= 18 or ms <= 0:
        _append_silence(samples, max(0, ms))
        return

    count = max(1, int(AUDIO_RATE * ms / 1000))
    phase = 0.0

    for i in range(count):
        t = i / max(1, count - 1)
        current_freq = freq if end_freq is None else freq + (end_freq - freq) * t
        phase = (phase + current_freq / AUDIO_RATE) % 1.0
        amp = volume * max(0.0, 1.0 - decay * t)
        value = 1.0 if phase < 0.5 else -1.0
        samples.append(int(32767 * amp * value * SOUND_MASTER_VOLUME))


def _append_pc_tone(samples, freq, delay_ms, volume=0.24):
    # FUN_1000_ac44 ignorerar frekvenser <= 0x12.
    if freq <= 18:
        _append_silence(samples, delay_ms)
    else:
        _append_square(samples, freq, delay_ms, volume)


def _append_pc_stop(samples, ms=1):
    # FUN_1000_ac70: avstängd speaker. I en sample blir det kort tystnad.
    _append_silence(samples, ms)


def _orig_rand16(state):
    # Exakt seed/generator är inte kritisk för ljudidentiteten här, eftersom
    # originalet bara använder slumpen som liten störning i frekvensen.
    state[0] = (state[0] * 0x4E6D + 0x3039) & 0xFFFF
    return state[0]


def _make_sound_from_samples(samples):
    if not samples:
        samples = array("h", [0])
    return pygame.mixer.Sound(buffer=samples.tobytes())


def _make_original_sound_id(sound_id, seed=0x1234):
    samples = array("h")
    rnd = [seed + sound_id * 0x1111]

    def r():
        return _orig_rand16(rnd)

    # ID 0: vanlig rörelse. Original: 5 mycket korta slumpade speaker-toner.
    if sound_id == 0:
        for i in range(0, 10, 2):
            _append_pc_tone(samples, r() % 200, 2, 0.16)
        _append_pc_stop(samples, 2)

    # ID 1: explosion/burst. Original: brusig serie med korta frekvenshopp.
    elif sound_id == 1:
        for base in range(0x32, 200, 10):
            for _ in range(5):
                freq = (r() % 2000) - base * 5
                _append_pc_tone(samples, freq, 2, 0.28)
                _append_pc_stop(samples, 1)
            _append_silence(samples, max(1, base // 0x14))

    # ID 2: dörr/level-start/exit. Original: stigande 50..ca 540 Hz.
    elif sound_id == 2:
        for base in range(0, 400, 10):
            freq = (r() % 100) + base + 0x32
            _append_pc_tone(samples, freq, 5, 0.24)

    # ID 3: diamant. Original: snabb stigande hög pitch utan delay.
    elif sound_id == 3:
        # Originalet skriver många frekvenser utan FUN_a694-delay.
        # Rendera som en kort kontinuerlig sweep.
        _append_square(samples, 2000, 95, 0.22, end_freq=8000, decay=0.25)
        _append_pc_stop(samples, 3)

    # ID 4: grävning/jord. Original: korta höga toner 2000..3000.
    elif sound_id == 4:
        for base in range(2000, 3000, 100):
            freq = (r() % 1000) + base
            _append_pc_tone(samples, freq, 3, 0.18)
            _append_pc_stop(samples, 1)

    # ID 5: landande sten/diamant/bomb. Original: fem korta slumpklick.
    elif sound_id == 5:
        for _ in range(1, 0x32, 10):
            _append_pc_tone(samples, r() % 2000, 2, 0.20)
            _append_pc_stop(samples, 1)

    # ID 6: alla diamanter/klart-signal. Original: snabb upp- och ned-sweep.
    elif sound_id == 6:
        _append_square(samples, 2000, 180, 0.22, end_freq=18000, decay=0.15)
        _append_square(samples, 18000, 180, 0.22, end_freq=2000, decay=0.15)
        _append_pc_stop(samples, 4)

    # ID 7: död. Original: fallande 8000..1000 Hz.
    elif sound_id == 7:
        _append_square(samples, 8000, 180, 0.26, end_freq=1000, decay=0.35)
        _append_pc_stop(samples, 5)

    else:
        _append_pc_stop(samples, 1)

    return _make_sound_from_samples(samples)


def _concat_sounds_as_original_ids(ids, pauses_ms=None):
    # Bygg sammansatta ljud där originalet spelar flera FUN_1000_0b5b-anrop.
    pauses_ms = pauses_ms or [0] * max(0, len(ids) - 1)
    samples = array("h")

    for i, sound_id in enumerate(ids):
        src = array("h")
        rnd = [0x1234 + sound_id * 0x1111 + i * 0x2222]

        def r():
            return _orig_rand16(rnd)

        # lokal rendering utan pygame.Sound mellan stegen
        if sound_id == 3:
            _append_square(src, 2000, 95, 0.22, end_freq=8000, decay=0.25)
            _append_pc_stop(src, 3)
        elif sound_id == 6:
            _append_square(src, 2000, 180, 0.22, end_freq=18000, decay=0.15)
            _append_square(src, 18000, 180, 0.22, end_freq=2000, decay=0.15)
            _append_pc_stop(src, 4)
        elif sound_id == 2:
            for base in range(0, 400, 10):
                _append_pc_tone(src, (r() % 100) + base + 0x32, 5, 0.24)
        else:
            # fallback: använd fristående ID och läs ut via samma generator är onödigt.
            # Lägg i stället kort tystnad om ett oväntat ID hamnar här.
            _append_pc_stop(src, 1)

        samples.extend(src)

        if i < len(ids) - 1:
            _append_silence(samples, pauses_ms[i])

    return _make_sound_from_samples(samples)



def _get_game_file_path(filename):
    # game_file_path är definierad längre ner men finns när init_sound körs.
    try:
        path = game_file_path(filename)
        if path:
            return path
    except NameError:
        pass

    for path in [
        Path(filename),
        Path(__file__).resolve().parent / filename,
    ]:
        if path.exists():
            return path

    return None


def _read_voc_pcm_u8(path):
    data = Path(path).read_bytes()

    if not data.startswith(b"Creative Voice File\x1a"):
        raise ValueError(f"Inte en Creative Voice File: {path}")

    header_size = int.from_bytes(data[20:22], "little")
    pos = header_size
    chunks = []
    sample_rate = None

    while pos < len(data):
        block_type = data[pos]
        pos += 1

        if block_type == 0:
            break

        if pos + 3 > len(data):
            break

        size = data[pos] | (data[pos + 1] << 8) | (data[pos + 2] << 16)
        pos += 3
        block = data[pos:pos + size]
        pos += size

        # Type 1 = 8-bit PCM block: time_constant, codec, raw bytes.
        if block_type == 1 and len(block) >= 2:
            time_constant = block[0]
            codec = block[1]

            if codec != 0:
                raise ValueError(f"Oväntad VOC-codec {codec} i {path}")

            sample_rate = round(1_000_000 / (256 - time_constant))
            chunks.append(block[2:])

        # Type 2 = continuation block.
        elif block_type == 2:
            chunks.append(block)

    if sample_rate is None:
        raise ValueError(f"Hittade ingen PCM-data i {path}")

    return b"".join(chunks), sample_rate


def _pcm_u8_to_s16_samples(raw, in_rate, volume=1.0):
    # Originalfilerna är 8-bit unsigned PCM. Konvertera till mixerformatet s16.
    if not raw:
        return array("h", [0])

    if in_rate == AUDIO_RATE:
        samples = array("h")
        for b in raw:
            samples.append(int((b - 128) * 256 * volume))
        return samples

    out_len = max(1, int(round(len(raw) * AUDIO_RATE / in_rate)))
    samples = array("h")

    for i in range(out_len):
        src_pos = i * in_rate / AUDIO_RATE
        src_i = min(len(raw) - 1, int(src_pos))
        samples.append(int((raw[src_i] - 128) * 256 * volume))

    return samples


def _sound_from_samples(samples):
    if not samples:
        samples = array("h", [0])
    return pygame.mixer.Sound(buffer=samples.tobytes())


def _load_voc_out_samples(filename, volume=1.0):
    path = _get_game_file_path(filename)

    if not path:
        print(f"Saknar originalljudfil: {filename}")
        return None

    try:
        raw, in_rate = _read_voc_pcm_u8(path)
        samples = _pcm_u8_to_s16_samples(raw, in_rate, volume)
        print(f"Laddade originalljud: {filename} ({in_rate} Hz)")
        return samples
    except Exception as exc:
        print(f"Kunde inte läsa {filename}: {exc}")
        return None


def _load_voc_out_sound(filename, volume=1.0):
    samples = _load_voc_out_samples(filename, volume)

    if samples is None:
        return None

    return _sound_from_samples(samples)


def _concat_sample_sounds(*sample_arrays, pause_ms=0):
    out = array("h")
    pause = array("h", [0] * int(AUDIO_RATE * pause_ms / 1000))

    for i, samples in enumerate(sample_arrays):
        if samples:
            out.extend(samples)
        if pause_ms and i != len(sample_arrays) - 1:
            out.extend(pause)

    return _sound_from_samples(out)



def _load_wav_sound_from_path(path):
    try:
        return pygame.mixer.Sound(str(path))
    except Exception as exc:
        print(f"Kunde inte läsa ljud {path}: {exc}")
        return None


def _load_wav_sound_from_zip(zip_path, filename):
    try:
        with zipfile.ZipFile(zip_path) as z:
            # Stöd både root och recorded_sounds/-mapp i zippen.
            wanted = filename.lower()
            candidates = [
                name for name in z.namelist()
                if Path(name).name.lower() == wanted
            ]

            if not candidates:
                return None

            data = z.read(candidates[0])
            return pygame.mixer.Sound(file=io.BytesIO(data))
    except Exception as exc:
        print(f"Kunde inte läsa {filename} från {zip_path}: {exc}")
        return None



recorded_out_cache = None

IMA_INDEX_TABLE = [-1, -1, -1, -1, 2, 4, 6, 8,
                   -1, -1, -1, -1, 2, 4, 6, 8]

IMA_STEP_TABLE = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17,
    19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
    50, 55, 60, 66, 73, 80, 88, 97, 107, 118,
    130, 143, 157, 173, 190, 209, 230, 253, 279, 307,
    337, 371, 408, 449, 494, 544, 598, 658, 724, 796,
    876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
    2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358,
    5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899,
    15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
]


def _decode_ima_adpcm(initial_predictor, initial_index, adpcm_data, sample_count):
    predictor = int(initial_predictor)
    index = max(0, min(88, int(initial_index)))
    samples = array("h", [max(-32768, min(32767, predictor))])

    for byte in adpcm_data:
        for code in (byte & 0x0f, (byte >> 4) & 0x0f):
            if len(samples) >= sample_count:
                return samples

            step = IMA_STEP_TABLE[index]
            delta = step >> 3
            if code & 4:
                delta += step
            if code & 2:
                delta += step >> 1
            if code & 1:
                delta += step >> 2

            if code & 8:
                predictor -= delta
            else:
                predictor += delta

            predictor = max(-32768, min(32767, predictor))
            index += IMA_INDEX_TABLE[code]
            index = max(0, min(88, index))
            samples.append(predictor)

    while len(samples) < sample_count:
        samples.append(predictor)

    return samples


def _resample_s16_samples(samples, in_rate):
    if in_rate == AUDIO_RATE:
        return samples

    if not samples:
        return array("h", [0])

    out_len = max(1, int(round(len(samples) * AUDIO_RATE / in_rate)))
    out = array("h")

    for i in range(out_len):
        src_pos = i * in_rate / AUDIO_RATE
        src_i = min(len(samples) - 1, int(src_pos))
        out.append(samples[src_i])

    return out


def _read_recorded_out_file(path):
    data = Path(path).read_bytes()

    old_magic = b"BOBRECOUT1"
    adpcm_magic = b"BOBADPCM1\0"

    if data.startswith(old_magic):
        header_len_pos = len(old_magic)
        header_len = int.from_bytes(data[header_len_pos:header_len_pos + 4], "little")
        header_start = header_len_pos + 4
        header_end = header_start + header_len
        header = json.loads(data[header_start:header_end].decode("utf-8"))

        if header.get("format") != "bomber_recorded_out_v1":
            raise ValueError(f"Okänt original.out-format: {header.get('format')}")

        return {
            "format": "pcm16",
            "path": Path(path),
            "header": header,
            "payload": data[header_end:],
        }

    if data.startswith(adpcm_magic):
        pos = len(adpcm_magic)
        if pos + 2 > len(data):
            raise ValueError("Trasig ADPCM-original.out: saknar ljudantal")

        sound_count = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        sounds = {}

        for _ in range(sound_count):
            name_len = data[pos]
            pos += 1
            name = data[pos:pos + name_len].decode("ascii")
            pos += name_len

            sample_rate, sample_count, predictor, index, comp_len = struct.unpack_from("<IIhBI", data, pos)
            pos += struct.calcsize("<IIhBI")

            comp = data[pos:pos + comp_len]
            pos += comp_len

            sounds[name] = {
                "sample_rate": int(sample_rate),
                "sample_count": int(sample_count),
                "predictor": int(predictor),
                "index": int(index),
                "compressed": comp,
            }

        return {
            "format": "ima_adpcm_zlib",
            "path": Path(path),
            "sounds": sounds,
            "decoded": {},
        }

    raise ValueError(f"Fel original.out-format: {path}")


def _get_recorded_out():
    global recorded_out_cache

    if recorded_out_cache is not None:
        return recorded_out_cache

    candidates = []

    try:
        candidates.extend([
            game_file_path("original.out"),
            game_file_path("ORIGINAL.OUT"),
            game_file_path("BOB_SOUNDS_ADPCM.OUT"),
        ])
    except NameError:
        pass

    candidates.extend([
        Path("original.out"),
        Path("ORIGINAL.OUT"),
        Path("BOB_SOUNDS_ADPCM.OUT"),
    ])

    seen = set()
    unique_candidates = []
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique_candidates.append(path)

    for path in unique_candidates:
        if path.exists():
            try:
                recorded_out_cache = _read_recorded_out_file(path)
                print(f"Laddade original-ljud från {path} ({recorded_out_cache['format']})")
                return recorded_out_cache
            except Exception as exc:
                print(f"Kunde inte läsa {path}: {exc}")

    recorded_out_cache = False
    return None


def _load_recorded_out_sound(sound_name):
    rec = _get_recorded_out()

    if not rec:
        return None

    if rec.get("format") == "pcm16":
        sounds = rec["header"].get("sounds", {})
        meta = sounds.get(sound_name)

        if not meta:
            return None

        offset = int(meta["offset"])
        length = int(meta["length"])
        chunk = rec["payload"][offset:offset + length]

        if not chunk:
            return None

        return pygame.mixer.Sound(buffer=chunk)

    if rec.get("format") == "ima_adpcm_zlib":
        meta = rec["sounds"].get(sound_name)

        if not meta:
            return None

        decoded_cache = rec.setdefault("decoded", {})
        if sound_name not in decoded_cache:
            adpcm = zlib.decompress(meta["compressed"])
            samples = _decode_ima_adpcm(
                meta["predictor"],
                meta["index"],
                adpcm,
                meta["sample_count"],
            )
            samples = _resample_s16_samples(samples, meta["sample_rate"])
            decoded_cache[sound_name] = samples.tobytes()

        return pygame.mixer.Sound(buffer=decoded_cache[sound_name])

    return None



def _load_recorded_sound(filename):
    # Prioritet:
    #   1. original.out / original.out
    #   2. recorded_sounds/<fil>
    #   3. <fil> i spelmappen
    #   4. recorded_sounds.zip
    #   5. capture.zip
    sound_name = Path(filename).stem
    out_sound = _load_recorded_out_sound(sound_name)

    if out_sound:
        return out_sound

    base_paths = []

    try:
        base_paths.append(game_file_path("recorded_sounds") / filename)
        base_paths.append(game_file_path(filename))
        base_paths.append(game_file_path("recorded_sounds.zip"))
        base_paths.append(game_file_path("capture.zip"))
    except NameError:
        pass

    base_paths.extend([
        Path("recorded_sounds") / filename,
        Path(filename),
        Path("recorded_sounds.zip"),
        Path("capture.zip"),
    ])

    for path in base_paths:
        if path.suffix.lower() == ".zip":
            if path.exists():
                sound = _load_wav_sound_from_zip(path, filename)
                if sound:
                    return sound
        else:
            if path.exists():
                sound = _load_wav_sound_from_path(path)
                if sound:
                    return sound

    print(f"Saknar inspelat ljud: {filename}")
    return None


def _first_sound(*names):
    for name in names:
        sound = _load_recorded_sound(name)
        if sound:
            return sound
    return None


def _first_sound_pair(a, b):
    sound_a = _load_recorded_sound(a)
    sound_b = _load_recorded_sound(b)

    if sound_a and sound_b:
        return [sound_a, sound_b]

    if sound_a:
        return sound_a

    if sound_b:
        return sound_b

    return None


def init_recorded_mode():
    global sound_available, sound_cache, sound_cycle_index, recorded_out_cache

    sound_available = False
    sound_cache = {}
    sound_cycle_index = {}
    recorded_out_cache = None

    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=AUDIO_RATE, size=-16, channels=1, buffer=256)

        walk_pair = _first_sound_pair("walk1.wav", "walk2.wav")
        dig_sound = _first_sound("dig.wav")
        diamond_sound = _first_sound("diamond.wav")
        diamond_complete_sound = _first_sound("diamond_complete.wav", "diamond.wav")
        fall_sound = _first_sound("fall.wav")
        explode_sound = _first_sound("explode.wav")
        level_sound = _first_sound("level.wav")
        dead_sound = _first_sound("dead.wav", "death.wav")

        # Fallbackkedja om någon fil saknas.
        if walk_pair is None:
            walk_pair = dig_sound or fall_sound
        if dig_sound is None:
            dig_sound = walk_pair
        if diamond_sound is None:
            diamond_sound = explode_sound
        if diamond_complete_sound is None:
            diamond_complete_sound = diamond_sound
        if fall_sound is None:
            fall_sound = walk_pair
        if explode_sound is None:
            explode_sound = fall_sound
        if level_sound is None:
            level_sound = diamond_complete_sound or diamond_sound
        if dead_sound is None:
            dead_sound = explode_sound

        sound_cache = {
            # Vanlig rörelse växlar mellan walk1/walk2.
            "walk": walk_pair,
            "walk_into_dirt": walk_pair,
            "push": walk_pair,
            "key": walk_pair,
            "door": walk_pair,

            # SHIFT + riktning mot jord.
            "dig": dig_sound,

            "diamond": diamond_sound,
            "diamond_complete": diamond_complete_sound,

            # Fallande sten/diamant/bomb landar.
            "land": fall_sound,

            # Bomb.
            "explode": explode_sound,

            # Fiendeljud mappas dynamiskt i monster_burst_at:
            # M -> diamond.wav, 2 -> fall.wav.
            "enemy_diamond": diamond_sound,
            "enemy_stone": fall_sound,
            "enemy": explode_sound,

            # Både banstart och exit.
            "level_start": level_sound,
            "exit": level_sound,
            "complete": level_sound,

            "death": dead_sound,

            # F2 har inget ljud.
            "toggle": None,
        }

        sound_available = True
        print("Ljudläge: Original")
    except Exception as exc:
        sound_available = False
        sound_cache = {}
        print(f"Ljud avstängt: {exc}")



def init_soundblaster_mode():
    global sound_available, sound_cache

    sound_available = False
    sound_cache = {}

    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=AUDIO_RATE, size=-16, channels=1, buffer=256)

        # Originalets SoundBlaster-läge laddar dessa Creative Voice-filer:
        #
        #   cnarring.out -> sound ID 2
        #   step.out     -> laddas av originalet; används här för gång/grävning
        #   munch.out    -> sound ID 3
        #   davevoc.out  -> sound ID 6
        #   burpa.out    -> laddas av originalet men anropas inte via FUN_1000_0b5b
        #   pock.out     -> sound ID 5
        #   starsnar.out -> sound ID 1 och ID 7
        #
        # Filerna är VOC/Creative Voice File med 8-bit unsigned PCM.
        step_samples = _load_voc_out_samples("STEP.OUT", 1.0)
        cnarring_samples = _load_voc_out_samples("CNARRING.OUT", 1.0)
        munch_samples = _load_voc_out_samples("MUNCH.OUT", 1.0)
        davevoc_samples = _load_voc_out_samples("DAVEVOC.OUT", 1.0)
        pock_samples = _load_voc_out_samples("POCK.OUT", 1.0)
        starsnar_samples = _load_voc_out_samples("STARSNAR.OUT", 1.0)
        burpa_samples = _load_voc_out_samples("BURPA.OUT", 1.0)

        original_id = {
            0: _make_original_sound_id(0),  # PC-speaker fallback
            1: _sound_from_samples(starsnar_samples) if starsnar_samples else _make_original_sound_id(1),
            2: _sound_from_samples(cnarring_samples) if cnarring_samples else _make_original_sound_id(2),
            3: _sound_from_samples(munch_samples) if munch_samples else _make_original_sound_id(3),
            4: _make_original_sound_id(4),  # originalet har PC-speaker-gren här
            5: _sound_from_samples(pock_samples) if pock_samples else _make_original_sound_id(5),
            6: _sound_from_samples(davevoc_samples) if davevoc_samples else _make_original_sound_id(6),
            7: _sound_from_samples(starsnar_samples) if starsnar_samples else _make_original_sound_id(7),
        }

        step_sound = _sound_from_samples(step_samples) if step_samples else original_id[0]

        if munch_samples and davevoc_samples:
            diamond_complete_sound = _concat_sample_sounds(munch_samples, davevoc_samples, pause_ms=30)
        else:
            diamond_complete_sound = _concat_sounds_as_original_ids([3, 6], [30])

        sound_cache = {
            # Enligt önskemål: gång och grävning låter lika.
            # STEP.OUT är originalets inlästa steg-sample.
            "walk": step_sound,
            "walk_into_dirt": step_sound,
            "dig": step_sound,
            "push": step_sound,
            "key": step_sound,
            "door": step_sound,

            "diamond": original_id[3],
            "diamond_complete": diamond_complete_sound,

            "land": original_id[5],
            "explode": original_id[1],
            "enemy": original_id[1],

            "level_start": original_id[2],
            "exit": original_id[2],
            "complete": original_id[2],

            "death": original_id[7],

            # Originalets F2-toggle ger inget eget ljud.
            "toggle": None,

            # BURPA.OUT finns med i originalet men har ingen tydlig FUN_1000_0b5b-mappning.
            # Spara den ändå om vi senare hittar exakt anrop.
            "_burpa_unused_original": _sound_from_samples(burpa_samples) if burpa_samples else None,
        }

        sound_available = True
        print("Ljudläge: SoundBlaster (.OUT/VOC)")
    except Exception as exc:
        sound_available = False
        sound_cache = {}
        print(f"Ljud avstängt: {exc}")

def init_speaker_mode():
    global sound_available, sound_cache

    sound_available = False
    sound_cache = {}

    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=AUDIO_RATE, size=-16, channels=1, buffer=256)

        original_id = {
            0: _make_original_sound_id(0),
            1: _make_original_sound_id(1),
            2: _make_original_sound_id(2),
            3: _make_original_sound_id(3),
            4: _make_original_sound_id(4),
            5: _make_original_sound_id(5),
            6: _make_original_sound_id(6),
            7: _make_original_sound_id(7),
        }

        sound_cache = {
            # Enligt önskemål: gång och grävning ska låta lika.
            "walk": original_id[0],
            "walk_into_dirt": original_id[0],
            "dig": original_id[0],
            "push": original_id[0],
            "key": original_id[0],
            "door": original_id[0],

            "diamond": original_id[3],
            "diamond_complete": _concat_sounds_as_original_ids([3, 6], [30]),

            "land": original_id[5],
            "explode": original_id[1],
            "enemy": original_id[1],

            "level_start": original_id[2],
            "exit": original_id[2],
            "complete": original_id[2],

            "death": original_id[7],
            "toggle": None,
        }

        sound_available = True
        print("Ljudläge: Internal speaker")
    except Exception as exc:
        sound_available = False
        sound_cache = {}
        print(f"Ljud avstängt: {exc}")


def init_sound():
    if sound_mode == SOUND_MODE_ORIGINAL:
        init_recorded_mode()
    elif sound_mode == SOUND_MODE_SPEAKER:
        init_speaker_mode()
    else:
        init_soundblaster_mode()

    # Musik renderas om när ljudläge byts, eftersom auto-läget följer F3-ljudläget.
    init_music()


def cycle_sound_mode():
    global sound_mode

    modes = [SOUND_MODE_SOUNDBLASTER, SOUND_MODE_SPEAKER, SOUND_MODE_ORIGINAL]
    sound_mode = modes[(modes.index(sound_mode) + 1) % len(modes)]

    init_sound()
    set_message(f"Ljudläge: {sound_mode}")




def _music_note_freq(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def _music_mixer_rate():
    init = pygame.mixer.get_init()
    if init:
        return int(init[0])
    return AUDIO_RATE


def _load_music_out(path):
    path = Path(path)
    if not path.exists():
        return None

    blob = path.read_bytes()
    single_magic = b"BOBMUSIC1\0"
    pack_magic = b"BOBMUSPK1\0"

    if blob.startswith(single_magic):
        pos = len(single_magic)
        comp_len = struct.unpack_from("<I", blob, pos)[0]
        pos += 4
        payload = zlib.decompress(blob[pos:pos + comp_len])
        music = json.loads(payload.decode("utf-8"))
        music.setdefault("type", "song")
        return music

    if blob.startswith(pack_magic):
        pos = len(pack_magic)
        comp_len = struct.unpack_from("<I", blob, pos)[0]
        pos += 4
        payload = zlib.decompress(blob[pos:pos + comp_len])
        pack = json.loads(payload.decode("utf-8"))
        pack.setdefault("type", "pack")
        return pack

    raise ValueError("MUSIC.OUT har fel format/magic. Kör midi_to_bob_music.py eller bob_music_gui.py igen.")


def _music_pack_level_number():
    try:
        return int(visible_level_number())
    except Exception:
        return int(level_index)


def _select_music_song(music_data):
    if not music_data:
        return None, None

    if music_data.get("type") != "pack":
        return music_data, "single"

    songs = music_data.get("songs") or []
    if not songs:
        return None, None

    level_no = _music_pack_level_number()
    level_map = music_data.get("level_map") or {}
    slot = level_map.get(str(level_no), level_map.get(level_no))

    if slot is None:
        # Standard: bana 1 -> slot 0, bana 2 -> slot 1 ...
        # Efter sista låtslotten börjar den om: bana 11 -> slot 0 när 10 låtar finns.
        slot = (max(1, level_no) - 1) % len(songs)

    try:
        slot = int(slot)
    except Exception:
        slot = 0

    if slot < 0 or slot >= len(songs):
        return None, None

    song = songs[slot]
    if not song:
        return None, None

    song.setdefault("type", "song")
    return song, f"pack:{slot}:level:{level_no}"


def _music_make_sound(samples):
    if not samples:
        samples = array("h", [0])

    # pygame.mixer.Sound(buffer=...) tolkar råbuffer enligt aktuell mixer-init:
    # frequency, format och ANTAL KANALER. Om mixern råkar vara stereo men
    # buffern är mono blir ljudet hälften så långt och spelas därför upp som
    # ungefär dubbel hastighet. Detta hände på vissa system trots pre_init(..., channels=1).
    init = pygame.mixer.get_init()
    channels = 1
    if init and len(init) >= 3:
        try:
            channels = max(1, int(init[2]))
        except Exception:
            channels = 1

    if channels <= 1:
        return pygame.mixer.Sound(buffer=samples.tobytes())

    interleaved = array("h")
    for value in samples:
        for _ in range(channels):
            interleaved.append(value)

    return pygame.mixer.Sound(buffer=interleaved.tobytes())


def _render_music_soundblaster_samples(music, rate):
    # Enkel polyfon "sampled synth". Detta är inte original-SB-MIDI, utan en
    # liten testmotor för att kunna höra MIDI som musik i porten.
    duration_ms = int(music.get("duration_ms", 0)) + 250
    total = max(1, int(rate * duration_ms / 1000))
    acc = array("i", [0]) * total
    notes = music.get("notes", [])

    if not notes:
        return array("h", [0])

    # Sänk per-note-volym när låten är tät, så mixen inte klipper för lätt.
    base_amp = 5200

    for note in notes:
        start_ms, end_ms, pitch, velocity = note[:4]
        start = max(0, int(float(start_ms) * rate / 1000))
        end = min(total, int(float(end_ms) * rate / 1000))
        if end <= start:
            continue

        freq = _music_note_freq(int(pitch))
        amp = int(base_amp * max(0.0, min(1.0, int(velocity) / 127.0)))
        phase = 0.0
        step = freq / rate
        length = end - start
        attack = max(1, int(rate * 0.006))
        release = max(1, int(rate * 0.025))

        for i in range(length):
            # Lite rundare än ren square: square + svag triangle.
            phase = (phase + step) % 1.0
            sq = 1.0 if phase < 0.5 else -1.0
            tri = 4.0 * abs(phase - 0.5) - 1.0
            env = 1.0
            if i < attack:
                env *= i / attack
            if length - i < release:
                env *= max(0.0, (length - i) / release)
            value = int(amp * env * (0.80 * sq + 0.20 * tri))
            acc[start + i] += value

    out = array("h")
    for v in acc:
        v = max(-32768, min(32767, int(v)))
        out.append(v)

    return out


def _render_music_speaker_samples(music, rate, c64_mode=False):
    # En riktig PC speaker har i praktiken en ton åt gången. c64_mode här är
    # inte SID-emulering, utan snabb arpeggio/time-slicing så ackord blir mer
    # musikaliska på en enkanalig speaker.
    duration_ms = int(music.get("duration_ms", 0)) + 250
    total = max(1, int(rate * duration_ms / 1000))
    notes = music.get("notes", [])

    events = []
    for note in notes:
        start_ms, end_ms, pitch, velocity = note[:4]
        start = max(0, int(float(start_ms) * rate / 1000))
        end = min(total, int(float(end_ms) * rate / 1000))
        if end <= start:
            continue
        events.append((start, 1, int(pitch), int(velocity)))
        events.append((end, -1, int(pitch), int(velocity)))

    events.sort(key=lambda e: (e[0], -e[1]))
    out = array("h")
    active = []
    event_i = 0
    phase = 0.0
    arp_samples = max(1, int(rate * (0.018 if c64_mode else 0.050)))
    last_note = None

    for sample_i in range(total):
        while event_i < len(events) and events[event_i][0] <= sample_i:
            _, typ, pitch, velocity = events[event_i]
            if typ > 0:
                active.append((pitch, velocity))
            else:
                try:
                    active.remove((pitch, velocity))
                except ValueError:
                    # Om velocity skiljer sig, ta bort första med samma pitch.
                    for idx, item in enumerate(active):
                        if item[0] == pitch:
                            del active[idx]
                            break
            event_i += 1

        if not active:
            out.append(0)
            continue

        ordered = sorted(active, key=lambda n: n[0])
        if c64_mode and len(ordered) > 1:
            idx = (sample_i // arp_samples) % len(ordered)
            pitch, velocity = ordered[idx]
        else:
            pitch, velocity = ordered[-1]

        # Resetta fas lite när vald ton byts. Det låter mer som snabb portstyrning.
        if pitch != last_note:
            phase = 0.0
            last_note = pitch

        freq = _music_note_freq(pitch)
        phase = (phase + freq / rate) % 1.0
        amp = int(7200 * max(0.25, min(1.0, velocity / 127.0)))
        out.append(amp if phase < 0.5 else -amp)

    return out


def _resolve_music_mode():
    if music_mode != MUSIC_MODE_AUTO:
        return music_mode

    if sound_mode == SOUND_MODE_SPEAKER:
        return MUSIC_MODE_SPEAKER

    return MUSIC_MODE_SOUNDBLASTER


def _split_music_loop(samples, music, rate):
    duration_ms = int(music.get("duration_ms", 0)) + 250
    loop_start_ms = music.get("loop_start_ms", None)
    loop_end_ms = music.get("loop_end_ms", duration_ms)

    if loop_start_ms is None:
        return None, samples, 0

    try:
        loop_start_ms = max(0.0, float(loop_start_ms))
        loop_end_ms = max(loop_start_ms + 1.0, float(loop_end_ms))
    except Exception:
        return None, samples, 0

    start = max(0, min(len(samples), int(loop_start_ms * rate / 1000)))
    end = max(start + 1, min(len(samples), int(loop_end_ms * rate / 1000)))

    intro = samples[:start] if start > 0 else None
    loop = samples[start:end]
    intro_ms = int(start * 1000 / rate) if intro else 0
    return intro, loop, intro_ms


def _start_music_from_song(song, key):
    global music_available, music_channel, music_sound, music_intro_sound, music_loop_sound
    global music_loop_started, music_loop_switch_at, music_runtime_mode, music_current_key

    music_available = False
    music_sound = None
    music_intro_sound = None
    music_loop_sound = None
    music_loop_started = False
    music_loop_switch_at = 0
    music_current_key = None

    if not song:
        if music_channel:
            music_channel.stop()
        return

    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=AUDIO_RATE, size=-16, channels=1, buffer=256)

    pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
    music_channel = pygame.mixer.Channel(7)
    music_channel.stop()

    rate = _music_mixer_rate()
    resolved = _resolve_music_mode()
    if resolved == MUSIC_MODE_SPEAKER:
        samples = _render_music_speaker_samples(song, rate, c64_mode=False)
    elif resolved == MUSIC_MODE_C64:
        samples = _render_music_speaker_samples(song, rate, c64_mode=True)
    else:
        samples = _render_music_soundblaster_samples(song, rate)

    intro, loop, intro_ms = _split_music_loop(samples, song, rate)
    music_loop_sound = _music_make_sound(loop)
    music_sound = music_loop_sound
    music_runtime_mode = resolved
    music_current_key = key
    music_channel.set_volume(max(0.0, min(1.0, music_volume)))

    if intro:
        music_intro_sound = _music_make_sound(intro)
        music_channel.play(music_intro_sound)
        music_loop_switch_at = pygame.time.get_ticks() + intro_ms
        music_loop_started = False
    else:
        music_channel.play(music_loop_sound, loops=-1)
        music_loop_started = True

    music_available = True
    title = song.get("title") or key or "MUSIC.OUT"
    print(f"Musik: {music_file} / {title} ({resolved}, {rate} Hz)")


def music_playback_allowed():
    # Musiken ska bara höras inne på en spelbar bana. Titelintro, demo, topplista,
    # highscore, level-kod/"Gör dig beredd" och slutbild ska vara tysta.
    blocked_names = (
        "startup_sequence",
        "demo_mode",
        "topten_screen",
        "highscore_entry",
        "game_complete_sequence",
        "level_code_intro",
        "level_intro",
        "code_mode",
    )

    for name in blocked_names:
        if bool(globals().get(name, False)):
            return False

    return True


def stop_music_playback():
    global music_available, music_current_key, music_sound, music_intro_sound, music_loop_sound
    global music_loop_started, music_loop_switch_at, music_runtime_mode, music_duck_until

    if music_channel:
        music_channel.stop()

    music_available = False
    music_current_key = None
    music_sound = None
    music_intro_sound = None
    music_loop_sound = None
    music_loop_started = False
    music_loop_switch_at = 0
    music_runtime_mode = None
    music_duck_until = 0


def init_music():
    global music_available, music_current_key, music_sound, music_intro_sound, music_loop_sound, music_runtime_mode

    music_available = False
    music_sound = None
    music_intro_sound = None
    music_loop_sound = None
    music_runtime_mode = None

    if not music_enabled or not music_playback_allowed():
        stop_music_playback()
        return

    try:
        music_data = _load_music_out(music_file)
        if not music_data:
            if music_channel:
                music_channel.stop()
            return

        song, key = _select_music_song(music_data)
        _start_music_from_song(song, key)
    except Exception as exc:
        stop_music_playback()
        print(f"Musik avstängd: {exc}")


def restart_music_for_level():
    if music_enabled and music_playback_allowed():
        init_music()
    else:
        stop_music_playback()


def toggle_music():
    global music_enabled

    music_enabled = not music_enabled

    if not music_enabled:
        stop_music_playback()
        set_message("Musik: av")
    else:
        if music_playback_allowed():
            init_music()
            set_message("Musik: på" if music_available else "Musik: ingen MUSIC.OUT")
        else:
            stop_music_playback()
            set_message("Musik: på (startar på bana)")


def _duck_music_for_sfx(now):
    global music_duck_until

    if not music_available or not music_channel:
        return

    # Autentiskt PC-speaker-läge: effekter stjäl speakern kort.
    if music_runtime_mode in (MUSIC_MODE_SPEAKER, MUSIC_MODE_C64):
        music_duck_until = max(music_duck_until, now + 120)
        music_channel.set_volume(0.0)


def update_music(now):
    global music_duck_until, music_loop_started

    if music_available and not music_playback_allowed():
        stop_music_playback()
        return

    if not music_available or not music_channel:
        return

    if music_duck_until and now >= music_duck_until:
        music_duck_until = 0
        music_channel.set_volume(max(0.0, min(1.0, music_volume)))

    if music_loop_sound and not music_loop_started and music_loop_switch_at and now >= music_loop_switch_at:
        music_channel.play(music_loop_sound, loops=-1)
        music_loop_started = True

def play_game_sound(name, min_interval_ms=35, force=False):
    if not sound_enabled or not sound_available:
        return

    sound = sound_cache.get(name)

    if sound is None:
        return

    now = pygame.time.get_ticks()
    last = last_sound_time.get(name, -100000)

    if not force and now - last < min_interval_ms:
        return

    last_sound_time[name] = now
    _duck_music_for_sfx(now)

    try:
        if isinstance(sound, (list, tuple)):
            if not sound:
                return

            idx = sound_cycle_index.get(name, 0) % len(sound)
            sound_cycle_index[name] = idx + 1
            sound[idx].play()
        else:
            sound.play()
    except Exception:
        pass


def clear_held_direction():
    global held_dx, held_dy, held_source, player_moving
    held_dx = 0
    held_dy = 0
    held_source = None
    player_moving = False


def set_held_direction(dx, dy, now, repeat_delay=MOVE_REPEAT_DELAY, source="keyboard"):
    global held_dx, held_dy, held_source, next_move_time

    held_dx = dx
    held_dy = dy
    held_source = source
    next_move_time = now + repeat_delay


def update_held_direction_from_keyboard(now):
    pressed = pygame.key.get_pressed()

    if pressed[pygame.K_LEFT]:
        set_held_direction(-1, 0, now, MOVE_REPEAT_MS)
    elif pressed[pygame.K_RIGHT]:
        set_held_direction(1, 0, now, MOVE_REPEAT_MS)
    elif pressed[pygame.K_UP]:
        set_held_direction(0, -1, now, MOVE_REPEAT_MS)
    elif pressed[pygame.K_DOWN]:
        set_held_direction(0, 1, now, MOVE_REPEAT_MS)
    else:
        clear_held_direction()


def dir_name_from_delta(dx, dy):
    if dx < 0:
        return "left"
    if dx > 0:
        return "right"
    if dy < 0:
        return "up"
    if dy > 0:
        return "down"

    return last_dir_name



def joystick_config_path():
    try:
        return game_file_path(joystick_config_file)
    except NameError:
        return Path(__file__).resolve().parent / joystick_config_file


def load_joystick_config():
    global joystick_dig_buttons, joystick_axis_centers, joystick_deadzone

    path = joystick_config_path()

    if not path.exists():
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        buttons = data.get("dig_buttons")

        if isinstance(buttons, list) and buttons:
            joystick_dig_buttons = {int(button) for button in buttons}

        centers = data.get("axis_centers", {})

        if isinstance(centers, dict):
            joystick_axis_centers = {
                str(instance_id): {int(axis): float(value) for axis, value in axes.items()}
                for instance_id, axes in centers.items()
                if isinstance(axes, dict)
            }

        deadzone = data.get("deadzone")

        if deadzone is not None:
            joystick_deadzone = max(0.05, min(0.90, float(deadzone)))
    except Exception as exc:
        print(f"Kunde inte läsa joystick.json: {exc}")


def save_joystick_config():
    path = joystick_config_path()

    try:
        data = {
            "dig_buttons": sorted(joystick_dig_buttons),
            "axis_centers": joystick_axis_centers,
            "deadzone": joystick_deadzone,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Sparade joystick-inställningar: {path}")
    except Exception as exc:
        print(f"Kunde inte spara joystick.json: {exc}")


def init_joysticks():
    global joysticks

    joysticks = {}

    try:
        pygame.joystick.init()
        load_joystick_config()

        for index in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(index)
            joystick.init()
            joysticks[joystick.get_instance_id()] = joystick
            print(f"Joystick hittad: {joystick.get_name()}")

        if joysticks:
            set_message(f"Joystick: {len(joysticks)} hittad")
    except Exception as exc:
        print(f"Joystick avstängd: {exc}")
        joysticks = {}


def add_joystick_device(device_index):
    try:
        joystick = pygame.joystick.Joystick(device_index)
        joystick.init()
        joysticks[joystick.get_instance_id()] = joystick
        set_message(f"Joystick: {joystick.get_name()}")
        print(f"Joystick ansluten: {joystick.get_name()}")
    except Exception as exc:
        print(f"Kunde inte initiera joystick: {exc}")


def remove_joystick_device(instance_id):
    if instance_id in joysticks:
        try:
            name = joysticks[instance_id].get_name()
        except Exception:
            name = "okänd"
        joysticks.pop(instance_id, None)
        set_message("Joystick bortkopplad")
        print(f"Joystick bortkopplad: {name}")


def joystick_axis_value(joystick, axis):
    try:
        raw = float(joystick.get_axis(axis))
    except Exception:
        return 0.0

    centers = joystick_axis_centers.get(str(joystick.get_instance_id()), {})
    center = float(centers.get(axis, 0.0))

    return max(-1.0, min(1.0, raw - center))


def joystick_direction():
    # D-pad/hat prioriteras över analog spak.
    for joystick in list(joysticks.values()):
        try:
            for hat_index in range(joystick.get_numhats()):
                hx, hy = joystick.get_hat(hat_index)

                if hx < 0:
                    return (-1, 0)
                if hx > 0:
                    return (1, 0)
                if hy > 0:
                    return (0, -1)
                if hy < 0:
                    return (0, 1)
        except Exception:
            continue

    # Analog vänsterspak. Kardinalriktning väljs efter starkaste axeln.
    for joystick in list(joysticks.values()):
        try:
            if joystick.get_numaxes() < 2:
                continue

            x = joystick_axis_value(joystick, 0)
            y = joystick_axis_value(joystick, 1)

            if abs(x) < joystick_deadzone and abs(y) < joystick_deadzone:
                continue

            if abs(x) >= abs(y):
                return (-1, 0) if x < 0 else (1, 0)

            return (0, -1) if y < 0 else (0, 1)
        except Exception:
            continue

    return (0, 0)


def joystick_dig_pressed():
    for joystick in list(joysticks.values()):
        try:
            for button in joystick_dig_buttons:
                if 0 <= button < joystick.get_numbuttons() and joystick.get_button(button):
                    return True
        except Exception:
            continue

    return False


def calibrate_joystick_centers():
    global joystick_axis_centers

    joystick_axis_centers = {}

    for joystick in list(joysticks.values()):
        centers = {}

        try:
            for axis in range(joystick.get_numaxes()):
                centers[axis] = float(joystick.get_axis(axis))

            joystick_axis_centers[str(joystick.get_instance_id())] = centers
        except Exception:
            continue


def start_joystick_remap():
    global joystick_remap_active, joystick_remap_started

    if not joysticks:
        init_joysticks()

    if not joysticks:
        set_message("Ingen joystick hittad.")
        return

    calibrate_joystick_centers()
    joystick_remap_active = True
    joystick_remap_started = pygame.time.get_ticks()
    set_message("F5: tryck grävknappen på handkontrollen.")


def cancel_joystick_remap():
    global joystick_remap_active
    joystick_remap_active = False
    set_message("Joystick-remap avbruten.")


def handle_joystick_remap_event(event):
    global joystick_remap_active, joystick_dig_buttons

    if not joystick_remap_active:
        return False

    if event.type == pygame.JOYBUTTONDOWN:
        joystick_dig_buttons = {int(event.button)}
        joystick_remap_active = False
        save_joystick_config()
        set_message(f"Joystick: grävknapp = {event.button}")
        return True

    return False


def gameplay_input_active():
    return (
        alive
        and not game_complete_sequence
        and not demo_mode
        and not startup_sequence
        and not highscore_entry
        and not topten_screen
        and not level_code_intro
        and not code_mode
        and not level_intro
        and not death_waiting_for_key
    )


def update_joystick_input(now):
    if not joysticks or not gameplay_input_active():
        return

    dx, dy = joystick_direction()

    if dx == 0 and dy == 0:
        if held_source == "joystick":
            clear_held_direction()
        return

    if held_source != "joystick" or held_dx != dx or held_dy != dy:
        do_direction(dx, dy, force_dig=joystick_dig_pressed())
        set_held_direction(dx, dy, now, source="joystick")


def handle_joystick_button_action(event, now):
    # Under spel: grävknappen + riktning ska ge direkt SHIFT-grävning.
    if gameplay_input_active():
        if event.button in joystick_dig_buttons:
            dx, dy = joystick_direction()

            if dx != 0 or dy != 0:
                do_direction(dx, dy, force_dig=True)
                set_held_direction(dx, dy, now, source="joystick")
                return True

        return False

    # På intro/demo/övergångar fungerar en knapp som "valfri tangent".
    if topten_screen:
        hide_topten_screen()
        return True

    if game_complete_sequence:
        begin_game_complete_close()
        return True

    if startup_sequence:
        begin_startup_close("game")
        return True

    if demo_mode:
        if demo_only_mode:
            start_demo_mode()
        else:
            begin_demo_close()
        return True

    if level_complete_transition:
        return True

    if level_code_intro:
        begin_level_code_intro_close()
        return True

    if level_intro:
        begin_level_intro_close()
        return True

    if death_waiting_for_key:
        begin_death_fade()
        return True

    return False



def normalize_sprite_map(sprite_map):
    sprite_map.setdefault("tiles", {})
    sprite_map.setdefault("animations", {})

    sprite_map["tiles"].pop("bomb_small", None)
    sprite_map["tiles"].pop("nyckel", None)

    # H/O/I-bilder styrs av sprite_map.json.
    # Här får vi inte tvinga rectar, annars skrivs dina val över vid start.

    directions = {
        "left": [0, 4],
        "right": [1, 5],
        "up": [2, 6],
        "down": [3, 7],
    }

    for name in ["player", "M", "2", "3"]:
        if name in sprite_map["animations"]:
            sprite_map["animations"][name].setdefault("directions", directions)

    if "bomb" not in sprite_map["animations"]:
        sprite_map["animations"]["bomb"] = {
            "frames": [
                [24, 153, 16, 16],
                [47, 153, 16, 16],
                [71, 153, 16, 16],
                [23, 170, 16, 16],
                [47, 170, 16, 16],
                [71, 170, 16, 16],
            ],
            "transparent": True,
            "speed_ms": 90,
        }

    return sprite_map


def make_sprite(sheet, rect, transparent=True):
    x, y, w, h = rect
    surf = sheet.subsurface((x, y, w, h)).copy().convert()

    if transparent:
        surf.set_colorkey((0, 0, 0))

    return surf



def recolor_surface(surface, src_rgb, dst_rgb):
    surf = surface.copy().convert_alpha()

    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            r, g, b, a = surf.get_at((x, y))
            if a == 0:
                continue

            if (r, g, b) == src_rgb:
                surf.set_at((x, y), (*dst_rgb, a))

    return surf


def recolor_player_pants():
    # Demo endast: byt exakt byxfärgen #5555ff till #ffff55 på karaktären.
    if "player" in animations:
        animations["player"] = [
            recolor_surface(frame, (0x55, 0x55, 0xFF), (0xFF, 0xFF, 0x55))
            for frame in animations["player"]
        ]


def rotate_demo_diamonds():
    # Demo endast: vrid diamanter 90 grader.
    if "D" in tile_sprites and tile_sprites["D"]:
        tile_sprites["D"] = pygame.transform.rotate(tile_sprites["D"], 90)


def recolor_demo_enemy_purple_to_red():
    # Demo endast: lila enemy -> röd
    # Kropp: #aa00aa -> #aa0000
    # Highlight: #ff55ff -> #ff5555
    # Öga: #55ffff -> #5555ff
    if "3" in animations:
        new_frames = []
        for frame in animations["3"]:
            updated = recolor_surface(frame, (0xAA, 0x00, 0xAA), (0xAA, 0x00, 0x00))
            updated = recolor_surface(updated, (0xFF, 0x55, 0xFF), (0xFF, 0x55, 0x55))
            updated = recolor_surface(updated, (0x55, 0xFF, 0xFF), (0x55, 0x55, 0xFF))
            new_frames.append(updated)
        animations["3"] = new_frames


def recolor_demo_outro_pants():
    # Demo endast: EOF/outrobilden ska ha gula byxor i stället för blå.
    eof = startup_surfaces.get("eof")
    if eof:
        updated = recolor_surface(eof, (0x55, 0x55, 0xFF), (0xFF, 0xFF, 0x55))
        updated = recolor_surface(updated, (0x00, 0x00, 0xAA), (0xAA, 0x55, 0x00))
        startup_surfaces["eof"] = updated


def make_blue_key_tile():
    key = tile_sprites.get("blue_key")
    if not key:
        return None

    surf = pygame.Surface((TILE, TILE)).convert()
    surf.fill((0, 0, 0))
    surf.set_colorkey((0, 0, 0))
    surf.blit(key, ((TILE - key.get_width()) // 2, (TILE - key.get_height()) // 2))
    return surf


def make_blue_exit_sprite():
    source = default_exit_sprite or tile_sprites.get("E")
    if not source:
        return None

    # Utgången är brun (#aa5500). I demo-bana 10 ska samma utgång ritas blå,
    # med blånyckelns färg #5555ff.
    return recolor_surface(source, (0xAA, 0x55, 0x00), (0x55, 0x55, 0xFF))


def load_graphics():
    global tile_sprites, animations, animation_meta, startup_surfaces, startup_names_shadow_surface, topten_entries, demo_badge_surface, default_exit_sprite, blue_exit_sprite

    try:
        sheet = load_pic_surface(OBJECTS_FILE).convert()

        startup_surfaces = {}
        startup_names_shadow_surface = None
        topten_entries = load_topten_entries()
        for key, filename in [
            ("top", TITLE_TOP_FILE),
            ("intro", TITLE_INTRO_FILE),
            ("names", TITLE_NAMES_FILE),
            ("eof", TITLE_EOF_FILE),
        ]:
            try:
                startup_surfaces[key] = load_pic_surface(filename).convert()
            except Exception as title_error:
                print(f"Kunde inte läsa {filename}: {title_error}")

        if startup_surfaces.get("names"):
            startup_names_shadow_surface = make_startup_names_shadow(startup_surfaces["names"])

        demo_badge_surface = None
        for badge_path in [game_file_path(DEMO_BADGE_FILE), Path(DEMO_BADGE_FILE)]:
            try:
                if badge_path.exists():
                    # DEM.PIC sparas som helskärmsbild. Plocka ut själva DEMO-rutan
                    # som en opak crop, precis som NAMES.PIC-rutan.
                    if badge_path.suffix.lower() == ".pic":
                        badge_full = load_pic_surface(str(badge_path)).convert()
                        demo_badge_surface = pygame.Surface((DEMO_BADGE_W, DEMO_BADGE_H)).convert()
                        demo_badge_surface.blit(badge_full, (0, 0), pygame.Rect(DEMO_BADGE_X, DEMO_BADGE_Y, DEMO_BADGE_W, DEMO_BADGE_H))
                    else:
                        demo_badge_surface = pygame.image.load(str(badge_path)).convert()
                    break
            except Exception as badge_error:
                print(f"Kunde inte läsa {badge_path}: {badge_error}")

        sprite_map = json.loads(Path(SPRITE_MAP_FILE).read_text(encoding="utf-8"))
        sprite_map = normalize_sprite_map(sprite_map)

        tile_sprites = {}
        animations = {}
        animation_meta = {}

        for name, item in sprite_map["tiles"].items():
            tile_sprites[name] = make_sprite(
                sheet,
                item["rect"],
                item.get("transparent", True),
            )

        for name, anim in sprite_map["animations"].items():
            animations[name] = [
                make_sprite(sheet, rect, anim.get("transparent", True))
                for rect in anim["frames"]
            ]

            animation_meta[name] = {
                "speed_ms": anim.get("speed_ms", 160),
                "directions": anim.get("directions"),
            }

        default_exit_sprite = tile_sprites.get("E")
        blue_exit_sprite = make_blue_exit_sprite()

        blue_key_tile = make_blue_key_tile()
        if blue_key_tile:
            tile_sprites["&"] = blue_key_tile

        if demo_campaign_mode:
            recolor_player_pants()
            recolor_demo_enemy_purple_to_red()
            recolor_demo_outro_pants()

        set_message("sprite_map.json laddad.")

    except Exception as e:
        tile_sprites = {}
        animations = {}
        animation_meta = {}
        topten_entries = load_topten_entries()
        set_message(f"Sprite-fel: {e}")


def get_anim_frame(name, now, direction_name=None, moving=True):
    frames = animations.get(name)

    if not frames:
        return None

    meta = animation_meta.get(name, {})
    speed = meta.get("speed_ms", 160)
    directions = meta.get("directions")

    if direction_name and directions:
        indexes = directions.get(direction_name)

        if indexes:
            if moving:
                local = (now // speed) % len(indexes)
                frame_i = indexes[local]
            else:
                frame_i = indexes[-1]

            frame_i = max(0, min(len(frames) - 1, frame_i))
            return frames[frame_i]

    frame_i = (now // speed) % len(frames)
    return frames[frame_i]


def draw_tile(surface, ch, sx, sy, now, wx, wy):
    if ch == " ":
        return

    px = sx * TILE
    py = sy * TILE

    if ch in ENEMY_TILES and ch in animations:
        dx, dy = enemy_dirs.get((wx, wy), DOWN)
        direction_name = dir_name_from_delta(dx, dy)
        frame = get_anim_frame(ch, now, direction_name, moving=True)

        if frame:
            surface.blit(frame, (px, py))
            return

    if ch in tile_sprites:
        surface.blit(tile_sprites[ch], (px, py))
        return

    color = colors.get(ch, (255, 0, 255))
    pygame.draw.rect(surface, color, (px, py, TILE, TILE))



def draw_tile_debug_overlay(surface, font, cam_x, cam_y, view_tiles_x=None):
    if view_tiles_x is None:
        view_tiles_x = VIEW_W

    for sy in range(VIEW_H):
        for sx in range(view_tiles_x):
            wx = cam_x + sx
            wy = cam_y + sy
            ch = grid[wy][wx]

            if ch == " ":
                continue

            px = sx * TILE
            py = sy * TILE

            # Svart bakgrund så bokstaven syns på alla sprites.
            pygame.draw.rect(surface, (0, 0, 0), (px + 1, py + 1, 9, 10))
            draw_original_font_text(surface, ch, px + 2, py + 1, (255, 255, 0))


def get_player_frame():
    frames = animations.get("player")

    if not frames:
        return None

    meta = animation_meta.get("player", {})
    directions = meta.get("directions")

    if not directions:
        return None

    indexes = directions.get(last_dir_name)

    if not indexes:
        return None

    # Original-lik steglogik:
    # - aktuell gångbild sparas i player_walk_phase
    # - den växlar vid varje gångförsök/steg
    # - om spelaren går mot vägg står han kvar men animationen fortsätter
    # - när knappen släpps ligger samma bild kvar
    frame_i = indexes[player_walk_phase % len(indexes)]
    frame_i = max(0, min(len(frames) - 1, frame_i))
    return frames[frame_i]


def draw_player(surface, sx, sy, now):
    # När spelaren är död ligger en diamant i hans grid-ruta.
    # Rita därför inte en röd gubbe ovanpå.
    if not alive:
        return

    px = sx * TILE
    py = sy * TILE

    if "player" in animations:
        frame = get_player_frame()

        if frame:
            surface.blit(frame, (px, py))
            return

    pygame.draw.rect(surface, (255, 255, 0), (px, py, TILE, TILE))


def draw_explosions(surface, cam_x, cam_y, now, view_tiles_x=None):
    global explosion_effects

    if view_tiles_x is None:
        view_tiles_x = VIEW_W

    if "bomb" in animations and len(animations["bomb"]) > 1:
        # Frame 0 är normal bomb. Explosionen börjar alltså på frame 1.
        frames = animations["bomb"][1:]
        speed = animation_meta.get("bomb", {}).get("speed_ms", 90)
    elif "explosion" in animations:
        frames = animations["explosion"]
        speed = animation_meta.get("explosion", {}).get("speed_ms", 90)
    else:
        return

    if not frames:
        return

    duration = speed * len(frames)
    still_active = []

    for x, y, start_time in explosion_effects:
        age = now - start_time

        if age >= duration:
            continue

        if cam_x <= x < cam_x + view_tiles_x and cam_y <= y < cam_y + VIEW_H:
            frame_i = min(len(frames) - 1, age // speed)
            frame = frames[frame_i]

            sx = x - cam_x
            sy = y - cam_y

            surface.blit(frame, (sx * TILE, sy * TILE))

        still_active.append((x, y, start_time))

    explosion_effects = still_active



def draw_hud_icon(surface, name, x, y):
    icon = tile_sprites.get(name)

    if icon:
        surface.blit(icon, (x, y))
        return

    # Fallback om sprite saknas.
    pygame.draw.rect(surface, (255, 255, 255), (x, y, 8, 8))


def measure_original_font_text(text, scale=1):
    if not original_bitmap_font:
        return intro_font.size(str(text))[0]

    glyphs = original_bitmap_font.get("glyphs", {})
    default_advance = int(original_bitmap_font.get("default_advance", 8))

    width = 0
    for ch in str(text):
        glyph = glyphs.get(ch) or glyphs.get(ch.lower()) or glyphs.get(" ")
        if glyph is None:
            width += default_advance * scale
        else:
            width += int(glyph.get("advance", default_advance)) * scale

    return width


def draw_hud(surface):
    hud_y = VIEW_H * TILE
    surface_w = surface.get_width()

    # Original-HUD: svart nederkant. Inga leveltiles eller extra diamantikon
    # ska synas bakom/under texten.
    pygame.draw.rect(surface, (0, 0, 0), (0, hud_y, surface_w, HUD_H))

    # Originalets bitmapfont från font.json.
    x = 0
    y = hud_y + 1
    cyan = (85, 255, 255)
    yellow = (255, 255, 0)

    x += draw_original_font_text(surface, "Diamanter: ", x, y, cyan)
    x += draw_original_font_text(surface, str(diamonds), x, y, yellow)
    x += draw_original_font_text(surface, " av ", x, y, cyan)
    x += draw_original_font_text(surface, str(required_diamonds), x, y, yellow)

    # Originalets HUD-nycklar börjar vid x=0xb0 och flyttas 16 px åt höger.
    # Det visas en ikon per färg om spelaren har minst en nyckel.
    key_x = 0xB0
    key_y = hud_y + 6

    if keys["$"] > 0:
        draw_hud_icon(surface, "hud_key_white", key_x, key_y)
        key_x += 16

    if keys["%"] > 0:
        draw_hud_icon(surface, "hud_key_red", key_x, key_y)
        key_x += 16

    if keys["^"] > 0:
        draw_hud_icon(surface, "hud_key_green", key_x, key_y)
        key_x += 16

    # Originalet ritar fyra liv-ikoner längst ner till höger, från höger mot vänster.
    life_y = hud_y + 5
    for i in range(max(0, min(lives - 1, MAX_LIVES - 1))):
        life_x = surface_w - 8 - i * 8
        draw_hud_icon(surface, "hud_life", life_x, life_y)


def load_level(index):
    global grid, player_x, player_y, diamonds, required_diamonds
    global alive, death_restart_time, death_waiting_for_key, death_fade_active, death_fade_start
    global falling_items, enemy_dirs, fall_timer, enemy_timer, keys
    global held_dx, held_dy, next_move_time, enemy_tick
    global last_dir_name, player_moving, player_walk_phase
    global level_intro, level_intro_start_time, level_intro_closing, level_intro_closing_start
    global level_code_intro, level_code_intro_closing, level_code_intro_closing_start
    global explosion_effects, pending_explosions, scheduled_bombs, reserved_bombs, bomb_hit_queue, queued_bombs, chain_next_trigger_time, bomb_exploded_this_frame

    offset = index * LEVEL_SIZE
    raw = data[offset:offset + MAP_SIZE]
    meta = data[offset + MAP_SIZE:offset + LEVEL_SIZE]

    grid = [
        [chr(raw[y * MAP_W + x]) for x in range(MAP_W)]
        for y in range(MAP_H)
    ]

    player_x = 0
    player_y = 0

    diamonds = 0
    required_diamonds = meta[0] if len(meta) else 0
    alive = True
    death_restart_time = None
    death_waiting_for_key = False
    death_fade_active = False
    death_fade_start = 0

    keys = {"$": 0, "%": 0, "^": 0, "&": 0}

    falling_items = set()
    enemy_dirs = {}

    explosion_effects = []
    pending_explosions = []
    scheduled_bombs = set()
    reserved_bombs = set()
    bomb_hit_queue = []
    queued_bombs = set()
    bomb_exploded_this_frame = False

    fall_timer = 0
    enemy_timer = 0
    enemy_tick = 0

    held_dx = 0
    held_dy = 0
    next_move_time = 0

    last_dir_name = "right"
    player_moving = False
    player_walk_phase = 0

    current_level_number = visible_level_number() if demo_campaign_mode else (index if index > PRACTICE_LEVEL_INDEX else 0)

    level_code_intro = current_level_number in LEVEL_TO_CODE and (index != PRACTICE_LEVEL_INDEX or demo_campaign_mode) and not (demo_campaign_mode and current_level_number >= 10) and not (demo_campaign_mode and current_level_number >= 10)
    level_code_intro_closing = False
    level_code_intro_closing_start = 0

    # Prövbanan startar utan "Gör dig beredd"-text, utom i spelbart demo-läge.
    level_intro = (index != PRACTICE_LEVEL_INDEX or demo_campaign_mode) and not level_code_intro
    level_intro_start_time = pygame.time.get_ticks()
    level_intro_closing = False
    level_intro_closing_start = 0

    for y in range(MAP_H):
        for x in range(MAP_W):
            if grid[y][x] == "S":
                player_x = x
                player_y = y
                grid[y][x] = " "

            elif grid[y][x] in {"M", "2"}:
                enemy_dirs[(x, y)] = DOWN

            elif grid[y][x] == "3":
                enemy_dirs[(x, y)] = LEFT

    if demo_campaign_mode and visible_level_number() == 10:
        add_demo_campaign_key_and_door()
        if blue_exit_sprite is not None:
            tile_sprites["E"] = blue_exit_sprite
    elif default_exit_sprite is not None:
        tile_sprites["E"] = default_exit_sprite

    if index == PRACTICE_LEVEL_INDEX and not demo_campaign_mode:
        set_message(f"Prövbana. Samla {required_diamonds} diamanter.")
    else:
        set_message(f"Bana {visible_level_number()}. Samla {required_diamonds} diamanter.")

    restart_music_for_level()


def in_bounds(x, y):
    return 0 <= x < MAP_W and 0 <= y < MAP_H


def is_player(x, y):
    return x == player_x and y == player_y


def walkable(ch):
    return ch in WALKABLE_TILES or ch in KEY_TILES


def get_camera(view_tiles_x=None):
    if view_tiles_x is None:
        view_tiles_x = VIEW_W

    view_tiles_x = max(VIEW_W, min(MAP_W, int(view_tiles_x)))

    cam_x = player_x - view_tiles_x // 2
    cam_y = player_y - 6

    cam_x = max(0, min(MAP_W - view_tiles_x, cam_x))
    cam_y = max(0, min(MAP_H - VIEW_H, cam_y))

    return cam_x, cam_y



def visible_level_number():
    if demo_campaign_mode:
        return demo_real_to_display_level(level_index)

    if level_index <= PRACTICE_LEVEL_INDEX:
        return 0

    return level_index


def visible_level_name():
    if level_index <= PRACTICE_LEVEL_INDEX and not demo_campaign_mode:
        return "prövbana"

    return f"bana {visible_level_number()}"


def demo_display_to_real_level(display_level):
    if display_level <= 1:
        return PRACTICE_LEVEL_INDEX
    if display_level == 10:
        return 11
    return display_level - 1


def demo_real_to_display_level(real_level):
    if real_level == PRACTICE_LEVEL_INDEX:
        return 1
    if real_level == 11:
        return 10
    return real_level + 1


def is_demo_campaign_last_level():
    return demo_campaign_mode and visible_level_number() >= 10


def add_demo_campaign_key_and_door():
    # Demo-bana 10:
    # Lägg blå nyckel på en säker plats precis före den vanliga utgången.
    # Ingen extra dörr läggs ut. Den vanliga utgången ritas blå och kräver denna nyckel.
    key_tile = "&"

    exit_positions = [
        (x, y)
        for y in range(MAP_H)
        for x in range(MAP_W)
        if grid[y][x] == "E"
    ]

    # Först: placera nyckeln direkt före/vid sidan av utgången.
    # På original bana 11 hamnar detta på rutten in till sista dörren och inte under bomben.
    for ex, ey in exit_positions:
        for kx, ky in [
            (ex - 1, ey),
            (ex - 2, ey),
            (ex, ey - 1),
            (ex, ey + 1),
            (ex - 1, ey - 1),
            (ex - 1, ey + 1),
        ]:
            if in_bounds(kx, ky) and not is_player(kx, ky) and grid[ky][kx] in {" ", "G", "O"}:
                grid[ky][kx] = key_tile
                return

    # Fallback: nära spelaren i startkammaren, också på säkert grävbar/tom ruta.
    for dx, dy in [
        (-1, 0),
        (-2, 0),
        (1, 0),
        (2, 0),
        (0, -1),
        (0, 1),
        (-1, -1),
        (1, -1),
        (-1, 1),
        (1, 1),
    ]:
        kx = player_x + dx
        ky = player_y + dy
        if in_bounds(kx, ky) and not is_player(kx, ky) and grid[ky][kx] in {" ", "G", "O"}:
            grid[ky][kx] = key_tile
            return


def death_diamond_cells(cx, cy):
    cells = []

    for y in range(cy - 1, cy + 2):
        for x in range(cx - 1, cx + 2):
            if (x, y) == (cx, cy):
                continue

            if in_bounds(x, y):
                cells.append((x, y))

    return cells


def spawn_death_diamonds():
    start_time = pygame.time.get_ticks()

    cells = [(player_x, player_y)] + death_diamond_cells(player_x, player_y)

    for x, y in cells:
        if grid[y][x] in PRESERVE_TILES:
            continue

        enemy_dirs.pop((x, y), None)
        falling_items.discard((x, y))
        grid[y][x] = "D"
        add_explosion_effect(x, y, start_time)


def begin_death_fade():
    global death_fade_active, death_fade_start

    if death_waiting_for_key and not death_fade_active:
        death_fade_active = True
        death_fade_start = pygame.time.get_ticks()




def kill_player(reason):
    global alive, lives, death_restart_time
    global death_waiting_for_key, death_fade_active, death_fade_start

    if alive:
        alive = False
        lives = max(0, lives - 1)
        death_restart_time = None
        death_waiting_for_key = False
        death_fade_active = False
        death_fade_start = 0
        clear_held_direction()
        spawn_death_diamonds()
        play_game_sound("death", min_interval_ms=250, force=True)

        if lives <= 0:
            level_for_score = visible_level_number()

            if begin_highscore_entry(level_for_score):
                set_message("")
            else:
                death_waiting_for_key = True
                set_message("GAME OVER")
        else:
            death_waiting_for_key = True
            set_message(f"{reason} Liv kvar: {lives}")


def check_enemy_contact():
    if not alive:
        return

    for y in range(max(0, player_y - 1), min(MAP_H, player_y + 2)):
        for x in range(max(0, player_x - 1), min(MAP_W, player_x + 2)):
            if grid[y][x] in ENEMY_TILES:
                if abs(x - player_x) + abs(y - player_y) <= 1:
                    kill_player("Du blev tagen av en fiende!")
                    return


def next_level():
    global level_index

    if demo_mode:
        # Demo/prövbana ska inte fortsätta till riktig bana.
        finish_demo_to_intro()
        return

    if demo_campaign_mode:
        current_display = visible_level_number()
        if current_display >= 10:
            start_game_complete_sequence()
            return
        level_index = demo_display_to_real_level(current_display + 1)
        load_level(level_index)
        return

    level_index += 1

    if level_index >= level_count:
        # Originalet kör EOF.PIC och avslutar efter sista riktiga banan.
        start_game_complete_sequence()
        return

    load_level(level_index)


def restart_level(reset_life_counter=False):
    global lives

    if reset_life_counter or lives <= 0:
        lives = MAX_LIVES

    load_level(level_index)


def collect_diamond():
    global diamonds

    diamonds += 1

    if diamonds >= required_diamonds and required_diamonds > 0:
        play_game_sound("diamond_complete", min_interval_ms=250, force=True)
    else:
        play_game_sound("diamond", min_interval_ms=55)

    set_message(f"Diamanter: {diamonds}/{required_diamonds}")


def collect_key(tile):
    keys[tile] += 1
    play_game_sound("key", min_interval_ms=80)

    if tile == "$":
        set_message("Vit nyckel.")
    elif tile == "%":
        set_message("Röd nyckel.")
    elif tile == "^":
        set_message("Grön nyckel.")
    elif tile == "&":
        set_message("Blå nyckel.")


def pickup_tile(tile):
    if tile == "D":
        collect_diamond()
    elif tile in KEY_TILES:
        collect_key(tile)


def burst_cells(cx, cy):
    cells = []

    # Vanlig bombexplosion/burst:
    # 3 kolumner och 3 rader från objektets rad och nedåt.
    for y in range(cy, cy + 3):
        for x in range(cx - 1, cx + 2):
            if in_bounds(x, y):
                cells.append((x, y))

    return cells


def centered_bomb_cells(cx, cy):
    cells = []

    # Bara när en fallande sten/bumling träffar en bomb:
    # 3x3 med bomben i centrum.
    for y in range(cy - 1, cy + 2):
        for x in range(cx - 1, cx + 2):
            if in_bounds(x, y):
                cells.append((x, y))

    return cells


def explosion_cells(cx, cy):
    return burst_cells(cx, cy)



def reserve_bomb_chain(start_x, start_y, centered=False):
    # Viktigt:
    # Originalkedjan ska inte reservera/spränga hela raden på en gång.
    # Bara den bomb som faktiskt träffas fryses och läggs i kö.
    if in_bounds(start_x, start_y) and grid[start_y][start_x] in BOMB_TILES:
        reserved_bombs.add((start_x, start_y))

def queue_bomb_hit(x, y):
    if not in_bounds(x, y):
        return

    if grid[y][x] not in BOMB_TILES:
        return

    if (x, y) in scheduled_bombs or (x, y) in queued_bombs:
        return

    reserved_bombs.add((x, y))
    queued_bombs.add((x, y))
    bomb_hit_queue.append((x, y))


def arm_next_bomb_hit(delay_ms=BOMB_HIT_DELAY_MS):
    global chain_next_trigger_time

    # Bara en aktiv bombtimer åt gången. Resten väntar.
    if scheduled_bombs or pending_explosions:
        return

    now = pygame.time.get_ticks()

    while bomb_hit_queue:
        x, y = bomb_hit_queue.pop(0)
        queued_bombs.discard((x, y))

        if not in_bounds(x, y):
            continue

        if grid[y][x] not in BOMB_TILES:
            reserved_bombs.discard((x, y))
            continue

        trigger_time = max(now, chain_next_trigger_time) + delay_ms
        chain_next_trigger_time = trigger_time

        scheduled_bombs.add((x, y))
        reserved_bombs.add((x, y))
        pending_explosions.append((trigger_time, x, y))
        return


def schedule_explosion(x, y, delay_ms=BOMB_HIT_DELAY_MS):
    queue_bomb_hit(x, y)
    arm_next_bomb_hit(delay_ms)


def remove_pending_explosion_at(x, y):
    global pending_explosions

    pending_explosions = [
        item for item in pending_explosions
        if (item[1], item[2]) != (x, y)
    ]


def can_bomb_fall_down(x, y):
    below_y = y + 1

    if not in_bounds(x, below_y):
        return False

    if is_player(x, below_y):
        return False

    return grid[below_y][x] == " "


def bomb_should_explode_after_move(x, y):
    below_y = y + 1

    if not in_bounds(x, below_y):
        return True

    if is_player(x, below_y):
        return True

    return grid[below_y][x] != " "


def update_pending_explosions():
    global pending_explosions

    now = pygame.time.get_ticks()

    due = []
    still_pending = []

    for trigger_time, x, y in pending_explosions:
        if now >= trigger_time:
            due.append((x, y))
        else:
            still_pending.append((trigger_time, x, y))

    pending_explosions = still_pending

    if due:
        # Säkerhet: spräng max en timerbomb per frame.
        x, y = due[0]

        # Om gamla pending-listor råkar innehålla fler, lägg tillbaka dem
        # som köade bomber så de får ny 300 ms-tur senare.
        for ex, ey in due[1:]:
            if in_bounds(ex, ey) and grid[ey][ex] in BOMB_TILES:
                scheduled_bombs.discard((ex, ey))
                queue_bomb_hit(ex, ey)

        scheduled_bombs.discard((x, y))
        reserved_bombs.discard((x, y))
        queued_bombs.discard((x, y))

        if in_bounds(x, y) and grid[y][x] in BOMB_TILES:
            explode_at(x, y)

    arm_next_bomb_hit()


def add_explosion_effect(x, y, start_time):
    explosion_effects.append((x, y, start_time))


def explode_at(start_x, start_y, centered=False):
    global enemy_dirs, falling_items, explosion_effects, reserved_bombs, queued_bombs
    global bomb_exploded_this_frame

    if not in_bounds(start_x, start_y):
        return

    bomb_exploded_this_frame = True

    scheduled_bombs.discard((start_x, start_y))
    reserved_bombs.discard((start_x, start_y))
    queued_bombs.discard((start_x, start_y))

    if centered:
        cells = centered_bomb_cells(start_x, start_y)
    else:
        cells = explosion_cells(start_x, start_y)

    if cells:
        set_message("BOOM!")
        play_game_sound("explode", min_interval_ms=120, force=True)

    start_time = pygame.time.get_ticks()

    for x, y in cells:
        tile = grid[y][x]

        if is_player(x, y):
            kill_player("Du sprängdes!")

        if tile in BOMB_TILES and (x, y) != (start_x, start_y):
            # Alla träffade bomber får delay. De exploderar inte direkt.
            # arm_next_bomb_hit ser till att bara en bomb i taget får aktiv timer.
            queue_bomb_hit(x, y)
            continue

        if tile not in PRESERVE_TILES:
            grid[y][x] = " "
            add_explosion_effect(x, y, start_time)

        enemy_dirs.pop((x, y), None)
        falling_items.discard((x, y))

        if grid[y][x] not in BOMB_TILES:
            reserved_bombs.discard((x, y))

    arm_next_bomb_hit()

def monster_burst_at(start_x, start_y):
    global enemy_dirs, falling_items, explosion_effects, reserved_bombs, queued_bombs

    if not in_bounds(start_x, start_y):
        return

    cells = burst_cells(start_x, start_y)
    start_time = pygame.time.get_ticks()

    # Viktigt:
    # Funktionen anropas från rutan där stenen/diamanten/bomben är,
    # inte nödvändigtvis från fiendens egen ruta.
    # Därför måste vi skanna hela 3x3-området för att hitta vilken
    # fiende som faktiskt krossades.
    hit_m = False
    hit_2 = False
    hit_bomb = False

    for x, y in cells:
        tile = grid[y][x]

        if tile == "M":
            hit_m = True
        elif tile == "2":
            hit_2 = True
        elif tile in BOMB_TILES:
            hit_bomb = True

    # Originalbeteende:
    # M -> diamant-burst
    # 2 -> sten/bumling-burst
    # Z/bomb -> bara rensning
    # 3 ensam -> rensas utan sten/diamant
    if hit_m:
        burst_tile = "D"
    elif hit_2:
        burst_tile = "B"
    elif hit_bomb:
        burst_tile = " "
    else:
        burst_tile = " "

    set_message("Fiende krossad!")

    # Inspelat ljudläge/originalmappning enligt test:
    # M-fiende som blir diamanter använder diamantljud.
    # anim:2 som blir sten använder sten/fall-ljud.
    if hit_m:
        play_game_sound("enemy_diamond", min_interval_ms=120)
    elif hit_2:
        play_game_sound("enemy_stone", min_interval_ms=120)
    else:
        play_game_sound("enemy", min_interval_ms=120)

    for x, y in cells:
        tile = grid[y][x]

        if is_player(x, y):
            kill_player("Du krossades av raset!")

        enemy_dirs.pop((x, y), None)
        falling_items.discard((x, y))
        scheduled_bombs.discard((x, y))
        reserved_bombs.discard((x, y))
        queued_bombs.discard((x, y))
        remove_pending_explosion_at(x, y)

        if tile in PRESERVE_TILES:
            continue

        # Om en bomb råkar ligga i samma område triggas kedja,
        # men rutorna skrivs inte om till diamant/sten av bomben.
        if tile in BOMB_TILES:
            schedule_explosion(x, y, BOMB_HIT_DELAY_MS)
            continue

        grid[y][x] = burst_tile
        add_explosion_effect(x, y, start_time)



def mark_player_step():
    global player_moving, player_walk_phase

    player_moving = True
    player_walk_phase ^= 1


def mark_player_blocked_step():
    # Originalbeteende: om spelaren håller riktning mot vägg/objekt
    # flyttas han inte, men gånganimation och gångljud fortsätter.
    mark_player_step()
    play_game_sound("walk", min_interval_ms=65)



def dig(dx, dy):
    tx = player_x + dx
    ty = player_y + dy

    if not in_bounds(tx, ty):
        return

    target = grid[ty][tx]

    if target in DIGGABLE_TILES or target in KEY_TILES:
        pickup_tile(target)

        if target not in DIAMOND_TILES and target not in KEY_TILES:
            play_game_sound("dig", min_interval_ms=45)

        grid[ty][tx] = " "
        falling_items.discard((tx, ty))


def try_open_door(nx, ny, target):
    required_key = DOOR_TO_KEY[target]

    if keys[required_key] <= 0:
        set_message("Dörren är låst.")
        return False

    keys[required_key] -= 1
    grid[ny][nx] = " "
    play_game_sound("door", min_interval_ms=100)
    set_message("Dörr öppnad.")
    return True



def push_object(nx, ny, dx, dy):
    global player_x, player_y

    target = grid[ny][nx]
    px = nx + dx
    py = ny + dy

    if not in_bounds(px, py):
        return False

    if grid[py][px] != " " or is_player(px, py):
        return False

    # Ett objekt som redan håller på att falla får inte knuffas vidare över hål.
    if (nx, ny) in falling_items:
        return False

    grid[py][px] = target
    grid[ny][nx] = " "

    player_x = nx
    player_y = ny
    mark_player_step()
    play_game_sound("push", min_interval_ms=60)

    falling_items.discard((nx, ny))
    falling_items.discard((px, py))

    # Om objektet knuffas ut över ett hål ska det börja falla direkt och
    # kan inte "skjutas vidare" över hålet innan nästa gravity-tick.
    if in_bounds(px, py + 1) and grid[py + 1][px] == " " and not is_player(px, py + 1):
        falling_items.add((px, py))

    return True


def move_player(dx, dy):
    global player_x, player_y

    nx = player_x + dx
    ny = player_y + dy

    if not in_bounds(nx, ny):
        mark_player_blocked_step()
        return

    target = grid[ny][nx]

    if target in ENEMY_TILES:
        kill_player("Du blev tagen av en fiende!")
        return

    if target in DOOR_TILES:
        if try_open_door(nx, ny, target):
            player_x = nx
            player_y = ny
            mark_player_step()
        else:
            mark_player_blocked_step()
        return

    # Knuffa bumling/bomb vänster eller höger.
    if target in PUSHABLE_TILES and dy == 0:
        if not push_object(nx, ny, dx, 0):
            mark_player_blocked_step()
        return

    # Knuffa bumling/bomb uppåt om rutan ovanför är tom.
    if target in PUSHABLE_TILES and dx == 0 and dy == -1:
        if not push_object(nx, ny, 0, -1):
            mark_player_blocked_step()
        return

    if walkable(target):
        pickup_tile(target)

        if target in {"G", "O"}:
            # Gång in i jord går via originalets vanliga rörelseljud, ID 0.
            # SHIFT-grävning använder däremot originalets ID 4.
            play_game_sound("walk_into_dirt", min_interval_ms=45)

        if target == "E":
            if diamonds >= required_diamonds:
                if demo_campaign_mode and visible_level_number() >= 10:
                    if keys["&"] <= 0:
                        set_message("Behöver blå nyckeln.")
                        mark_player_blocked_step()
                        return
                    keys["&"] -= 1
                    play_game_sound("door", min_interval_ms=100)

                play_game_sound("exit", min_interval_ms=250, force=True)

                # Visa spelaren på utgången och kör sedan originalets slumpade
                # fade/wipe innan nästa nivå-titel visas.
                player_x = nx
                player_y = ny
                mark_player_step()
                begin_level_complete_transition()
            else:
                set_message(f"Behöver {required_diamonds - diamonds} diamanter till.")
                mark_player_blocked_step()
            return

        grid[ny][nx] = " "
        player_x = nx
        player_y = ny
        mark_player_step()
        falling_items.discard((nx, ny))

        # Originalet triggar även ett kort ljud vid vanlig gång.
        # Behåll separata ljud för jord, diamant, nyckel och utgång.
        if target == " ":
            play_game_sound("walk", min_interval_ms=65)

        check_enemy_contact()
        return

    mark_player_blocked_step()


def do_direction(dx, dy, force_dig=False):
    global last_dir_name

    last_dir_name = dir_name_from_delta(dx, dy)

    if force_dig or (pygame.key.get_mods() & pygame.KMOD_SHIFT):
        dig(dx, dy)
    else:
        move_player(dx, dy)


def can_move_to(x, y):
    return in_bounds(x, y) and grid[y][x] == " " and not is_player(x, y)


def try_roll(x, y, tile):
    # Originalet testar höger först, sedan vänster.
    # Objektet hamnar diagonalt nedåt, inte på samma rad.
    for dx in (1, -1):
        if can_move_to(x + dx, y) and can_move_to(x + dx, y + 1):
            grid[y][x] = " "
            grid[y + 1][x + dx] = tile
            return x + dx, y + 1

    return None


def update_gravity():
    global falling_items

    new_falling = set()
    moved_to = set()

    positions = []

    # Originalet går från botten till toppen. Då faller staplar tätt,
    # eftersom en ruta som nyss tömts kan fyllas av objektet ovanför
    # i samma gravity-steg.
    for y in range(MAP_H - 2, -1, -1):
        for x in range(MAP_W):
            if grid[y][x] in MOVING_TILES:
                positions.append((x, y, grid[y][x]))

    for x, y, tile in positions:
        # Efter en bombexplosion ska inte fler bomber få falla/explodera
        # samma gravity-tick. Annars ser bombkedjor simultana ut.
        if bomb_exploded_this_frame:
            break

        if (x, y) in moved_to:
            continue

        if grid[y][x] != tile:
            continue

        # Bomb som ingår i en aktiv bombkedja ska stå still.
        if tile == "Z" and (
            (x, y) in scheduled_bombs or
            (x, y) in reserved_bombs or
            (x, y) in queued_bombs
        ):
            continue

        was_falling = (x, y) in falling_items
        below_y = y + 1

        if not in_bounds(x, below_y):
            if tile == "Z" and was_falling:
                explode_at(x, y)
            continue

        below = grid[below_y][x]

        if is_player(x, below_y):
            if was_falling:
                if tile == "Z":
                    explode_at(x, y)
                else:
                    kill_player("Du blev krossad!")
            continue

        if below in ENEMY_TILES and was_falling:
            if tile == "Z":
                explode_at(x, y)
            else:
                monster_burst_at(x, y)
            continue

        if tile == "B" and below == "D" and was_falling:
            # Original: en fallande bumling som landar på diamant
            # gör diamanten till bumling.
            grid[below_y][x] = "B"
            falling_items.discard((x, y))
            play_game_sound("land", min_interval_ms=70)
            continue

        if tile == "B" and below in BOMB_TILES and was_falling:
            # Fallande bumling på bomb:
            # första bomben exploderar direkt i centrerad 3x3.
            grid[y][x] = " "
            falling_items.discard((x, y))
            explode_at(x, below_y, centered=True)
            continue

        if tile == "Z" and below in BOMB_TILES and was_falling:
            # Fallande bomb som träffar en annan bomb:
            # den fallande bomben exploderar direkt på sin plats.
            explode_at(x, y)
            continue

        if below == " ":
            grid[y][x] = " "
            grid[below_y][x] = tile
            moved_to.add((x, below_y))

            # Original: om en bumling efter fallet hamnar ovanför diamant,
            # blir diamanten bumling.
            if tile == "B" and in_bounds(x, below_y + 1) and grid[below_y + 1][x] == "D":
                grid[below_y + 1][x] = "B"
                continue

            if tile == "Z" and bomb_should_explode_after_move(x, below_y):
                explode_at(x, below_y)
            else:
                new_falling.add((x, below_y))

            continue

        if below in ROUNDED_TILES:
            rolled = try_roll(x, y, tile)

            if rolled:
                moved_to.add(rolled)
                rx, ry = rolled

                # Originalet kontrollerar spelarkontakt direkt efter rull/fall.
                if is_player(rx, ry + 1):
                    if tile == "Z":
                        explode_at(rx, ry)
                    elif (x, y) in falling_items:
                        kill_player("Du blev krossad!")
                    continue

                if tile == "Z" and bomb_should_explode_after_move(rx, ry):
                    explode_at(rx, ry)
                else:
                    new_falling.add(rolled)

                continue

        if was_falling and tile != "Z":
            play_game_sound("land", min_interval_ms=70)

        # Om en bomb redan var fallande och nu står mot något,
        # ska den explodera på sin nuvarande ruta.
        if tile == "Z" and was_falling:
            explode_at(x, y)

    falling_items = new_falling


def turn_right(direction):
    dx, dy = direction
    return -dy, dx


def turn_left(direction):
    dx, dy = direction
    return dy, -dx


def reverse_dir(direction):
    dx, dy = direction
    return -dx, -dy


def enemy_can_move_to(x, y):
    return in_bounds(x, y) and grid[y][x] == " " and not is_player(x, y)


def try_enemy_move(x, y, tile, direction, new_dirs):
    dx, dy = direction
    nx = x + dx
    ny = y + dy

    if in_bounds(nx, ny) and is_player(nx, ny):
        kill_player("Du blev tagen av en fiende!")
        new_dirs[(x, y)] = direction
        return True

    if enemy_can_move_to(nx, ny):
        grid[y][x] = " "
        grid[ny][nx] = tile
        new_dirs[(nx, ny)] = direction
        return True

    return False


def wall_follower_dirs(tile, direction):
    if tile == "M":
        return [
            turn_right(direction),
            direction,
            turn_left(direction),
            reverse_dir(direction),
        ]

    return [
        turn_left(direction),
        direction,
        turn_right(direction),
        reverse_dir(direction),
    ]


def chaser_dirs(x, y):
    dx = 0
    dy = 0

    if player_x < x:
        dx = -1
    elif player_x > x:
        dx = 1

    if player_y < y:
        dy = -1
    elif player_y > y:
        dy = 1

    dirs = []

    if dx != 0:
        dirs.append((dx, 0))
    if dy != 0:
        dirs.append((0, dy))
    if dx != 0:
        dirs.append((-dx, 0))
    if dy != 0:
        dirs.append((0, -dy))

    for direction in [UP, RIGHT, DOWN, LEFT]:
        if direction not in dirs:
            dirs.append(direction)

    return dirs


def update_enemies():
    global enemy_dirs, enemy_tick

    enemy_tick += 1
    new_dirs = {}
    enemies = []

    for y in range(MAP_H):
        for x in range(MAP_W):
            if grid[y][x] in ENEMY_TILES:
                enemies.append((x, y, grid[y][x]))

    for x, y, tile in enemies:
        if grid[y][x] != tile:
            continue

        old_dir = enemy_dirs.get((x, y), DOWN)

        if tile == "3":
            if enemy_tick % 2 == 1:
                new_dirs[(x, y)] = old_dir
                continue

            candidates = chaser_dirs(x, y)

        else:
            candidates = wall_follower_dirs(tile, old_dir)

        moved = False

        for direction in candidates:
            if try_enemy_move(x, y, tile, direction, new_dirs):
                moved = True
                break

        if not moved and grid[y][x] == tile:
            new_dirs[(x, y)] = old_dir

    enemy_dirs = new_dirs
    check_enemy_contact()



def restart_game_from_beginning():
    global level_index, lives, restart_from_beginning_after_topten
    global topten_screen, highscore_entry

    if demo_campaign_mode:
        level_index = PRACTICE_LEVEL_INDEX
    else:
        level_index = FIRST_REAL_LEVEL_INDEX
    lives = MAX_LIVES
    restart_from_beginning_after_topten = False
    topten_screen = False
    highscore_entry = False
    load_level(level_index)


def show_topten_screen():
    global topten_screen
    if demo_campaign_mode:
        return
    topten_screen = True
    stop_music_playback()
    clear_held_direction()


def hide_topten_screen():
    global topten_screen

    if restart_from_beginning_after_topten:
        restart_game_from_beginning()
        return

    topten_screen = False
    clear_held_direction()


def start_code_mode():
    global code_mode, code_text

    code_mode = True
    code_text = ""
    clear_held_direction()
    set_message("Skriv in kod:")


def submit_code():
    global code_mode, code_text, level_index

    if code_text in LEVEL_CODES:
        level_index = LEVEL_CODES[code_text]
        code_mode = False
        load_level(level_index)
    else:
        set_message("FELAKTIG KOD!")
        code_text = ""


def handle_code_key(e):
    global code_mode, code_text

    if e.key == pygame.K_ESCAPE:
        code_mode = False
        code_text = ""
        return

    if e.key == pygame.K_RETURN:
        submit_code()
        return

    if e.key == pygame.K_BACKSPACE:
        code_text = code_text[:-1]
        return

    if e.unicode.isdigit() and len(code_text) < 8:
        code_text += e.unicode



def draw_centered_text(surface, font, text, y, color):
    text = str(text)
    text_w = measure_original_font_text(text)
    text_h = int(original_bitmap_font.get("default_height", 8)) if original_bitmap_font else intro_font.get_height()
    x = (surface.get_width() - text_w) // 2
    draw_original_font_text(surface, text, x, y, color)
    return pygame.Rect(x, y, text_w, text_h)


def draw_level_intro(surface, now):
    # Behåll originalbeteendet: helt svart skärm och slumpad/flimrande DOS-färg.
    # Bara själva font-renderingen är bytt till font.json.
    surface.fill((0, 0, 0))

    dos_text_colors = [
        (0, 0, 0),        # 0 svart
        (0, 0, 170),      # 1 blå
        (0, 170, 0),      # 2 grön
        (0, 170, 170),    # 3 cyan
        (170, 0, 0),      # 4 röd
        (170, 0, 170),    # 5 magenta
        (170, 85, 0),     # 6 brun/gul
        (170, 170, 170),  # 7 ljusgrå
        (85, 85, 85),     # 8 mörkgrå
        (85, 85, 255),    # 9 ljusblå
        (85, 255, 85),    # 10 ljusgrön
        (85, 255, 255),   # 11 ljuscyan
        (255, 85, 85),    # 12 ljusröd
        (255, 85, 255),   # 13 ljusmagenta
        (255, 255, 85),   # 14 gul
        (255, 255, 255),  # 15 vit
    ]

    color = dos_text_colors[random.randrange(16)]

    if level_index == PRACTICE_LEVEL_INDEX and not demo_campaign_mode:
        title = "Gör dig beredd på prövbana!"
    else:
        title = f"Gör dig beredd på bana {visible_level_number()}!"

    text_w = measure_original_font_text(title, scale=1)

    if original_bitmap_font:
        text_h = int(original_bitmap_font.get("default_height", 8))
    else:
        text_h = intro_font.get_height()

    x = (surface.get_width() - text_w) // 2
    y = SCREEN_H // 2 - 12

    draw_original_font_text(surface, title, x, y, color, scale=1)
    title_rect = pygame.Rect(x, y, text_w, text_h)

    if not level_intro_closing:
        return

    elapsed = now - level_intro_closing_start
    progress = max(0.0, min(1.0, elapsed / LEVEL_INTRO_CLOSE_MS))

    # Svart wipe från båda sidorna över själva texten, som före fontbytet.
    half_w = title_rect.width // 2
    wipe_w = int(half_w * progress) + 1

    pygame.draw.rect(
        surface,
        (0, 0, 0),
        (title_rect.left, title_rect.top, wipe_w, title_rect.height),
    )
    pygame.draw.rect(
        surface,
        (0, 0, 0),
        (title_rect.right - wipe_w, title_rect.top, wipe_w, title_rect.height),
    )


def start_level_intro():
    global level_intro, level_intro_start_time, level_intro_closing, level_intro_closing_start
    level_intro = True
    level_intro_start_time = pygame.time.get_ticks()
    level_intro_closing = False
    level_intro_closing_start = 0


def begin_level_intro_close():
    global level_intro_closing, level_intro_closing_start
    if not level_intro_closing:
        level_intro_closing = True
        level_intro_closing_start = pygame.time.get_ticks()


def finish_level_intro():
    global level_intro, level_intro_closing
    level_intro = False
    level_intro_closing = False

    # Originalet spelar FUN_1000_0b5b(2) vid banstart i FUN_1000_2e92,
    # efter att banan laddats/ritats och innan själva spel-loopen börjar.
    if (level_index != PRACTICE_LEVEL_INDEX or demo_campaign_mode) and not demo_mode:
        play_game_sound("level_start", min_interval_ms=250, force=True)

    restart_music_for_level()
    clear_held_direction()



def fit_title_surface(surface):
    if surface is None:
        return None

    if surface.get_width() == SCREEN_W and surface.get_height() == SCREEN_H:
        return surface

    # Originalbilderna är 320x200. Lägg dem överst och lämna HUD-ytan svart.
    return surface


def blit_pic_screen(surface, pic):
    surface.fill((0, 0, 0))

    if pic:
        x = (surface.get_width() - pic.get_width()) // 2
        surface.blit(pic, (x, 0))


def make_startup_names_shadow(pic):
    # Originalet använder bara namnrutan från NAMES.PIC:
    # x=159..319, y=118..156.
    #
    # Viktigt: svart i denna ruta ska INTE vara transparent.
    # Det är den svarta bakgrunden som skuggan/texten ligger på.
    # Bara allt utanför denna crop ska ignoreras.
    rect = pygame.Rect(159, 118, 161, 39)

    overlay = pygame.Surface((rect.w, rect.h)).convert()
    overlay.blit(pic, (0, 0), rect)
    return overlay


def blit_startup_names_with_shadow(surface, names_pic):
    global startup_names_shadow_surface

    if not names_pic:
        return

    if startup_names_shadow_surface is None:
        startup_names_shadow_surface = make_startup_names_shadow(names_pic)

    # Kopiera namnrutan opakt, exakt som originalets screen-copy:
    # svart bakgrund + grå skugga + grön text.
    base_x = (surface.get_width() - SCREEN_W) // 2
    surface.blit(startup_names_shadow_surface, (base_x + 159, 118))


def wrap_text(text, font, max_width):
    lines = []

    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()

        if not paragraph:
            lines.append("")
            continue

        words = paragraph.split()
        line = ""

        for word in words:
            test = word if not line else f"{line} {word}"

            if measure_original_font_text(test) <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word

        if line:
            lines.append(line)

    return lines


def load_original_bitmap_font():
    global original_bitmap_font

    candidates = []

    try:
        candidates.append(game_file_path(BITMAP_FONT_FILE))
    except NameError:
        pass

    candidates.append(Path(BITMAP_FONT_FILE))

    for path in candidates:
        try:
            if path.exists():
                original_bitmap_font = json.loads(path.read_text(encoding="utf-8"))
                print(f"Laddade bitmapfont: {path}")
                return
        except Exception as exc:
            print(f"Kunde inte läsa bitmapfont {path}: {exc}")

    original_bitmap_font = None
    print("Ingen font.json hittades, använder fallback-font.")


def draw_original_font_text(surface, text, x, y, color, scale=1):
    # Ritar text med extraherad originalfont från font.json.
    # Returnerar bredden som ritades. Fallbackar till pygame-font om font.json saknas.
    if not original_bitmap_font:
        label = intro_font.render(str(text), False, color)
        surface.blit(label, (x, y))
        return label.get_width()

    start_x = x
    glyphs = original_bitmap_font.get("glyphs", {})
    default_advance = int(original_bitmap_font.get("default_advance", 8))

    for ch in str(text):
        if ch == "\n":
            break

        glyph = glyphs.get(ch) or glyphs.get(ch.lower()) or glyphs.get(" ")

        if glyph is None:
            x += default_advance * scale
            continue

        for gy, row in enumerate(glyph.get("rows", [])):
            for gx, bit in enumerate(row):
                if bit == "1":
                    pygame.draw.rect(
                        surface,
                        color,
                        (x + gx * scale, y + gy * scale, scale, scale),
                    )

        x += int(glyph.get("advance", default_advance)) * scale

    return x - start_x



def draw_scaled_font_text(surface, use_font, text, x, y, color, x_scale=1.23):
    # Gammal pygame-font-wrapper. Behåll namnet för kompatibilitet,
    # men rendera med font.json. x_scale ignoreras eftersom originalfonten
    # redan är pixelkorrekt.
    return draw_original_font_text(surface, str(text), x, y, color)


def draw_wrapped_text(surface, text, x, y, color, max_width, line_h=10):
    for line in wrap_text(text, None, max_width):
        if line:
            draw_original_font_text(surface, line, x, y, color)

        y += line_h

    return y


def draw_startup_help_1(surface):
    surface.fill((0, 0, 0))

    lines = [
        "Flytta gubben med piltangenterna eller",
        "använd joysticken om du har en sådan.",
        "För att gräva trycker du SHIFT +",
        "piltangent eller knapp på joystick +",
        "riktning. Om du på något sätt skulle",
        "fastna på en bana kan du trycka F10 för",
        "att starta om banan från början.",
    ]

    x = 0
    y = 73
    line_h = 10
    color = (85, 255, 255)

    for line in lines:
        draw_original_font_text(surface, line, x, y, color)
        y += line_h


def draw_startup_help_2(surface):
    surface.fill((0, 0, 0))

    lines = [
        "Tryck F1 för att visa tio i topp-listan",
        "Tryck F2 för att stänga av/sätta på",
        "          ljudet.",
        "Tryck F3 för att byta ljudläge.",
        "Tryck F5 för att kalibrera joysticken.",
        "Tryck ESC när du vill avsluta spelet.",
        "",
        "Var tionde bana får du en hemlig kod.",
        "Skriv ned den på ett papper. När du",
        "sedan vill spela igen trycker du F6 och",
        "skriver in koden. På detta sätt får du",
        "börja direkt på den bana du fick koden",
        "till.",
    ]

    x = 0
    y = 44
    line_h = 10
    color = (255, 255, 255)

    for line in lines:
        if line:
            draw_original_font_text(surface, line, x, y, color)
        y += line_h


def game_file_path(filename):
    paths = [
        Path(filename),
        Path(__file__).resolve().parent / filename,
    ]

    for path in paths:
        if path.exists():
            return path

    return paths[0]


def load_topten_entries():
    path = game_file_path(TOPTEN_FILE)

    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return [(0, "(Namn)")] * 10

    entries = []

    # Originalformatet är binärt:
    # 10 poster * 27 byte
    # 2 byte little-endian bana + 25 byte CP437-namn.
    if len(raw) >= 270:
        for i in range(10):
            rec = raw[i * 27:(i + 1) * 27]
            level = int.from_bytes(rec[:2], "little", signed=False)

            name_bytes = rec[2:27].split(b"\x00", 1)[0]
            name = name_bytes.decode("cp437", errors="replace").strip()

            if not name:
                name = "(Namn)"

            entries.append((level, name))

        return entries

    # Fallback om någon TOPTEN.DAT råkar vara textbaserad.
    lines = raw.decode("cp437", errors="replace").splitlines()

    i = 0
    while len(entries) < 10 and i < len(lines):
        try:
            level = int(lines[i].strip() or "0")
        except ValueError:
            level = 0

        name = lines[i + 1].strip() if i + 1 < len(lines) else ""

        if not name:
            name = "(Namn)"

        entries.append((level, name))
        i += 2

    while len(entries) < 10:
        entries.append((0, "(Namn)"))

    return entries



def save_topten_entries():
    entries = list(topten_entries)

    while len(entries) < 10:
        entries.append((0, ""))

    raw = bytearray()

    for level, name in entries[:10]:
        raw += int(level).to_bytes(2, "little", signed=False)

        name_bytes = str(name).encode("cp437", errors="replace")[:25]
        name_bytes = name_bytes.ljust(25, b" ")
        raw += name_bytes

    game_file_path(TOPTEN_FILE).write_bytes(bytes(raw))


def highscore_rank_for_level(level):
    entries = topten_entries if topten_entries else load_topten_entries()

    for i, (old_level, _old_name) in enumerate(entries[:10]):
        if level > old_level:
            return i

    if len(entries) < 10:
        return len(entries)

    return None


def begin_highscore_entry(level):
    global highscore_entry, highscore_name, highscore_level, highscore_insert_index
    global topten_entries

    if not topten_entries:
        topten_entries = load_topten_entries()

    rank = highscore_rank_for_level(level)

    if rank is None:
        return False

    highscore_entry = True
    highscore_name = ""
    highscore_level = level
    highscore_insert_index = rank
    stop_music_playback()
    clear_held_direction()
    return True


def begin_highscore_entry_force(level):
    global highscore_entry, highscore_name, highscore_level, highscore_insert_index
    global topten_entries, restart_from_beginning_after_topten, topten_screen

    if not topten_entries:
        topten_entries = load_topten_entries()

    rank = highscore_rank_for_level(level)

    # Efter att alla banor klarats ska namn-inmatning visas ändå.
    # Om listan redan är full med lika/högre nivå läggs posten sist.
    if rank is None:
        rank = min(9, len(topten_entries))

    highscore_entry = True
    highscore_name = ""
    highscore_level = level
    highscore_insert_index = rank
    restart_from_beginning_after_topten = False
    topten_screen = False
    stop_music_playback()
    clear_held_direction()
    return True


def finish_highscore_entry():
    global highscore_entry, highscore_name, highscore_level, highscore_insert_index
    global topten_entries, topten_screen, restart_from_beginning_after_topten

    name = highscore_name.strip() or "(Namn)"

    entries = list(topten_entries if topten_entries else load_topten_entries())
    insert_at = highscore_insert_index

    if insert_at is None:
        insert_at = highscore_rank_for_level(highscore_level)

    if insert_at is None:
        highscore_entry = False
        restart_from_beginning_after_topten = True
        topten_screen = True
        return

    entries.insert(insert_at, (highscore_level, name))
    topten_entries = entries[:10]
    save_topten_entries()

    highscore_entry = False
    highscore_name = ""
    highscore_level = 0
    highscore_insert_index = None

    restart_from_beginning_after_topten = True
    topten_screen = True


def handle_highscore_key(e):
    global highscore_name

    if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        finish_highscore_entry()
        return

    if e.key == pygame.K_ESCAPE:
        finish_highscore_entry()
        return

    if e.key == pygame.K_BACKSPACE:
        highscore_name = highscore_name[:-1]
        return

    if e.unicode and len(highscore_name) < HIGHSCORE_NAME_MAX:
        ch = e.unicode

        if ch.isprintable() and ch not in "\\r\\n\\t":
            highscore_name += ch


def draw_highscore_entry(surface, now):
    surface.fill((0, 0, 0))

    draw_centered_text(
        surface,
        font,
        "Du har spelat så bra att du kommer på",
        SCREEN_H // 2 - 42,
        (85, 255, 85),
    )

    draw_centered_text(
        surface,
        font,
        "Tio i Topp listan.",
        SCREEN_H // 2 - 20,
        (255, 85, 85),
    )

    x = 34
    y = SCREEN_H // 2 + 14

    shown = highscore_name

    if (now // 250) % 2 == 0:
        shown += "_"

    draw_original_font_text(surface, shown, x, y, (85, 255, 85))


def draw_startup_topten(surface):
    surface.fill((0, 0, 0))

    def line(text, x, y, color):
        draw_original_font_text(surface, str(text), x, y, color)

    line("Tio i topp lista", 96, 11, (255, 255, 85))
    line("Bana", 22, 33, (255, 85, 85))
    line("Namn", 81, 33, (255, 85, 85))

    entries = topten_entries if topten_entries else load_topten_entries()

    y = 56
    for level, name in entries[:10]:
        line(level, 22, y, (85, 255, 255))
        line(name, 81, y, (85, 255, 255))
        y += 10


def original_wipe_cells():
    # Ghidra FUN_1000_5e38:
    # 20x13 rutor, 16 px block, från kanterna inåt i spiral.
    cells = []
    left = 0
    top = 0
    right = 0x13
    bottom = 0x0C

    while bottom > 5:
        for y in range(top, bottom + 1):
            cells.append((left, y))

        for x in range(left, right + 1):
            cells.append((x, bottom))

        for y in range(bottom, top - 1, -1):
            cells.append((right, y))

        for x in range(right, left - 1, -1):
            cells.append((x, top))

        left += 1
        top += 1
        right -= 1
        bottom -= 1

    # Ta bort dubbletter men behåll ordning.
    result = []
    seen = set()

    for cell in cells:
        if cell not in seen:
            seen.add(cell)
            result.append(cell)

    return result


ORIGINAL_WIPE_CELLS = original_wipe_cells()


def draw_original_wipe(surface, now, start_time, duration_ms=250):
    elapsed = now - start_time
    progress = max(0.0, min(1.0, elapsed / max(1, duration_ms)))
    count = int(len(ORIGINAL_WIPE_CELLS) * progress)

    for col, row in ORIGINAL_WIPE_CELLS[:count]:
        pygame.draw.rect(
            surface,
            (0, 0, 0),
            (col * TILE, row * TILE, TILE, TILE),
        )


def draw_side_wipe(surface, now, start_time, duration_ms):
    # Namnet finns kvar för gamla anrop, men beteendet är nu originalets
    # block/wipe från skärmbufferten, inte en mjuk rektangel-fade.
    draw_original_wipe(surface, now, start_time, duration_ms)


def spiral_wipe_groups():
    # Ghidra FUN_1000_5e38: spiral/ramar från kanten inåt.
    groups = []
    left = 0
    top = 0
    right = 0x13
    bottom = 0x0C

    while bottom > 5:
        group = []

        for y in range(top, bottom + 1):
            group.append((left, y))

        for x in range(left, right + 1):
            group.append((x, bottom))

        for y in range(bottom, top - 1, -1):
            group.append((right, y))

        for x in range(right, left - 1, -1):
            group.append((x, top))

        # ta bort dubbletter inom gruppen men behåll ordning
        clean = []
        seen = set()
        for cell in group:
            if cell not in seen:
                seen.add(cell)
                clean.append(cell)

        groups.append(clean)

        left += 1
        top += 1
        right -= 1
        bottom -= 1

    return groups


def alternating_row_wipe_groups():
    # Ghidra FUN_1000_5eed: först jämna rader, sedan udda rader.
    groups = []

    for row in range(0, 0x0D, 2):
        groups.append([(col, row) for col in range(0x14)])

    for row in range(1, 0x0D, 2):
        groups.append([(col, row) for col in range(0x14)])

    return groups


def side_column_wipe_groups():
    # Ghidra FUN_1000_5f60: vänster/höger kolumnpar in mot mitten.
    groups = []
    left = 0
    right = 0x13

    while left <= right:
        group = []

        for row in range(0x0D):
            group.append((left, row))
            group.append((right, row))

        # när left == right ska mittkolumnen inte dubbleras
        clean = []
        seen = set()
        for cell in group:
            if cell not in seen:
                seen.add(cell)
                clean.append(cell)

        groups.append(clean)

        left += 1
        right -= 1

    return groups


LEVEL_COMPLETE_WIPE_GROUPS = [
    spiral_wipe_groups(),
    alternating_row_wipe_groups(),
    side_column_wipe_groups(),
]

# Delay per steg från originalrutinerna:
# 5e38/5eed använder FUN_1000_a694(0x32), 5f60 använder FUN_1000_a694(0x1e).
LEVEL_COMPLETE_WIPE_STEP_MS = [50, 50, 30]


def draw_level_complete_wipe(surface, now, start_time, mode):
    mode = max(0, min(mode, len(LEVEL_COMPLETE_WIPE_GROUPS) - 1))
    groups = LEVEL_COMPLETE_WIPE_GROUPS[mode]
    step_ms = LEVEL_COMPLETE_WIPE_STEP_MS[mode]

    elapsed = max(0, now - start_time)
    visible_groups = min(len(groups), elapsed // step_ms + 1)

    for group in groups[:visible_groups]:
        for col, row in group:
            pygame.draw.rect(
                surface,
                (0, 0, 0),
                (col * TILE, row * TILE, TILE, TILE),
            )

    return elapsed >= len(groups) * step_ms


def begin_level_complete_transition():
    global level_complete_transition, level_complete_transition_start
    global level_complete_transition_target, level_complete_transition_mode

    if level_complete_transition:
        return

    clear_held_direction()

    level_complete_transition = True
    level_complete_transition_start = pygame.time.get_ticks()
    level_complete_transition_target = level_index + 1
    level_complete_transition_mode = random.randrange(len(LEVEL_COMPLETE_WIPE_GROUPS))


def finish_level_complete_transition():
    global level_index, level_complete_transition
    global level_complete_transition_start, level_complete_transition_target
    global level_complete_transition_mode

    target = level_complete_transition_target

    level_complete_transition = False
    level_complete_transition_start = 0
    level_complete_transition_target = 0
    level_complete_transition_mode = 0

    # Prövbane-demot/preview ska aldrig fortsätta till bana 1 av sig självt.
    # Originalflödet är intro -> hjälp -> topplista -> demo -> intro igen
    # tills spelaren trycker en tangent.
    if demo_mode:
        finish_demo_to_intro()
        return

    if demo_campaign_mode:
        current_display = visible_level_number()

        if current_display >= 10:
            start_game_complete_sequence()
            return

        level_index = demo_display_to_real_level(current_display + 1)
        load_level(level_index)
        return

    if target >= level_count:
        start_game_complete_sequence()
        return

    level_index = target
    load_level(level_index)


def begin_startup_close(target="game"):
    global startup_closing, startup_closing_start, startup_close_target

    if not startup_closing:
        startup_closing = True
        startup_closing_start = pygame.time.get_ticks()
        startup_close_target = target


def load_demo_macro():
    path = game_file_path(MACRO_FILE) if "game_file_path" in globals() else Path(MACRO_FILE)

    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return []

    return [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw) - 1, 2)]


def start_intro_sequence():
    global startup_sequence, startup_start_time, startup_closing, startup_closing_start, startup_close_target
    global demo_mode, demo_closing, demo_closing_start, demo_macro_index, demo_end_time

    startup_sequence = True
    startup_start_time = pygame.time.get_ticks()
    startup_closing = False
    startup_closing_start = 0
    startup_close_target = "demo"

    demo_mode = False
    demo_closing = False
    demo_closing_start = 0
    demo_macro_index = 0
    demo_end_time = 0

    stop_music_playback()
    clear_held_direction()


def start_demo_mode():
    global demo_mode, demo_macro, demo_macro_index, demo_next_step_time
    global demo_closing, demo_closing_start, demo_end_time
    global startup_sequence, startup_closing
    global level_index, lives

    startup_sequence = False
    startup_closing = False

    demo_mode = True
    demo_macro = load_demo_macro()
    demo_macro_index = 0
    demo_next_step_time = pygame.time.get_ticks()
    demo_closing = False
    demo_closing_start = 0
    demo_end_time = 0

    level_index = PRACTICE_LEVEL_INDEX
    lives = MAX_LIVES
    load_level(level_index)
    clear_held_direction()


def start_real_game_from_intro():
    global startup_sequence, startup_closing
    global demo_mode, demo_closing
    global level_index, lives

    startup_sequence = False
    startup_closing = False
    demo_mode = False
    demo_closing = False

    level_index = FIRST_REAL_LEVEL_INDEX
    lives = MAX_LIVES
    load_level(level_index)
    clear_held_direction()


def start_demo_campaign():
    global startup_sequence, startup_closing
    global demo_mode, demo_closing
    global level_index, lives

    startup_sequence = False
    startup_closing = False
    demo_mode = False
    demo_closing = False

    level_index = PRACTICE_LEVEL_INDEX
    lives = MAX_LIVES
    load_level(level_index)
    clear_held_direction()


def begin_demo_close():
    global demo_closing, demo_closing_start

    if not demo_closing:
        demo_closing = True
        demo_closing_start = pygame.time.get_ticks()


def finish_demo_to_intro():
    if demo_only_mode:
        start_demo_mode()
    else:
        start_intro_sequence()


def demo_key_to_action(code):
    # Originalets MACRO består av 16-bitars tangentkoder.
    # 0x100 är "ingen aktiv tangent"/vänta.
    if code in (0, 0x100):
        return

    if code == 0x148:
        do_direction(0, -1)
    elif code == 0x14b:
        do_direction(-1, 0)
    elif code == 0x14d:
        do_direction(1, 0)
    elif code == 0x150:
        do_direction(0, 1)
    elif code == 0x0a:
        dig(-1, 0)
    elif code == 0x0b:
        dig(1, 0)
    elif code == 0x0c:
        dig(0, 1)
    elif code == 0x0d:
        dig(0, -1)


def update_demo(now):
    global demo_macro_index, demo_next_step_time, demo_end_time

    if not demo_mode or demo_closing:
        return

    if not alive:
        if demo_end_time == 0:
            demo_end_time = now + DEMO_AFTER_END_MS
        elif now >= demo_end_time:
            finish_demo_to_intro()
        return

    if now < demo_next_step_time:
        return

    # Originalets demo-loop gör ett helt spelsteg per MACRO-värde:
    # gravitation/fiender först, sedan läses nästa inspelade tangent.
    update_pending_explosions()

    if alive:
        check_enemy_contact()

    if alive and not bomb_exploded_this_frame:
        update_gravity()

    if alive:
        update_enemies()

    if alive:
        check_enemy_contact()

    if demo_macro_index < len(demo_macro):
        code = demo_macro[demo_macro_index]
        demo_macro_index += 1
        demo_key_to_action(code)
    else:
        if demo_end_time == 0:
            demo_end_time = now + DEMO_AFTER_END_MS

    demo_next_step_time = now + DEMO_STEP_MS

    # Om MACRO har tagit slut eller bara nollor återstår, låt demo visas kort
    # och gå sedan tillbaka till intro-loopen.
    if demo_macro_index >= len(demo_macro) and demo_end_time == 0:
        demo_end_time = now + DEMO_AFTER_END_MS

    if demo_end_time and now >= demo_end_time:
        finish_demo_to_intro()


def draw_startup_sequence(surface, now):
    elapsed = now - startup_start_time

    top_end = STARTUP_TOP_MS
    intro_only_end = top_end + STARTUP_INTRO_ONLY_MS
    intro_names_end = intro_only_end + STARTUP_INTRO_NAMES_MS
    help_1_end = intro_names_end + STARTUP_HELP_1_MS
    help_2_end = help_1_end + STARTUP_HELP_2_MS
    top_ten_end = help_2_end + STARTUP_TOPTEN_MS

    if elapsed < top_end:
        blit_pic_screen(surface, startup_surfaces.get("top"))
    elif elapsed < intro_names_end:
        blit_pic_screen(surface, startup_surfaces.get("intro"))

        if demo_campaign_mode and demo_badge_surface:
            base_x = (surface.get_width() - SCREEN_W) // 2
            surface.blit(demo_badge_surface, (base_x + DEMO_BADGE_X, DEMO_BADGE_Y))

        if elapsed >= intro_only_end:
            names = startup_surfaces.get("names")
            if names:
                blit_startup_names_with_shadow(surface, names)
    elif elapsed < help_1_end:
        draw_startup_help_1(surface)
    elif elapsed < help_2_end:
        draw_startup_help_2(surface)
    elif not demo_campaign_mode and elapsed < top_ten_end:
        draw_startup_topten(surface)
    else:
        if not demo_campaign_mode:
            draw_startup_topten(surface)

        if not startup_closing:
            begin_startup_close("demo")

    if startup_closing:
        draw_side_wipe(surface, now, startup_closing_start, STARTUP_CLOSE_MS)


def finish_startup_sequence():
    global startup_sequence, startup_closing

    if demo_campaign_mode:
        start_demo_campaign()
    elif startup_close_target == "game":
        start_real_game_from_intro()
    else:
        start_demo_mode()


def current_level_code():
    return LEVEL_TO_CODE.get(visible_level_number())


def draw_level_code_intro(surface, now):
    surface.fill((0, 0, 0))

    code = current_level_code()

    if not code:
        finish_level_code_intro()
        return

    label = "Kod för denna bana är:"
    label_rect = draw_centered_text(
        surface,
        font,
        label,
        SCREEN_H // 2 - 22,
        (255, 255, 255),
    )

    # Samma typ av färgflimmer som titeln: slumpad DOS/EGA-färg.
    dos_text_colors = [
        (0, 0, 0),
        (0, 0, 170),
        (0, 170, 0),
        (0, 170, 170),
        (170, 0, 0),
        (170, 0, 170),
        (170, 85, 0),
        (170, 170, 170),
        (85, 85, 85),
        (85, 85, 255),
        (85, 255, 85),
        (85, 255, 255),
        (255, 85, 85),
        (255, 85, 255),
        (255, 255, 85),
        (255, 255, 255),
    ]

    color = dos_text_colors[random.randrange(16)]

    code_rect = draw_centered_text(
        surface,
        font,
        code,
        SCREEN_H // 2 - 2,
        color,
    )

    if not level_code_intro_closing:
        return

    elapsed = now - level_code_intro_closing_start
    progress = max(0.0, min(1.0, elapsed / LEVEL_CODE_INTRO_CLOSE_MS))

    for rect in [label_rect, code_rect]:
        half_w = rect.width // 2
        wipe_w = int(half_w * progress) + 1

        pygame.draw.rect(
            surface,
            (0, 0, 0),
            (rect.left, rect.top, wipe_w, rect.height),
        )
        pygame.draw.rect(
            surface,
            (0, 0, 0),
            (rect.right - wipe_w, rect.top, wipe_w, rect.height),
        )


def begin_level_code_intro_close():
    global level_code_intro_closing, level_code_intro_closing_start

    if not level_code_intro_closing:
        level_code_intro_closing = True
        level_code_intro_closing_start = pygame.time.get_ticks()


def finish_level_code_intro():
    global level_code_intro, level_code_intro_closing
    global level_intro, level_intro_start_time, level_intro_closing, level_intro_closing_start

    level_code_intro = False
    level_code_intro_closing = False

    level_intro = True
    level_intro_start_time = pygame.time.get_ticks()
    level_intro_closing = False
    level_intro_closing_start = 0

    clear_held_direction()




def remember_presented_canvas(surface):
    global last_presented_canvas
    last_presented_canvas = surface.copy()


def start_game_complete_sequence():
    global game_complete_sequence, game_complete_start_time, game_complete_snapshot
    global game_complete_closing, game_complete_closing_start, game_complete_score_level
    global held_dx, held_dy

    game_complete_sequence = True
    game_complete_start_time = pygame.time.get_ticks()
    game_complete_snapshot = None
    game_complete_closing = False
    game_complete_closing_start = 0

    # level_index har redan ökats förbi sista banan här.
    # Spara sista riktiga banans nummer till tio-i-topp.
    game_complete_score_level = max(FIRST_REAL_LEVEL_INDEX, level_count - 1)
    stop_music_playback()
    clear_held_direction()


def begin_game_complete_close():
    global game_complete_closing, game_complete_closing_start

    if game_complete_closing:
        return

    game_complete_closing = True
    game_complete_closing_start = pygame.time.get_ticks()
    clear_held_direction()


def finish_game_complete_to_highscore():
    global game_complete_sequence, game_complete_closing
    global game_complete_start_time, game_complete_snapshot

    game_complete_sequence = False
    game_complete_closing = False
    game_complete_start_time = 0
    game_complete_snapshot = None

    if demo_campaign_mode:
        start_intro_sequence()
        return

    begin_highscore_entry_force(game_complete_score_level)


def draw_game_complete_sequence(surface, now):
    # Efter sista banan visas EOF.PIC direkt.
    eof = startup_surfaces.get("eof")
    blit_pic_screen(surface, eof)

    if demo_campaign_mode:
        draw_centered_text(surface, font, "DU KLARADE DET!", 186, (255, 255, 85))

    # Efter tangent körs samma block/wipe-fade ut från bilden.
    if game_complete_closing:
        draw_original_wipe(surface, now, game_complete_closing_start, GAME_COMPLETE_CLOSE_MS)
        return now - game_complete_closing_start >= GAME_COMPLETE_CLOSE_MS

    return False

args = parse_cli_args()
sound_mode = args.sound
debug_mode = args.debug
demo_campaign_mode = args.demo
demo_only_mode = False
music_file = args.music
music_mode = args.music_mode
# Standard är musik av. F4 slår på den inne i spelet; --music-on kan användas för test.
music_enabled = bool(args.music_on) and not args.no_music
music_volume = max(0.0, min(1.0, args.music_volume))
fullscreen_enabled = bool(args.fullscreen)

pygame.mixer.pre_init(AUDIO_RATE, -16, 1, 256)
pygame.init()
init_sound()
pygame.key.set_repeat(0)
init_joysticks()

def draw_gameplay_canvas(surface, now, draw_overlays=True):
    view_tiles_x = max(VIEW_W, min(MAP_W, math.ceil(surface.get_width() / TILE)))
    cam_x, cam_y = get_camera(view_tiles_x)

    surface.fill((0, 0, 0))

    for sy in range(VIEW_H):
        for sx in range(view_tiles_x):
            wx = cam_x + sx
            wy = cam_y + sy

            if not (0 <= wx < MAP_W and 0 <= wy < MAP_H):
                continue

            ch = grid[wy][wx]
            draw_tile(surface, ch, sx, sy, now, wx, wy)

    draw_explosions(surface, cam_x, cam_y, now, view_tiles_x)

    if DEBUG_TILE_LETTERS:
        draw_tile_debug_overlay(surface, font, cam_x, cam_y, view_tiles_x)

    px = player_x - cam_x
    py = player_y - cam_y

    draw_player(surface, px, py, now)
    draw_hud(surface)

    if demo_mode and demo_badge_surface:
        bx = surface.get_width() - demo_badge_surface.get_width() - 8
        by = 8
        surface.blit(demo_badge_surface, (bx, by))

    if not draw_overlays:
        return

    # Status/debug-meddelanden skrivs bara till CMD via set_message().
    # De ska inte ritas på spelbilden.

    if code_mode:
        pygame.draw.rect(surface, (20, 20, 20), (35, 80, 250, 60))

        draw_original_font_text(surface, "Skriv kod + Enter", 50, 92, (255, 255, 255))
        draw_original_font_text(surface, code_text, 135, 115, (255, 255, 0))

    if level_intro and not code_mode:
        draw_level_intro(surface, now)

    if death_fade_active:
        draw_side_wipe(surface, now, death_fade_start, DEATH_FADE_MS)

    if demo_mode and demo_closing:
        draw_side_wipe(surface, now, demo_closing_start, STARTUP_CLOSE_MS)


def compute_render_layout():
    """Returnera (logical_w, dest_rect) med pixel-perfect keep-aspect.

    Den här versionen använder bara EN skalfaktor och gör den dessutom
    heltalig. Då kan bilden inte dras ut i X-led eller Y-led av misstag.

    På bred skärm:
      - skalan väljs från höjden
      - logical_w blir bredare än 320
      - fler kartpixlar ritas åt sidorna

    På smalare skärm:
      - originalvyn 320x224 används
      - svarta kanter läggs där fönstret inte matchar
    """
    if window is None:
        return SCREEN_W, pygame.Rect(0, 0, SCREEN_W * SCALE, SCREEN_H * SCALE)

    win_w, win_h = window.get_size()

    if win_w <= 0 or win_h <= 0:
        return SCREEN_W, pygame.Rect(0, 0, SCREEN_W * SCALE, SCREEN_H * SCALE)

    base_aspect = SCREEN_W / SCREEN_H
    win_aspect = win_w / win_h

    # Pixel-perfect heltalsskala. Detta är viktigare än att fylla varje pixel
    # på skärmen, eftersom icke-heltalsskala kan se ut som stretch/blurr.
    if win_aspect > base_aspect:
        # Bredare än originalet: fyll så mycket av höjden som möjligt och
        # använd extra bredd till mer spelvy.
        scale = max(1, int(math.floor(win_h / SCREEN_H)))
        logical_w = int(math.floor(win_w / scale))
    else:
        # Smalare: behåll originalbredden 320 och centrera.
        scale = max(1, int(math.floor(win_w / SCREEN_W)))
        logical_w = SCREEN_W

    logical_w = max(SCREEN_W, logical_w)
    logical_w = min(MAP_W * TILE, logical_w)

    dest_w = logical_w * scale
    dest_h = SCREEN_H * scale

    # Om en extremt liten/udda fönsterstorlek ändå gör att bilden inte får
    # plats, gå ner en skala.
    while scale > 1 and (dest_w > win_w or dest_h > win_h):
        scale -= 1
        if win_aspect > base_aspect:
            logical_w = int(math.floor(win_w / scale))
            logical_w = max(SCREEN_W, min(MAP_W * TILE, logical_w))
        else:
            logical_w = SCREEN_W
        dest_w = logical_w * scale
        dest_h = SCREEN_H * scale

    dest_x = (win_w - dest_w) // 2
    dest_y = (win_h - dest_h) // 2
    return logical_w, pygame.Rect(dest_x, dest_y, dest_w, dest_h)

def compute_canvas_width_for_window():
    logical_w, _rect = compute_render_layout()
    return logical_w


def ensure_canvas_size():
    global canvas

    target_w = compute_canvas_width_for_window()
    target_size = (target_w, SCREEN_H)

    if canvas is None or canvas.get_size() != target_size:
        canvas = pygame.Surface(target_size)

    return canvas


def present_canvas(surface):
    window.fill((0, 0, 0))

    _logical_w, dest_rect = compute_render_layout()

    # Viktigt: skala till en rect som beräknats med samma scale i X/Y.
    # Det ger "keep aspect ratio" och bredare vy, inte utdragen 320-bild.
    scaled = pygame.transform.scale(surface, (dest_rect.w, dest_rect.h))
    window.blit(scaled, dest_rect.topleft)
    pygame.display.flip()


def set_display_mode(fullscreen=None, size=None):
    global window, fullscreen_enabled, windowed_size

    if fullscreen is not None:
        fullscreen_enabled = bool(fullscreen)

    if size is not None:
        w, h = size
        windowed_size = (max(SCREEN_W, int(w)), max(SCREEN_H, int(h)))

    if fullscreen_enabled:
        info = pygame.display.Info()
        window = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
    else:
        window = pygame.display.set_mode(windowed_size, pygame.RESIZABLE)

    ensure_canvas_size()
    pygame.display.set_caption("Bomber och Bumlingar Engine")


def toggle_fullscreen():
    set_display_mode(not fullscreen_enabled)
    set_message("Fullscreen: på" if fullscreen_enabled else "Fullscreen: av")


set_display_mode(fullscreen_enabled)

pygame.display.set_caption("Bomber och Bumlingar Engine")

clock = pygame.time.Clock()
font = pygame.font.SysFont("Consolas", 16, bold=True)
intro_font = pygame.font.SysFont("Consolas", 14, bold=True)
intro_help_font = pygame.font.SysFont("Consolas", 10, bold=True)
hud_font = pygame.font.SysFont("Consolas", 12, bold=True)

load_original_bitmap_font()
load_graphics()
load_level(PRACTICE_LEVEL_INDEX)
level_intro = False

start_intro_sequence()

running = True

while running:
    now = pygame.time.get_ticks()
    update_music(now)
    ensure_canvas_size()
    bomb_exploded_this_frame = False

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

        if e.type == pygame.VIDEORESIZE and not fullscreen_enabled:
            set_display_mode(False, (e.w, e.h))
            continue

        if e.type == pygame.JOYDEVICEADDED:
            add_joystick_device(e.device_index)
            continue

        if e.type == pygame.JOYDEVICEREMOVED:
            remove_joystick_device(e.instance_id)
            continue

        if e.type in (pygame.JOYBUTTONDOWN, pygame.JOYAXISMOTION, pygame.JOYHATMOTION):
            if handle_joystick_remap_event(e):
                continue

        if e.type == pygame.JOYBUTTONDOWN:
            if handle_joystick_button_action(e, now):
                continue

        if e.type == pygame.KEYDOWN and joystick_remap_active:
            if e.key == pygame.K_ESCAPE:
                cancel_joystick_remap()
                continue

        if e.type == pygame.KEYUP:
            if not startup_sequence and not demo_mode and not topten_screen and not level_intro and e.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
                update_held_direction_from_keyboard(now)

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and (e.mod & pygame.KMOD_ALT)):
                toggle_fullscreen()
                continue

            if highscore_entry:
                handle_highscore_key(e)
                continue

            if topten_screen:
                hide_topten_screen()
                continue

            if game_complete_sequence:
                # EOF.PIC stannar tills valfri tangent trycks.
                # Tangenten startar wipe/fade; efter den visas namn-inmatning.
                begin_game_complete_close()
                continue

            if level_complete_transition:
                continue

            if startup_sequence:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif demo_campaign_mode or demo_only_mode:
                    begin_startup_close("demo")
                else:
                    begin_startup_close("game")
                continue

            if demo_mode:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif demo_only_mode:
                    # I rent demo-läge ska valfri tangent inte starta spelbar bana.
                    # Starta bara om demo så man kan fortsätta testa loopen.
                    start_demo_mode()
                else:
                    begin_demo_close()
                continue

            if code_mode:
                handle_code_key(e)
                continue

            if e.key == pygame.K_ESCAPE:
                running = False
                continue

            elif e.key == pygame.K_F1:
                if not demo_campaign_mode:
                    show_topten_screen()
                continue

            if level_code_intro:
                begin_level_code_intro_close()
                continue

            if level_intro:
                begin_level_intro_close()
                continue

            if death_waiting_for_key:
                begin_death_fade()
                continue

            elif e.key == pygame.K_F10 or e.key == pygame.K_r:
                restart_level()

            elif debug_mode and e.key == pygame.K_n:
                # Debug/snabbhopp ska använda samma original-lika wipe
                # som när spelaren klarar banan via sista dörren.
                play_game_sound("exit", min_interval_ms=250, force=True)
                begin_level_complete_transition()

            elif e.key == pygame.K_F6:
                start_code_mode()

            elif e.key == pygame.K_F2:
                sound_enabled = not sound_enabled
                # Originalet togglar bara ljudflaggan, utan extra ljud.
                set_message("Ljud: på" if sound_enabled else "Ljud: av")

            elif e.key == pygame.K_F3:
                cycle_sound_mode()

            elif e.key == pygame.K_F4:
                toggle_music()

            elif e.key == pygame.K_F5:
                start_joystick_remap()

            elif debug_mode and e.key in (pygame.K_F9, pygame.K_9):
                DEBUG_TILE_LETTERS = not DEBUG_TILE_LETTERS
                set_message("Tile-debug: på" if DEBUG_TILE_LETTERS else "Tile-debug: av")

            if alive:
                dx = 0
                dy = 0

                if e.key == pygame.K_LEFT:
                    dx = -1
                elif e.key == pygame.K_RIGHT:
                    dx = 1
                elif e.key == pygame.K_UP:
                    dy = -1
                elif e.key == pygame.K_DOWN:
                    dy = 1

                if dx != 0 or dy != 0:
                    do_direction(dx, dy)

                    set_held_direction(dx, dy, now)

    if level_complete_transition:
        draw_gameplay_canvas(canvas, now, draw_overlays=False)
        done = draw_level_complete_wipe(
            canvas,
            now,
            level_complete_transition_start,
            level_complete_transition_mode,
        )

        remember_presented_canvas(canvas)
        present_canvas(canvas)
        clock.tick(60)

        if done:
            finish_level_complete_transition()

        continue

    if not game_complete_sequence and startup_sequence and startup_closing and now - startup_closing_start >= STARTUP_CLOSE_MS:
        finish_startup_sequence()

    if not game_complete_sequence and demo_mode and demo_closing and now - demo_closing_start >= STARTUP_CLOSE_MS:
        if demo_only_mode:
            start_demo_mode()
        else:
            start_real_game_from_intro()

    if not game_complete_sequence and demo_mode and not demo_closing:
        update_demo(now)

    if not game_complete_sequence and death_fade_active and now - death_fade_start >= DEATH_FADE_MS:
        if lives <= 0:
            restart_game_from_beginning()
        else:
            restart_level()
        continue

    if not game_complete_sequence and level_code_intro and level_code_intro_closing and now - level_code_intro_closing_start >= LEVEL_CODE_INTRO_CLOSE_MS:
        finish_level_code_intro()

    if not game_complete_sequence and not startup_sequence and not level_code_intro and level_intro and level_intro_closing and now - level_intro_closing_start >= LEVEL_INTRO_CLOSE_MS:
        finish_level_intro()

    if gameplay_input_active():
        update_joystick_input(now)

    if gameplay_input_active() and (held_dx != 0 or held_dy != 0):
        if held_source == "joystick":
            jdx, jdy = joystick_direction()
            still_pressed = (jdx == held_dx and jdy == held_dy)
        else:
            pressed = pygame.key.get_pressed()
            still_pressed = (
                (held_dx == -1 and pressed[pygame.K_LEFT]) or
                (held_dx == 1 and pressed[pygame.K_RIGHT]) or
                (held_dy == -1 and pressed[pygame.K_UP]) or
                (held_dy == 1 and pressed[pygame.K_DOWN])
            )

        if still_pressed and now >= next_move_time:
            do_direction(held_dx, held_dy, force_dig=(held_source == "joystick" and joystick_dig_pressed()))
            next_move_time = now + MOVE_REPEAT_MS

        if not still_pressed:
            clear_held_direction()

    if not game_complete_sequence and not demo_mode and not startup_sequence and not highscore_entry and not topten_screen and not level_code_intro and not code_mode and not level_intro and not death_waiting_for_key:
        update_pending_explosions()

    if alive and not game_complete_sequence and not demo_mode and not startup_sequence and not highscore_entry and not topten_screen and not level_code_intro and not code_mode and not level_intro:
        check_enemy_contact()

    if alive and not game_complete_sequence and not demo_mode and not bomb_exploded_this_frame and not startup_sequence and not highscore_entry and not topten_screen and not level_code_intro and not code_mode and not level_intro and now - fall_timer > FALL_MS:
        update_gravity()
        fall_timer = now

    if alive and not demo_mode and not startup_sequence and not highscore_entry and not topten_screen and not level_code_intro and not code_mode and not level_intro and now - enemy_timer > ENEMY_MS:
        update_enemies()
        enemy_timer = now

    if game_complete_sequence:
        done = draw_game_complete_sequence(canvas, now)
        remember_presented_canvas(canvas)

        present_canvas(canvas)
        clock.tick(60)

        if done:
            finish_game_complete_to_highscore()

        continue

    if startup_sequence:
        draw_startup_sequence(canvas, now)

        remember_presented_canvas(canvas)
        present_canvas(canvas)
        clock.tick(60)
        continue

    if level_code_intro:
        draw_level_code_intro(canvas, now)

        remember_presented_canvas(canvas)
        present_canvas(canvas)
        clock.tick(60)
        continue

    if highscore_entry:
        draw_highscore_entry(canvas, now)

        remember_presented_canvas(canvas)
        present_canvas(canvas)
        clock.tick(60)
        continue

    if topten_screen:
        draw_startup_topten(canvas)

        remember_presented_canvas(canvas)
        present_canvas(canvas)
        clock.tick(60)
        continue

    draw_gameplay_canvas(canvas, now)

    remember_presented_canvas(canvas)
    present_canvas(canvas)
    clock.tick(60)

pygame.quit()
