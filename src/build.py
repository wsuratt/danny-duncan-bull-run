#!/usr/bin/env python3
"""Build Danny Duncan: Bull Run. Python-only LR35902 assembler and assets.

No SDK, proprietary assets, or Nintendo boot ROM required. All addresses are
resolved in two passes; duplicate labels, byte values and ROM size are checked.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
rom = bytearray(32768)
pc = 0x150
labels = {}
fixups = []
def emit(*bs):
    global pc
    for b in bs:
        assert 0 <= b <= 255, b
        rom[pc] = b
        pc += 1
def label(name):
    assert name not in labels, name
    labels[name] = pc
def word(n): emit(n & 255, n >> 8)
def ref(op, target):
    emit(op)
    if isinstance(target, str):
        fixups.append((pc, target)); word(0)
    else: word(target)
def jp(name): ref(0xC3, name)
def call(name): ref(0xCD, name)
def jz(name): ref(0xCA, name)
def jnz(name): ref(0xC2, name)
def jc(name): ref(0xDA, name)
def jnc(name): ref(0xD2, name)
def ld_a(n): emit(0x3E, n)
def load(a): ref(0xFA, a)
def save(a): ref(0xEA, a)
def hl(a): ref(0x21, a)
def de(a): ref(0x11, a)
def bc(a): ref(0x01, a)
def cp(n): emit(0xFE, n)
def ret(): emit(0xC9)
def setv(a,n): ld_a(n); save(a)

# WRAM: DMA page followed by compact game state.
OAM=0xC000
STATE=0xC100; KEYS=0xC101; EDGE=0xC102; FRAME=0xC103
LANE=0xC104; JUMP=0xC105; LIVES=0xC106; INV=0xC107
BULLS=0xC108; BARRIER=0xC10B; BLANE=0xC10C; SPAWN=0xC10D
TICK=0xC10E; SCORE=0xC110; BEST=0xC114; RNG=0xC118
TEMP=0xC119; SPEED=0xC11A; BTIMER=0xC11B
SCROLL=0xC11C
ROAD_STEP=0xC11D
PLAYER_Y=112
HIT_MIN=PLAYER_Y-13; HIT_MAX=PLAYER_Y+14

label('boot')
emit(0xF3); ref(0x31,0xDFFF) # DI; LD SP
emit(0xAF); save(0xFFFF); save(0xFF0F)
call('lcd_off')
hl(0xC000); bc(0x0200); call('zero')
hl(0xFE00); bc(160); call('zero')
hl('tiles'); de(0x8000); bc(0); tile_count_patch=pc-2; call('copy')
hl('dma_code'); de(0xFF80); bc(10); call('copy')
setv(0xFF47,0xE4); setv(0xFF48,0xE4); setv(0xFF49,0xE4)
setv(0xFF26,0x80); setv(0xFF24,0x77); setv(0xFF25,0x11)
setv(0xFF42,0); setv(0xFF43,0); setv(RNG,71)
call('title_screen')
label('loop')
call('input')
load(STATE); cp(1); jz('running'); cp(3); jz('paused')
load(EDGE); emit(0xE6,128); jz('draw_frame')
call('new_game'); jp('draw_frame')
label('paused')
load(EDGE); emit(0xE6,128); jz('draw_frame')
setv(STATE,1); call('game_screen'); jp('draw_frame')
label('running')
load(EDGE); emit(0xE6,128); jz('advance')
setv(STATE,3); call('pause_screen'); jp('draw_frame')
label('advance')
call('update')
label('draw_frame')
call('render')
call('vblank')
call(0xFF80)
load(STATE); cp(1); jnz('no_hud'); call('hud')
load(SCROLL); save(0xFF42)
setv(0xFF40,0xF3) # Window at $9C00 covers the two HUD rows.
label('no_hud')
label('end_vblank'); load(0xFF44); cp(144); jnc('end_vblank')
load(STATE); cp(1); jnz('loop')
label('hud_cutoff'); load(0xFF44); cp(16); jc('hud_cutoff')
setv(0xFF40,0xD3) # Hide window below HUD; scrolling background continues.
jp('loop')

label('lcd_off')
load(0xFF40); emit(0xCB,0x7F); jz('already_off')
call('vblank'); emit(0xAF); save(0xFF40)
label('already_off'); ret()
label('vblank'); load(0xFF44); cp(144); jc('vblank'); ret()
label('zero'); emit(0xAF)
label('zero_loop'); emit(0x22,0x0B,0x78,0xB1); jz('zero_end'); emit(0xAF); jp('zero_loop')
label('zero_end'); ret()
label('copy'); emit(0x2A,0x12,0x13,0x0B,0x78,0xB1); jnz('copy'); ret()
label('dma_code'); emit(0x3E,0xC0,0xE0,0x46,0x3E,40,0x3D,0x20,0xFD,0xC9)
# Copy ten bytes (including RET) to HRAM; CPU runs here during OAM DMA.

# Input bit layout: right left up down A B select start.
label('input')
ld_a(0x20); save(0xFF00); load(0xFF00); load(0xFF00); emit(0x2F,0xE6,15,0x47)
ld_a(0x10); save(0xFF00); load(0xFF00); load(0xFF00); emit(0x2F,0xE6,15,0xCB,0x37,0xB0,0x47)
load(KEYS); emit(0x2F,0xA0); save(EDGE); emit(0x78); save(KEYS)
ld_a(0x30); save(0xFF00); ret()

label('new_game')
hl(FRAME); bc(0x11); call('zero') # preserves best score
setv(STATE,1); setv(LANE,1); setv(LIVES,3); setv(SPAWN,55); setv(BTIMER,100); setv(SPEED,1); setv(SCROLL,0)
call('game_screen'); ret()

label('update')
hl(FRAME); emit(0x34)
setv(ROAD_STEP,0)
load(FRAME); emit(0xE6,1); jnz('scroll_done')
load(SPEED); save(ROAD_STEP); emit(0x47); load(SCROLL); emit(0x90); save(SCROLL)
label('scroll_done')
load(EDGE); emit(0xE6,1); jz('left')
load(LANE); cp(2); jz('left'); emit(0x3C); save(LANE)
label('left'); load(EDGE); emit(0xE6,2); jz('jump_input')
load(LANE); emit(0xB7); jz('jump_input'); emit(0x3D); save(LANE)
label('jump_input'); load(JUMP); emit(0xB7); jnz('jump_tick')
load(EDGE); emit(0xE6,0x30); jz('inv_tick'); setv(JUMP,36)
call('jump_sound')
label('jump_tick'); hl(JUMP); emit(0x35)
label('inv_tick'); load(INV); emit(0xB7); jz('score_tick'); hl(INV); emit(0x35)
label('score_tick'); load(FRAME); emit(0xE6,7); jnz('spawn_tick')
hl(SCORE+3)
label('decimal_inc'); emit(0x34,0x7E); cp(10); jc('score_done'); emit(0x36,0,0x2B,0x7D); cp(SCORE&255); jnc('decimal_inc')
label('score_done'); load(SCORE+1); cp(2); jc('spawn_tick'); setv(SPEED,2)
label('spawn_tick'); hl(SPAWN); emit(0x35); jnz('barrier_tick')
load(SPEED); cp(2); ld_a(60); jnz('spawn_period'); ld_a(42)
label('spawn_period'); save(SPAWN); call('random_lane'); emit(0x5F,0x16,0); hl(BULLS); emit(0x19,0x7E,0xB7); jnz('barrier_tick'); emit(0x36,152)
label('barrier_tick'); hl(BTIMER); emit(0x35); jnz('move_bulls')
setv(BTIMER,110); load(BARRIER); emit(0xB7); jnz('move_bulls'); call('random_lane'); save(BLANE); setv(BARRIER,20)
label('move_bulls')
# Keep a readable reaction window now that Danny runs near the bottom.
load(FRAME); emit(0xE6,1); jnz('move_barrier')
for lane in range(3):
    load(BULLS+lane); emit(0xB7); jz(f'bull_end_{lane}')
    emit(0x47); load(SPEED); emit(0x4F,0x78,0x91); cp(19); jnc(f'bull_store_{lane}'); emit(0xAF)
    label(f'bull_store_{lane}'); save(BULLS+lane)
    cp(HIT_MIN); jc(f'bull_end_{lane}'); cp(HIT_MAX); jnc(f'bull_end_{lane}')
    load(LANE); cp(lane); jnz(f'bull_end_{lane}'); call('hit')
    label(f'bull_end_{lane}')
label('move_barrier')
# Fences are planted in the street: use this frame's exact background delta,
# including still frames and the frame that changes difficulty.
load(BARRIER); emit(0xB7); jz('update_end'); emit(0x47); load(ROAD_STEP); emit(0x80); cp(157); jc('barrier_store'); emit(0xAF)
label('barrier_store'); save(BARRIER); cp(HIT_MIN); jc('update_end'); cp(HIT_MAX); jnc('update_end')
load(JUMP); emit(0xB7); jnz('update_end'); load(BLANE); emit(0x47); load(LANE); emit(0xB8); jnz('update_end'); call('hit')
label('update_end'); ret()
label('random_lane')
load(RNG); emit(0x87); jnc('rng_no_xor'); emit(0xEE,0x1D)
label('rng_no_xor'); save(RNG); emit(0xE6,3); cp(3); jz('random_lane'); ret()
label('hit')
load(INV); emit(0xB7); emit(0xC0) # RET NZ
setv(INV,100); call('hit_sound'); hl(LIVES); emit(0x35,0xC0)
setv(STATE,2)
# Lexicographic decimal high score comparison.
for i in range(4):
    load(BEST+i); emit(0x47); load(SCORE+i); emit(0xB8); jc('best_done'); jnz('save_best')
jp('best_done')
label('save_best'); hl(SCORE); de(BEST); bc(4); call('copy')
label('best_done'); call('over_screen'); ret()

label('jump_sound')
setv(0xFF10,0x26); setv(0xFF11,0x80); setv(0xFF12,0xA2)
setv(0xFF13,0x40); setv(0xFF14,0x86); ret()
label('hit_sound')
setv(0xFF10,0x56); setv(0xFF11,0x80); setv(0xFF12,0xD3)
setv(0xFF13,0x80); setv(0xFF14,0x83); ret()

# Render to a WRAM shadow OAM; vblank performs hardware DMA.
label('render'); hl(OAM); bc(160); call('zero'); de(OAM)
load(STATE); emit(0xB7); jz('title_sprites'); cp(1); emit(0xC0)
load(INV); emit(0xB7); jz('player_visible'); load(FRAME); emit(0xE6,4); jnz('bull_render')
label('player_visible'); load(LANE); call('lane_x'); emit(0x47)
load(JUMP); emit(0xB7); ld_a(PLAYER_Y); jz('player_y'); ld_a(PLAYER_Y-11)
label('player_y'); emit(0x4F)
load(FRAME); emit(0xE6,8); ld_a(64); jz('player_tile'); ld_a(68)
label('player_tile'); call('sprite16')
label('bull_render')
for lane in range(3):
    load(BULLS+lane); emit(0xB7); jz(f'render_bull_end_{lane}'); emit(0x4F)
    emit(0x06,48+32*lane); load(FRAME); emit(0xE6,8); ld_a(72); jz(f'bull_tile_{lane}'); ld_a(76)
    label(f'bull_tile_{lane}'); call('sprite16')
    label(f'render_bull_end_{lane}')
load(BARRIER); emit(0xB7); emit(0xC8); emit(0x4F); load(BLANE); call('lane_x'); emit(0x47); ld_a(80); call('sprite16'); ret()
label('title_sprites')
for x,t in [(48,72),(80,64),(112,76)]:
    emit(0x06,x,0x0E,80); ld_a(t); call('sprite16')
ret()
label('lane_x'); emit(0x87,0x87,0x87,0x87,0x87,0xC6,48); ret()
# A=first tile, B=x, C=y. Four 8x8 sprites in row-major order.
label('sprite16'); save(TEMP)
for n in range(4):
    emit(0x79)
    if n>=2: emit(0xC6,8)
    emit(0x12,0x13,0x78)
    if n%2: emit(0xC6,8)
    emit(0x12,0x13); load(TEMP)
    if n: emit(0xC6,n)
    emit(0x12,0x13,0xAF,0x12,0x13)
ret()

# Tile maps and UI. Text uses font tile indexes equal to ASCII minus 32.
def textrow(row,col,text):
    hl(0x9800+row*32+col)
    for ch in text: emit(0x36,ord(ch)-32,0x23)
def screen_begin():
    call('lcd_off'); setv(0xFF42,0)
    hl(0x9800); bc(2048); call('zero')
def screen_end(): setv(0xFF40,0x93); ret()
label('title_screen'); screen_begin()
textrow(1,3,'DANNY DUNCAN')
textrow(3,3,'B U L L  R U N')
textrow(5,1,'RUN. DODGE. REPEAT.')
textrow(11,4,'PRESS START')
textrow(13,2,'LEFT/RIGHT: DODGE')
textrow(14,2,'A / B: JUMP')
textrow(16,1,'UNOFFICIAL FAN GAME')
screen_end()
label('game_screen'); screen_begin()
# Three-tile facades on either side: roofs, shuttered windows, iron balconies,
# arched entrances, stone paving and San Fermin-style festival pennants.
facade=[(88,89,90),(91,92,93),(94,95,96),(91,92,93),
        (94,95,96),(97,98,97),(99,99,99),(100,101,102)]
# Fill all 256 pixels so the street wraps continuously under hardware scroll.
for row in range(32):
    hl(0x9800+row*32)
    for col in range(20):
        tile=84 if col in (3,16) else (85 if col in (7,11) and row%4==0 else (86 if 4<=col<=15 else 87))
        if col<3: tile=facade[(row-2)%8][col]
        elif col>16: tile=facade[(row+1)%8][col-17]
        emit(0x36,tile,0x23)
setv(0xFF4A,0); setv(0xFF4B,7) # Window origin: top left, independent of SCY.
hl(0x9C00)
for ch in 'RUN 0000    HEART 3': emit(0x36,ord(ch)-32,0x23)
hl(0x9C20)
for ch in 'BEST 0000': emit(0x36,ord(ch)-32,0x23)
screen_end()
label('pause_screen'); screen_begin(); textrow(5,6,'PAUSED'); textrow(8,3,'START TO RESUME'); textrow(11,2,'DODGE EVERY BULL'); textrow(13,2,'JUMP THE BARRIERS'); screen_end()
label('over_screen'); screen_begin(); textrow(3,5,'TRAMPLED!'); textrow(6,3,'RUN  0000'); textrow(8,3,'BEST 0000'); textrow(11,3,'START TO RETRY'); textrow(14,2,'GET UP. RUN AGAIN.'); call('over_scores'); screen_end()
label('over_scores')
for addr,pos in [(SCORE,0x9800+6*32+8),(BEST,0x9800+8*32+8)]:
    hl(pos)
    for i in range(4): load(addr+i); emit(0xC6,16,0x22)
ret()
label('hud')
for addr,pos in [(SCORE,0x9C04),(BEST,0x9C25)]:
    hl(pos)
    for i in range(4): load(addr+i); emit(0xC6,16,0x22)
load(LIVES); emit(0xC6,16); save(0x9C12); ret()

# 5x7 hand-built font, padded to 8x8. Artwork is original and deliberately DMG.
FONT={
'A':['01110','10001','10001','11111','10001','10001','10001'],
'B':['11110','10001','10001','11110','10001','10001','11110'],
'C':['01111','10000','10000','10000','10000','10000','01111'],
'D':['11110','10001','10001','10001','10001','10001','11110'],
'E':['11111','10000','10000','11110','10000','10000','11111'],
'F':['11111','10000','10000','11110','10000','10000','10000'],
'G':['01111','10000','10000','10111','10001','10001','01111'],
'H':['10001','10001','10001','11111','10001','10001','10001'],
'I':['111','010','010','010','010','010','111'],
'J':['00111','00010','00010','00010','10010','10010','01100'],
'K':['10001','10010','10100','11000','10100','10010','10001'],
'L':['10000','10000','10000','10000','10000','10000','11111'],
'M':['10001','11011','10101','10101','10001','10001','10001'],
'N':['10001','11001','10101','10011','10001','10001','10001'],
'O':['01110','10001','10001','10001','10001','10001','01110'],
'P':['11110','10001','10001','11110','10000','10000','10000'],
'Q':['01110','10001','10001','10001','10101','10010','01101'],
'R':['11110','10001','10001','11110','10100','10010','10001'],
'S':['01111','10000','10000','01110','00001','00001','11110'],
'T':['11111','00100','00100','00100','00100','00100','00100'],
'U':['10001','10001','10001','10001','10001','10001','01110'],
'V':['10001','10001','10001','10001','10001','01010','00100'],
'W':['10001','10001','10001','10101','10101','11011','10001'],
'X':['10001','10001','01010','00100','01010','10001','10001'],
'Y':['10001','10001','01010','00100','00100','00100','00100'],
'Z':['11111','00001','00010','00100','01000','10000','11111'],
'0':['01110','10001','10011','10101','11001','10001','01110'],
'1':['00100','01100','00100','00100','00100','00100','01110'],
'2':['01110','10001','00001','00010','00100','01000','11111'],
'3':['11110','00001','00001','01110','00001','00001','11110'],
'4':['00010','00110','01010','10010','11111','00010','00010'],
'5':['11111','10000','10000','11110','00001','00001','11110'],
'6':['01110','10000','10000','11110','10001','10001','01110'],
'7':['11111','00001','00010','00100','01000','01000','01000'],
'8':['01110','10001','10001','01110','10001','10001','01110'],
'9':['01110','10001','10001','01111','00001','00001','01110'],
'.':['0','0','0','0','0','1','1'], ':':['0','1','1','0','1','1','0'],
'!':['1','1','1','1','1','0','1'], '/':['00001','00010','00010','00100','01000','01000','10000'],
'<':['0001','0010','0100','1000','0100','0010','0001'],
'>':['1000','0100','0010','0001','0010','0100','1000'],
'^':['00100','01010','10001','00000','00000','00000','00000'],
'_':['00000','00000','00000','00000','00000','00000','11111'],
'(':['001','010','100','100','100','010','001'],
')':['100','010','001','001','001','010','100'],
}
tiledata=[]
def tile(rows):
    for row in rows:
        lo=hi=0
        for x,c in enumerate(row):
            n=int(c); lo|=(n&1)<<(7-x); hi|=(n>>1)<<(7-x)
        tiledata.extend([lo,hi])
for code in range(32,96):
    rows=FONT.get(chr(code),[])
    tile(['00000000']+['0'+r.replace('1','3').ljust(7,'0') for r in rows]+['00000000']*(7-len(rows)))
def sprite(rows):
    assert len(rows)==16 and all(len(r)==16 for r in rows)
    for y,x in [(0,0),(0,8),(8,0),(8,8)]: tile([r[x:x+8] for r in rows[y:y+8]])
# Rear-view Danny: tousled curls instead of a cap; white festival shirt and
# trousers, contrasting neckerchief tails, waist sash, and dark running shoes.
player=[
'0000333333000000','0003322323330000','0033221222233000','0032222222223000',
'0033222222233000','0003322222330000','0000322222300000','0003332333330000',
'0033113311133000','0032113111123000','0003111311130000','0003333333330000',
'0003111001130000','0003111001130000','0003110001130000','0003330003330000']
sprite(player)
p2=player.copy()
p2[8]='0032113311123000'; p2[9]='0033113111133000'
p2[13]='0003111000000000'; p2[14]='0003330001130000'; p2[15]='0000000003330000'
sprite(p2)
bull=[
'0300000000000030','0330000000000330','0033300000033300','0003133333313000',
'0003111111113000','0033111111113300','0031321111231300','0031111111111300',
'0031123333211300','0003122222213000','0000332222330000','0000311111130000',
'0000311111130000','0000333333330000','0000330000330000','0000330000330000']
sprite(bull)
b2=bull.copy(); b2[14]='0000330000000000'; b2[15]='0000000000330000'; sprite(b2)
sprite(['0000000000000000']*3+['0333333333333330','0311311311311330','0313113113113130','0333333333333330','0030000000003000','0030000000003000','0030000000003000','0333000000033300']+['0000000000000000']*5)
tile(['33333333','31111113']*4) # 84 road edge
tile(['00033000']*4+['00000000']*4) # 85 lane dash
tile(['00000000']*8) # 86 asphalt
tile(['11111111','12111111','11111111','11111121','11111111','11121111','11111111','11111111']) # 87 pavement
# Spanish old-town facades. Rows encode the DMG's four shades directly.
tile(['11111112','11111123','11111233','11112323','11123333','11232323','12333333','33333333']) # 88 pitched roof
tile(['22222222','33333333','23232323','33333333','32323232','33333333','23232323','33333333']) # 89 clay roof tiles
tile(['21111111','32111111','33211111','32321111','33332111','32323211','33333321','33333333']) # 90 roof end
tile(['00000001','00000001','00000001','00000001','00000001','00000001','00000001','11111111']) # 91 stucco
tile(['11111111','13333331','13233231','13233231','13233231','13233231','13333331','11111111']) # 92 shutters
tile(['10000000','10000000','10000000','10000000','10000000','10000000','10000000','11111111']) # 93 stucco
tile(['00000000','00000000','33333333','03030303','03030303','33333333','11111111','00000000']) # 94 iron balcony
tile(['11111111','13333331','33333333','30330303','30330303','33333333','11111111','00000000']) # 95 balcony center
tile(['00000000','00000000','33333333','30303030','30303030','33333333','11111111','00000000']) # 96 balcony end
tile(['00000000','00000000','00000000','00000000','00000000','00000000','00000000','22222222']) # 97 facade base
tile(['00133100','01333310','13333331','13323331','13323331','13323331','13323331','23333332']) # 98 arched door
tile(['22232222','22232222','33333333','23222222','23222222','33333333','22223222','22223222']) # 99 stone paving
tile(['11111111','33311111','13333311','11333333','11133331','11113311','11111111','11111111']) # 100 pennant cord
tile(['11111111','11111111','11111111','33333333','13333311','11333111','11131111','11111111']) # 101 pennant
tile(['11111111','11111333','11133331','33333311','13333111','11331111','11111111','11111111']) # 102 pennant cord
label('tiles'); emit(*tiledata)

for at,target in fixups:
    assert target in labels, target
    dest=labels[target]; rom[at]=dest&255; rom[at+1]=dest>>8
rom[tile_count_patch]=len(tiledata)&255; rom[tile_count_patch+1]=len(tiledata)>>8
assert pc<0x8000, hex(pc)
# Standard DMG cartridge header. Nintendo logo is required by original hardware.
rom[0x100:0x104]=bytes([0,0xC3,0x50,1])
rom[0x104:0x134]=bytes.fromhex('CEED6666CC0D000B03730083000C000D0008111F8889000EDCCC6EE6DDDDD999BBBB67636E0EECCCDDDC999FBBB9333E')
rom[0x134:0x144]=b'DANNY BULL RUN\x00\x00'
rom[0x144:0x14D]=bytes([0,0,0,0,0,0,1,0,0])
checksum=0
for b in rom[0x134:0x14D]: checksum=(checksum-b-1)&255
rom[0x14D]=checksum
total=sum(rom[:0x14E])+sum(rom[0x150:]); rom[0x14E]=total>>8&255; rom[0x14F]=total&255
assert len(rom)==32768
(ROOT/'dist').mkdir(exist_ok=True)
(ROOT/'dist/danny-bull-run.gb').write_bytes(rom)
(ROOT/'dist/symbols.json').write_text(json.dumps({'labels':labels,'ram':{k:v for k,v in globals().copy().items() if k.isupper() and isinstance(v,int)}},indent=2))
print(f'Built dist/danny-bull-run.gb: {len(rom):,} bytes; program/assets end at ${pc:04X}')
