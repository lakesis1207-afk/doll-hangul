#!/usr/bin/env python3
"""인천공항 자기부상열차 릴스 (1080x1920, 30fps) 자동 제작 스크립트.

- 사진/영상 합성 + 한글 자막(PNG 오버레이) + 직접 합성한 오리지널 BGM(저작권 무관)
- 영상 클립은 1.5배속
사용:  python3 build_reels.py <uploads_dir> <font_jua.ttf> <out_dir>
"""
import math, os, re, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

UP, JUA, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
W, H, FPS, SPEED = 1080, 1920, 30, 1.5
WORK = os.path.join(OUT, "work")
os.makedirs(WORK, exist_ok=True)

IMG = {i: os.path.join(UP, f) for i, f in enumerate([
    "f98b06ac-image.jpg", "1c82e546-image.jpg", "92f250c8-image.jpg",
    "d4ea6be0-image.jpg", "49c35db8-image.jpg", "5988bdb4-image.png",
    "3df1bd24-image.jpg", "44bef7a5-image.jpg", "376671f1-image.jpg"], 1)}
VID = {
    "train": os.path.join(UP, "13126a76-2026_10_21_16_51_1.mp4"),    # 2번째: 열차 탑승
    "arrive": os.path.join(UP, "f3e97ce0-2026_10_21_16_51.mp4"),    # 3번째: 터미널 도착
    "media": os.path.join(UP, "d3de28d9-20260913_152957.mp4"),      # 8번째: 그림 출력 영상
    "robot": os.path.join(UP, "6e314585-2026_10_21_16_51_2.mp4"),   # 9번째: 로봇 초상화
}

WHITE, YELLOW, PINK, MINT = (255, 255, 255), (255, 232, 94), (255, 170, 214), (160, 255, 225)
LINE = [("", 0, WHITE)]

# ---- 구성표 -----------------------------------------------------------
# kind: photo | video | end ; dur(초, 영상은 1.5배속 후 길이) ; stages: (시작, 끝, [(글, 크기, 색)...])
SEGS = [
    dict(kind="photo", src=1, dur=5.2, badge="🚝 용유역 출발", stages=[
        (0.2, 2.9, [("이번 주말엔 뭐하지? 🤔", 70, WHITE), ("자기부상열차 타고", 68, YELLOW), ("인천공항에서 놀기♡", 80, PINK)]),
        (3.0, 5.2, [("🅿️ 주차 TIP", 72, YELLOW), ("네스트호텔 근처 주차 가능!", 56, WHITE), ("주차 후 용유역에서 출발~", 56, WHITE)])]),
    dict(kind="video", src="train", dur=7.1667 / SPEED, stages=[
        (0.2, 4.6, [("자기부상열차 타고 슝~ 🚝", 64, WHITE), ("창밖 풍경이 정말 예뻐요", 52, YELLOW)])]),
    dict(kind="video", src="arrive", dur=3.9 / SPEED, stages=[
        (0.1, 2.5, [("도착! 인천공항 제1터미널 ✈️", 56, YELLOW)])]),
    dict(kind="photo", src=2, dur=2.7, badge="아이랑 인천공항 놀기 1. 미디어아트", stages=[
        (0.2, 2.7, [("반짝반짝 별빛 속으로 ✨", 62, WHITE), ("코끼리가 나타났어요!", 58, YELLOW)])]),
    dict(kind="photo", src=3, dur=2.7, badge="1. 미디어아트", stages=[
        (0.2, 2.7, [("코끼리랑 인사하는 아이들 🐘", 56, WHITE)])]),
    dict(kind="photo", src=4, dur=3.2, badge="2. 그림 그리기", stages=[
        (0.2, 3.2, [("아이가 직접 색칠한 비행기 ✈️", 54, WHITE), ("엄마 아빠 하트도 쏙 💗", 54, YELLOW)])]),
    dict(kind="photo", src=5, dur=2.7, badge="2. 그림 그리기", stages=[
        (0.2, 2.7, [("그림을 스캔하면...", 62, WHITE), ("두근두근 👀", 58, YELLOW)])]),
    dict(kind="video", src="media", dur=6.0, trim=9.0, badge="2. 그림 그리기", stages=[
        (0.2, 5.9, [("짜잔! 내 그림이 영상으로 ✨", 56, YELLOW)])]),
    dict(kind="video", src="robot", dur=11.3 / SPEED, badge="3. 로봇 초상화", stages=[
        (0.2, 7.4, [("로봇이 얼굴을 보고", 60, WHITE), ("쓱쓱 그려줘요 🤖", 62, YELLOW)])]),
    dict(kind="photo", src=6, dur=3.0, badge="3. 로봇 초상화", stages=[
        (0.2, 3.0, [("이렇게 그려줬어요! ✨", 62, WHITE), ("신기하죠?", 56, YELLOW)])]),
    dict(kind="photo", src=7, dur=2.9, badge="4. K-컬처 체험", stages=[
        (0.2, 2.9, [("K-컬처 존에서 놀기 📸", 60, WHITE), ("모자 쓰고 변신!", 56, YELLOW)])]),
    dict(kind="photo", src=8, dur=2.9, badge="4. K-컬처 체험", stages=[
        (0.2, 2.9, [("찰칵! 가족사진 추억 남기기 💜", 52, WHITE)])]),
    dict(kind="photo", src=9, dur=3.2, badge="5. 빙글빙글", stages=[
        (0.2, 3.2, [("의자에 앉아 빙그르르~ 🌀", 58, WHITE), ("은근히 재밌어요!", 54, YELLOW)])]),
    dict(kind="end", src=2, dur=6.0, stages=[
        (0.2, 3.0, [("공항에서 비행기만", 66, WHITE), ("타지 마세요~", 72, YELLOW), ("아이와 충분히 재밌게", 62, WHITE), ("놀 수 있어요^^", 70, PINK)]),
        (3.1, 6.0, [("이번 주말", 74, YELLOW), ("자기부상열차 타고", 66, WHITE), ("인천공항 어떠세요? ✈️♡", 62, PINK)])]),
]
TOTAL = sum(s["dur"] for s in SEGS)

