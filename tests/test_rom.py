"""Headless integration tests against the compiled ROM using PyBoy."""
from pathlib import Path
import json
from pyboy import PyBoy
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / 'dist/danny-bull-run.gb'
R = json.loads((ROOT/'dist/symbols.json').read_text())['ram']
data = ROM.read_bytes()
assert len(data) == 32768
assert data[0x147:0x14A] == bytes(3), 'ROM-only, 32 KiB, no cartridge RAM'
check = 0
for b in data[0x134:0x14D]: check = (check-b-1)&255
assert check == data[0x14D]
assert (sum(data[:0x14E])+sum(data[0x150:]))&65535 == int.from_bytes(data[0x14E:0x150], 'big')

p = PyBoy(str(ROM), window='null', sound_emulated=True,
          color_palette=(0xE0F8D0,0x88C070,0x346856,0x081820))
p.set_emulation_speed(0)
def tick(n=1): p.tick(n, True)
def get(k): return p.memory[R[k]]
def put(k,v): p.memory[R[k]] = v
def tap(key): p.button(key); tick(2); p.button_release(key); tick(2)
def quiet():
    for i in range(3): p.memory[R['BULLS']+i]=0
    put('BARRIER',0); put('SPAWN',200); put('BTIMER',200)
def shot(name):
    p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(ROOT/'dist'/name)

try:
    tick(120)
    assert get('STATE') == 0
    assert bytes(p.memory[0xFF80:0xFF8A]) == bytes([0x3e,0xc0,0xe0,0x46,0x3e,40,0x3d,0x20,0xfd,0xc9])
    shot('title.png')
    tap('start'); assert get('STATE') == 1 and get('LIVES')==3
    quiet()
    tick(4)
    before=p.screen.image.copy(); scroll=get('SCROLL')
    tick(8)
    after=p.screen.image.copy()
    assert get('SCROLL')==(scroll-4)&255
    assert all(before.getpixel((x,y))==after.getpixel((x,y+4))
               for x in range(24) for y in range(24,120)), 'Facades must scroll down'
    assert before.crop((0,0,32,16)).tobytes()==after.crop((0,0,32,16)).tobytes(), 'HUD must stay fixed'
    tap('right'); assert get('LANE')==2
    tap('right'); assert get('LANE')==2
    tap('left'); assert get('LANE')==1
    tap('left'); assert get('LANE')==0
    tap('left'); assert get('LANE')==0
    tap('right'); assert get('LANE')==1
    tap('a'); assert get('JUMP')>0
    tick(40); assert get('JUMP')==0
    quiet(); tap('start'); assert get('STATE')==3
    frame=get('FRAME'); scroll=get('SCROLL'); tick(30)
    assert get('FRAME')==frame and get('SCROLL')==scroll
    tap('start'); assert get('STATE')==1

    # Score is decimal, carries correctly, and accelerates at 200 points.
    quiet(); put('FRAME',7)
    for i,v in enumerate([0,0,0,9]): p.memory[R['SCORE']+i]=v
    tick(); assert list(p.memory[R['SCORE']:R['SCORE']+4])==[0,0,1,0]
    p.memory[R['SCORE']+1]=2; tick(8); assert get('SPEED')==2
    put('SPEED',1); p.memory[R['SCORE']+1]=0

    # A planted fence must move exactly with the road, even at acceleration.
    for speed in (1,2):
        quiet(); put('SPEED',speed); put('BARRIER',30)
        for _ in range(12):
            road=get('SCROLL'); fence=get('BARRIER'); tick()
            assert get('BARRIER')-fence == (road-get('SCROLL'))&255
    quiet(); put('SPEED',1); put('BARRIER',30); put('FRAME',7)
    p.memory[R['SCORE']+1]=2
    road=get('SCROLL'); fence=get('BARRIER'); tick()
    assert get('SPEED')==2
    assert get('BARRIER')-fence == (road-get('SCROLL'))&255
    put('SPEED',1); p.memory[R['SCORE']+1]=0

    # A bull damages the player; invulnerability prevents repeated damage.
    quiet(); put('INV',0); p.memory[R['BULLS']+1]=R['HIT_MAX']
    tick(5); assert get('LIVES')==2 and get('INV')>0
    tick(10); assert get('LIVES')==2

    # Grounded barrier collision, airborne barrier clearance, airborne bull hit.
    quiet(); put('INV',0); put('LIVES',3); put('BARRIER',R['HIT_MIN']-2); put('BLANE',1)
    tick(5); assert get('LIVES')==2
    quiet(); put('INV',0); put('LIVES',3); tap('b')
    put('BARRIER',R['HIT_MIN']-3); put('BLANE',1); tick(8)
    assert get('LIVES')==3 and get('JUMP')>0
    quiet(); p.memory[R['BULLS']+1]=R['HIT_MAX']; tick(5); assert get('LIVES')==2

    # Capture a deterministic gameplay scene with two approaching threats.
    quiet(); put('INV',0); put('JUMP',0); put('LIVES',3)
    p.memory[R['BULLS']]=124; p.memory[R['BULLS']+2]=148
    put('BARRIER',66); put('BLANE',1); tick(2); shot('gameplay.png')
    quiet(); put('LIVES',1); put('INV',0); p.memory[R['BULLS']+1]=R['HIT_MAX']
    tick(5); assert get('STATE')==2
    final=list(p.memory[R['SCORE']:R['SCORE']+4])
    assert list(p.memory[R['BEST']:R['BEST']+4])==final
    shot('game-over.png')
    tap('start'); assert get('STATE')==1 and get('LIVES')==3
    assert list(p.memory[R['BEST']:R['BEST']+4])==final
    assert list(p.memory[R['SCORE']:R['SCORE']+4])==[0,0,0,0]

    # Exercise real spawning and repeated game-over/retry for several minutes.
    for i in range(80):
        if get('STATE')==2: tap('start')
        if i%3==0: tap('left')
        elif i%3==1: tap('right')
        if i%2==0: tap('a')
        tick(60)
        assert get('STATE') in (1,2)
        assert 0 <= get('LANE') <= 2 and 0 <= get('LIVES') <= 3
        assert all(v<10 for v in p.memory[R['SCORE']:R['SCORE']+4])
    print('PASS: header, boot, DMA, controls, jumping, pause, score carry, difficulty,')
    print('      pixel-accurate scenery scrolling and fixed HUD,')
    print('      fence/road synchronization at both speeds and acceleration,')
    print('      bull/barrier collisions, invulnerability, game over, best score, restart,')
    print('      and 4,800+ frames of spawning/stress gameplay. Screenshots saved to dist/.')
finally:
    p.stop(save=False)