# ---- 자막 PNG ---------------------------------------------------------
RE_EMOJI = re.compile("([\U0001F000-\U0001FFFF☀-➿♡♥][️]?)")
SWAP = {"♡": "💗", "♥": "❤"}


def render_line(text, size, color, maxw=940):
    for k, v in SWAP.items():
        text = text.replace(k, v)
    while True:
        f = ImageFont.truetype(JUA, size)
        ef = ImageFont.truetype(EMOJI, 109)
        pieces, x = [], 0
        for tok in [t for t in RE_EMOJI.split(text) if t]:
            if RE_EMOJI.fullmatch(tok):
                im = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
                ImageDraw.Draw(im).text((0, 0), tok.replace("️", ""), font=ef, embedded_color=True)
                s = size * 1.05 / 128
                im = im.resize((int(136 * s), int(128 * s)), Image.LANCZOS)
                pieces.append(("e", im, x)); x += im.width + 4
            else:
                wd = f.getlength(tok)
                pieces.append(("t", tok, x)); x += wd
        if x <= maxw or size <= 30:
            break
        size -= 2
    pad = 24
    img = Image.new("RGBA", (int(x) + pad * 2, int(size * 1.7) + pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for kind, v, px in pieces:
        if kind == "t":
            # 그림자 + 두꺼운 외곽선 + 본문
            d.text((px + pad + 3, pad + 7), v, font=f, fill=(20, 10, 40, 150), stroke_width=10, stroke_fill=(20, 10, 40, 150))
            d.text((px + pad, pad), v, font=f, fill=color, stroke_width=9, stroke_fill=(43, 27, 77, 255))
        else:
            img.alpha_composite(v, (int(px + pad), int(pad + size * 0.08)))
    return img


def render_caption(lines, path, badge=None):
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rendered = [render_line(t, s, c) for t, s, c in lines]
    total = sum(r.height - 20 for r in rendered)
    y = 1430 - total // 2          # 인스타 하단 UI(≈ 380px)를 피한 위치
    for r in rendered:
        canvas.alpha_composite(r, ((W - r.width) // 2, y))
        y += r.height - 20
    return canvas


def render_badge(text):
    f = ImageFont.truetype(JUA, 44)
    ef_text = render_line(text, 44, WHITE, 900)
    w, h = ef_text.width + 50, ef_text.height + 6
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0 = (W - w) // 2
    d.rounded_rectangle((x0, 300, x0 + w, 300 + h), radius=h // 2, fill=(255, 92, 160, 235))
    im.alpha_composite(ef_text, (x0 + 25 - 24, 300 + 3 - 6))
    return im


# ---- 배경/전경 합성 (사진) -----------------------------------------------
def compose(path, dim=0.0, blur=38):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    s = max(W / im.width, H / im.height)
    bg = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l, t = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(blur))
    bg = Image.eval(bg, lambda v: int(v * (0.78 - dim)))
    s = min(W / im.width, H / im.height)
    fg = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2 - (60 if fg.height < 1300 else 0)))
    return bg


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd)); print(r.stderr[-2500:]); sys.exit(1)


def caption_inputs(seg, idx):
    """자막(PNG) 입력 인자와 필터 조각 생성"""
    args, filt, last = [], [], "[base]"
    n = 1
    items = []
    if seg.get("badge"):
        p = f"{WORK}/b{idx}.png"; render_badge(seg["badge"]).save(p)
        items.append((p, 0.1, seg["dur"] - 0.05))
    for k, (a, b, lines) in enumerate(seg["stages"]):
        p = f"{WORK}/c{idx}_{k}.png"; render_caption(lines, p).save(p)
        items.append((p, a, min(b, seg["dur"] - 0.05)))
    for p, a, b in items:
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{seg['dur']:.3f}", "-i", p]
        filt.append(f"[{n}:v]format=rgba,fade=t=in:st={a:.2f}:d=0.3:alpha=1,fade=t=out:st={b-0.25:.2f}:d=0.25:alpha=1[o{n}]")
        filt.append(f"{last}[o{n}]overlay=0:0:format=auto[v{n}]")
        last = f"[v{n}]"; n += 1
    return args, filt, last


ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]


def build_segment(i, seg):
    out = f"{WORK}/seg{i:02d}.mp4"
    d = seg["dur"]
    cap_args, cap_filt, last = caption_inputs(seg, i)
    if seg["kind"] in ("photo", "end"):
        still = f"{WORK}/still{i:02d}.png"
        compose(IMG[seg["src"]], dim=0.3 if seg["kind"] == "end" else 0.0,
                blur=60 if seg["kind"] == "end" else 38).save(still)
        zin = "min(1+0.0009*on,1.09)" if i % 2 == 0 else "max(1.09-0.0009*on,1)"
        base = (f"[0:v]scale={W*2}:{H*2}:flags=lanczos,zoompan=z='{zin}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d=1:s={W}x{H}:fps={FPS},format=yuv420p[base]")
        src = ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", still]
    else:
        trim = ["-t", f"{seg['trim']}"] if seg.get("trim") else []
        # 가로 영상은 흐린 배경 + 중앙 배치, 세로 영상은 꽉 채움 / 1.5배속
        base = (f"[0:v]setpts=PTS/{SPEED},fps={FPS},split[a][b];"
                f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:4,eq=brightness=-0.2[bg];"
                f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2-50,format=yuv420p[base]")
        src = trim + ["-i", VID[seg["src"]]]
    filt = ";".join([base] + cap_filt)
    cmd = ["ffmpeg", "-v", "error", "-y"] + src + cap_args + ["-filter_complex", filt, "-map", last,
                                                              "-t", f"{d:.3f}"] + ENC + [out]
    run(cmd)
    return out


# ---- 오리지널 BGM 합성 (저작권 무관) ---------------------------------------
SR = 44100
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)


def tone(f, dur, kind):
    t = np.arange(int(SR * dur)) / SR
    if kind == "marimba":
        y = np.sin(2*np.pi*f*t)*np.exp(-t*7) + 0.35*np.sin(2*np.pi*f*4*t)*np.exp(-t*22) + 0.1*np.sin(2*np.pi*f*10*t)*np.exp(-t*40)
    elif kind == "uke":
        y = sum(a*np.sin(2*np.pi*f*h*t)*np.exp(-t*d) for h, a, d in [(1, 1, 6), (2, .5, 8), (3, .3, 11), (4, .18, 14), (5, .1, 18)])
    else:  # bass
        y = np.sin(2*np.pi*f*t)*np.exp(-t*3.2) + 0.25*np.sin(2*np.pi*f*2*t)*np.exp(-t*6)
    a = np.minimum(1, t / 0.004)
    return y * a


def make_music(total, path):
    bpm = 120
    step = 60 / bpm / 2                       # 8분음표
    bars = int(math.ceil(total / (step * 8))) + 1
    n = int((bars * 8 * step + 3) * SR)
    mix = np.zeros(n)
    def add(sig, t0, g=1.0):
        i = int(t0 * SR); sig = sig[: max(0, n - i)]
        mix[i:i + len(sig)] += sig * g
    chords = [("C", ["C4", "E4", "G4"], "C2"), ("G", ["B3", "D4", "G4"], "G2"),
              ("Am", ["C4", "E4", "A4"], "A2"), ("F", ["C4", "F4", "A4"], "F2")]
    A = [["E5", 0, "G5", "E5", 0, "C5", "E5", "G5"], ["D5", 0, "G5", "D5", 0, "B4", "D5", "G5"],
         ["C5", 0, "E5", "C5", 0, "A4", "C5", "E5"], ["C5", 0, "F5", "E5", 0, "D5", "C5", "A4"]]
    B = [["G5", 0, "G5", "E5", "G5", "A5", "G5", "E5"], ["D5", "E5", "G5", 0, "B5", "G5", "D5", 0],
         ["E5", 0, "C5", "E5", "A5", 0, "G5", "E5"], ["A4", "C5", "F5", "E5", "C5", 0, "D5", "C5"]]
    rng = np.random.default_rng(7)
    for bar in range(bars):
        t0 = bar * 8 * step
        ci = bar % 4
        _, tri, root = chords[ci]
        last = bar == bars - 1
        if last:
            for nt in tri + ["C5"]:
                add(tone(hz(nt), 2.5, "uke"), t0, 0.16)
            add(tone(hz("C2"), 2.5, "bass"), t0, 0.5)
            add(tone(hz("C6"), 2.0, "marimba"), t0 + step, 0.25)
            continue
        # 베이스
        for k in (0, 3, 4, 6):
            add(tone(hz(root), 0.5, "bass"), t0 + k * step, 0.42)
        # 우쿨렐레 스트럼 (오프비트)
        for k in (1, 3, 5, 7):
            for j, nt in enumerate(tri):
                add(tone(hz(nt), 0.45, "uke"), t0 + k * step + j * 0.012, 0.10)
        # 멜로디 (2마디 인트로 이후)
        if bar >= 2:
            phrase = (A if (bar // 4) % 3 != 2 else B)[ci]
            for k, nt in enumerate(phrase):
                if nt:
                    add(tone(hz(nt), 0.7, "marimba"), t0 + k * step, 0.22)
        # 드럼
        for k in range(8):
            if k in (0, 4) or (bar >= 4 and k == 3 and bar % 2):  # 킥
                tt = np.arange(int(SR * .18)) / SR
                add(np.sin(2*np.pi*(55 + 90*np.exp(-tt*40))*tt)*np.exp(-tt*16), t0 + k*step, 0.55)
            if k in (2, 6):                                         # 클랩
                tt = np.arange(int(SR * .14)) / SR
                add(rng.standard_normal(len(tt))*np.exp(-tt*38), t0 + k*step, 0.16)
            tt = np.arange(int(SR * .05)) / SR                       # 하이햇
            add(np.diff(rng.standard_normal(len(tt)+1))*np.exp(-tt*90), t0 + k*step, 0.10 if k % 2 else 0.06)
    # 간단한 에코(공간감)
    for dly, g in ((0.25, 0.22), (0.5, 0.1)):
        d = int(dly * SR); mix[d:] += mix[:-d] * g
    mix = mix[: int((total + 1.5) * SR)]
    mix /= np.max(np.abs(mix)) / 0.85
    fade = int(2.0 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
    mix[:int(.3*SR)] *= np.linspace(0, 1, int(.3*SR))
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    print(f"총 길이 ≈ {TOTAL:.1f}s")
    parts = [build_segment(i, s) for i, s in enumerate(SEGS)]
    with open(f"{WORK}/list.txt", "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{WORK}/list.txt", "-c", "copy", f"{WORK}/all.mp4"])
    make_music(TOTAL, f"{WORK}/bgm.wav")
    final = os.path.join(OUT, "incheon_airport_reels.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", f"{WORK}/all.mp4", "-i", f"{WORK}/bgm.wav", "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-t", f"{TOTAL:.3f}", "-movflags", "+faststart", final])
    print("완료:", final)
