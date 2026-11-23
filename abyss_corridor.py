# -*- coding: utf-8 -*-
"""深渊回廊：六模式 · 二十八层异域 · 无尽层域 —— 单文件肉鸽射击（pygame）"""
import os, sys, math, json, random, array, time, re, wave

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
HEADLESS = os.environ.get('ABYSS_HEADLESS') == '1'
if HEADLESS:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

W, H = 1280, 760


def asset_path(*parts):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


FPS = 60
SR = 22050
VERSION = '3.5.0'
TITLE = '深渊回廊'
TITLE_EN = 'ABYSS CORRIDOR'
LAYERS = 28

# 每层是一张比屏幕大得多的地图，镜头跟随玩家
def world_of(layer):
    layer = max(1, int(layer))
    # 每层是一张比屏幕大得多的地图；3.3 加大基础面积，深层的成长稍放缓以控制显存
    return (7000 + min(110, layer - 1) * 260, 4800 + min(110, layer - 1) * 140)

DIFFS = [
    dict(id=0, name='巡航', en='CRUISE', desc='标准节奏 · 先把二十八层摸熟',
         desc_en='Standard pacing · learn the 28 strata',
         ehp=1.0, budget=1.0, espd=1.0, score=1.0, dmg2=0.0, col='steel'),
    dict(id=1, name='深渊', en='ABYSS', desc='敌人更硬更密 · 偶发重创 · 得分 ×1.35',
         desc_en='Tougher, denser enemies · rare heavy hits · score ×1.35',
         ehp=1.22, budget=1.15, espd=1.08, score=1.35, dmg2=0.14, col='violet'),
    dict(id=2, name='噩梦', en='NIGHTMARE', desc='最硬的敌人 · 频繁重创 · 得分 ×1.8',
         desc_en='Hardest enemies · frequent heavy hits · score ×1.8',
         ehp=1.45, budget=1.30, espd=1.18, score=1.8, dmg2=0.28, col='coral'),
]

# 模式决定整局节奏；waves=每层波数，layers=None 表示无限
MODES = [
    dict(id='voyage', name='远航', en='VOYAGE', col='aqua', layers=28, waves=5,
         budget=1.0, ehp=1.0, boss_hp=1.0, bossrate=1.0, score=1.0,
         desc='28 层完整远征 · 每层 5 波 + BOSS',
         desc_en='Full 28-stratum expedition · 5 waves + boss per stratum'),
    dict(id='endless', name='无尽', en='ENDLESS', col='violet', layers=None, waves=5,
         budget=1.06, ehp=1.0, boss_hp=1.0, bossrate=1.06, score=1.45,
         desc='层数无上限 · 每 5 波一位 BOSS · 主题轮回',
         desc_en='No depth limit · boss every 5 waves · themes cycle'),
    dict(id='rush', name='急行', en='RUSH', col='coral', layers=12, waves=3,
         budget=1.22, ehp=1.05, boss_hp=1.05, bossrate=1.14, score=1.55,
         desc='12 层 · 每层 3 波 · 高压快节奏',
         desc_en='12 strata · 3 waves per stratum · high-pressure pace'),
    dict(id='hunt', name='猎王', en='HUNT', col='gold', layers=12, waves=1,
         budget=1.0, ehp=1.0, boss_hp=1.18, bossrate=1.22, score=1.8,
         desc='12 层 · 跳过杂兵 · 每层直接猎杀 BOSS',
         desc_en='12 strata · skip mobs · hunt a boss every stratum'),
    dict(id='daily', name='每日', en='DAILY', col='green', layers=24, waves=5,
         budget=1.08, ehp=1.03, boss_hp=1.05, bossrate=1.06, score=1.5,
         daily=True,
         desc='每日固定种子 · 24 层 · 全服同一条回廊',
         desc_en='Fixed daily seed · 24 strata · everyone runs the same corridor'),
    dict(id='pact', name='契约', en='PACT', col='gold', layers=28, waves=5,
         budget=1.12, ehp=1.04, boss_hp=1.02, bossrate=1.04, score=1.65, pact=True,
         desc='28 层 · 每层 BOSS 后签一份风险契约',
         desc_en='28 strata · sign a risk pact after every boss'),
]

# 契约模式：每层 BOSS 之后三选一，收益与代价同时写进本局
PACTS = [
    dict(id='bounty', name='悬赏契约', en='BOUNTY PACT', rarity='r',
         desc='得分 +30% · 敌机 +20%', desc_en='Score +30% · enemies +20%',
         flavor='回廊把赏金压在你的名字上。',
         mods={'score': 1.3, 'budget': 1.2}),
    dict(id='blood', name='血契', en='BLOOD PACT', rarity='l',
         desc='伤害 +35% · 艇体 -1', desc_en='Damage +35% · hull -1',
         flavor='用一层壳，换一把更快的刀。',
         mods={'dmg': 1.35, 'maxhp': -1}),
    dict(id='overclock', name='超频契约', en='OVERCLOCK PACT', rarity='r',
         desc='射速 +20% · 敌弹 +15%', desc_en='Fire rate +20% · enemy bullets +15%',
         flavor='枪管烧红之前，敌人先烧起来。',
         mods={'rate': 1.2, 'espd': 1.15}),
    dict(id='aegis', name='神盾契约', en='AEGIS PACT', rarity='r',
         desc='立即 +2 护盾 · 敌机 +20%', desc_en='+2 shields now · enemies +20%',
         flavor='壳先替你说话，后面再算账。',
         mods={'shield': 2, 'budget': 1.2}),
    dict(id='greed', name='贪婪契约', en='GREED PACT', rarity='c',
         desc='掉落 +45% · 敌人艇体 +15%', desc_en='Drops +45% · enemy hull +15%',
         flavor='沉在泥里的东西，也会长出牙齿。',
         mods={'drop': 1.45, 'ehp': 1.15}),
    dict(id='slipstream', name='疾流契约', en='SLIPSTREAM PACT', rarity='c',
         desc='移动 +18% · 得分 +15%', desc_en='Move +18% · score +15%',
         flavor='水压替你让路，代价是别停下来。',
         mods={'speed': 1.18, 'score': 1.15}),
    dict(id='glass', name='玻璃契约', en='GLASS PACT', rarity='l',
         desc='伤害 +40% · 冷却 -15% · 艇体 -1',
         desc_en='Damage +40% · CD -15% · hull -1',
         flavor='壳碎了，光才透进来。',
         mods={'dmg': 1.4, 'cd': .85, 'maxhp': -1}),
    dict(id='fortune', name='命运契约', en='FORTUNE PACT', rarity='r',
         desc='稀有/传说增幅更常出现 · 敌机 +10%',
         desc_en='More rare/legendary augments · enemies +10%',
         flavor='深渊偶尔也会把好牌递给你。',
         mods={'luck': 1, 'budget': 1.1}),
    dict(id='repair', name='修复契约', en='REPAIR PACT', rarity='c',
         desc='立即修复 2 艇体 · 掉落 -10%', desc_en='Repair 2 hull now · drops -10%',
         flavor='先把裂口焊上，再谈下一层。',
         mods={'heal': 2, 'drop': .9}),
    dict(id='hunt', name='猎王契约', en='HUNT PACT', rarity='r',
         desc='BOSS 艇体 -10% · 敌机 +15%', desc_en='Boss hull -10% · enemies +15%',
         flavor='王座也是可以撬开的。',
         mods={'boss_hp': .9, 'budget': 1.15}),
    dict(id='echo', name='回声契约', en='ECHO PACT', rarity='r',
         desc='技能冷却 -20% · 敌弹 +10%', desc_en='Cooldown -20% · enemy bullets +10%',
         flavor='喊得越响，回来的东西越多。',
         mods={'cd': .8, 'espd': 1.1}),
    dict(id='void', name='虚空契约', en='VOID PACT', rarity='c',
         desc='敌弹 -15% · 得分 -10%', desc_en='Enemy bullets -15% · score -10%',
         flavor='有一段路，连声音都被吃掉了。',
         mods={'espd': .85, 'score': .9}),
]
PACT_BY_ID = {p['id']: p for p in PACTS}
PACT_FLAVOR_EN = {
    'bounty': 'The corridor puts a bounty on your name.',
    'blood': 'Trade one layer of hull for a faster blade.',
    'overclock': 'Burn the barrel before the enemy burns.',
    'aegis': 'Let the shell speak first; settle the debt later.',
    'greed': 'What sinks in the mud grows teeth.',
    'slipstream': 'The current makes way; just do not stop.',
    'glass': 'The shell breaks so the light gets in.',
    'fortune': 'Even the abyss hands out a good hand now and then.',
    'repair': 'Weld the crack first; talk about the next layer later.',
    'hunt': 'Thrones can be pried open.',
    'echo': 'Shout louder; more comes back.',
    'void': 'There is a stretch where even sound is eaten.',
}


def roll_pacts():
    return random.sample(PACTS, 3)


def pact_card(p):
    """把契约包装成和增幅卡同构的数据，复用现有的三卡界面。"""
    return (p['id'], p['name'], p['desc'], p.get('rarity', 'r'), 'pact', p, 1)


def apply_pact(p):
    r = G.run
    st = r.st
    m = p.get('mods', {})
    for key in ('dmg', 'rate', 'cd', 'speed'):
        if key in m:
            st[key] *= m[key]
    if 'maxhp' in m:
        r.max_hp = max(2, r.max_hp + int(m['maxhp']))
        r.hp = min(r.hp, r.max_hp)
        if G.player:
            G.player.max_hp = r.max_hp
            G.player.hp = min(G.player.hp, r.max_hp)
    if 'shield' in m and G.player:
        G.player.shield = min(3, G.player.shield + int(m['shield']))
        G.player.shield_t = max(G.player.shield_t, 18)
    if 'heal' in m:
        heal_player(int(m['heal']), quiet=True)
    if 'luck' in m:
        st['luck'] += m['luck']
    for key in ('score', 'budget', 'ehp', 'espd', 'drop', 'boss_hp', 'bossrate'):
        if key in m:
            r.mut[key] = r.mut.get(key, 1.0) * m[key]
    r.pacts.append(p['id'])
    if len(r.pacts) >= 5:
        grant_ach('pact5')
    if len(r.pacts) >= 10:
        grant_ach('pact10')



# 回声工坊：跨局永久升级（用回声结晶购买，局内不出现）
UPGRADES = [
    dict(id='hull', name='加固艇壳', en='HARDENED HULL',
         desc='艇体上限 +1', desc_en='Max hull +1', max=3, costs=(30, 60, 110)),
    dict(id='gun', name='校准火力', en='CALIBRATED GUNS',
         desc='子弹伤害 +7%', desc_en='Projectile damage +7%', max=3, costs=(25, 50, 95)),
    dict(id='magnet', name='回声磁芯', en='ECHO MAGNET',
         desc='拾取范围 +18%', desc_en='Pickup radius +18%', max=3, costs=(20, 45, 80)),
    dict(id='cool', name='冷却旁路', en='COOLING LOOP',
         desc='技能冷却 -6%', desc_en='Skill cooldown -6%', max=3, costs=(25, 50, 90)),
    dict(id='salvage', name='回收协议', en='SALVAGE PROTOCOL',
         desc='掉落率 +10%', desc_en='Drop rate +10%', max=3, costs=(20, 40, 75)),
    dict(id='shield', name='应急护盾', en='EMERGENCY SHIELD',
         desc='开局护盾 +1', desc_en='Start with +1 shield', max=2, costs=(45, 95)),
    dict(id='cache', name='预装增幅', en='PRELOADED AUGMENT',
         desc='开局随机增幅 +1', desc_en='Start with +1 random augment', max=2, costs=(60, 130)),
    dict(id='bane', name='猎王校准', en='BOSS CALIBRATION',
         desc='对 BOSS 伤害 +8%', desc_en='Damage to bosses +8%', max=3, costs=(30, 65, 120)),
]
UPG_BY_ID = {u['id']: u for u in UPGRADES}


def upg_level(uid):
    g = globals().get('G')
    p = getattr(g, 'profile', None)
    upg = p.get('upg', {}) if isinstance(p, dict) else META.get('upg', {})
    return int(upg.get(uid, 0)) if isinstance(upg, dict) else 0


def profile_shards():
    g = globals().get('G')
    p = getattr(g, 'profile', None)
    if isinstance(p, dict):
        return int(max(0, p.get('shards', 0)))
    return int(max(0, META.get('shards', 0)))


def profile_of_slot(slot):
    d = read_slot(slot)
    return normalize_profile(d.get('profile')) if d else None


def upg_cost(u):
    lvl = upg_level(u['id'])
    if lvl >= u['max']:
        return None
    return u['costs'][min(lvl, len(u['costs']) - 1)]


def mode_of(run=None):
    run = run or getattr(G, 'run', None)
    if run and getattr(run, 'mode', None) is not None:
        return MODES[run.mode]
    return MODES[getattr(G, 'mode', 0)]


def waves_for_layer():
    run = getattr(G, 'run', None)
    if run and getattr(run, 'waves_per_layer', None):
        return run.waves_per_layer
    return mode_of()['waves']


def layers_for_run():
    run = getattr(G, 'run', None)
    if run:
        return run.layer_cap
    return mode_of()['layers']


def threat_of(layer):
    """线性威胁：每下一层，敌人和 BOSS 的强度按固定斜率上升"""
    return 1.0 + max(0, int(layer) - 1) * .012

COL = {
    'bg0': (7, 22, 30), 'bg1': (3, 10, 16), 'bg2': (1, 6, 10),
    'ink': (228, 246, 250), 'dim': (110, 152, 165), 'dimmer': (58, 96, 108),
    'aqua': (95, 240, 208), 'amber': (255, 178, 87), 'coral': (255, 110, 120),
    'violet': (168, 140, 255), 'green': (150, 255, 190), 'white': (236, 252, 255),
    'gold': (255, 210, 120), 'steel': (127, 200, 216),
}

def dist2(a, b):
    dx = a[0] - b[0]; dy = a[1] - b[1]
    return dx * dx + dy * dy


def seg_dist2(px, py, x1, y1, x2, y2):
    """点到线段的最短距离平方。"""
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return (px - x1) ** 2 + (py - y1) ** 2
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return (px - (x1 + dx * t)) ** 2 + (py - (y1 + dy * t)) ** 2

def clamp(v, a, b):
    return a if v < a else (b if v > b else v)

def lerp(a, b, t):
    return a + (b - a) * t

def norm_aim(a):
    """把航向角收敛到 -pi ~ pi。0 指向正上方，正值为顺时针。"""
    return (a + math.pi) % (math.pi * 2) - math.pi

def aim_to(dx, dy):
    """从位移向量求船头角：0 上、+pi/2 右、pi 下。"""
    return math.atan2(dx, -dy)

def aim_target():
    """自动索敌：优先附近 Boss，其次最近敌机；没有目标返回 None。"""
    p = G.player
    if not p:
        return None
    best = None
    bestd = 1e18
    bo = G.boss
    if bo and not bo.dying:
        best = aim_to(bo.x - p.x, bo.y - p.y)
        bestd = dist2((bo.x, bo.y), (p.x, p.y)) * .82
    for e in G.enemies:
        if e.dead:
            continue
        d = dist2((e.x, e.y), (p.x, p.y))
        if d < bestd:
            bestd = d
            best = aim_to(e.x - p.x, e.y - p.y)
    return best

def ease(t):
    return 2 * t * t if t < .5 else 1 - (-2 * t + 2) ** 2 / 2

def rnd(a=1.0, b=0.0):
    return b + random.random() * (a - b)

def rndint(a, b):
    return random.randint(b, a)

# ---------------------------------------------------------------- 字体
_FONT_PATH = {False: None, True: None}

def find_font(bold=False):
    k = bool(bold)
    if _FONT_PATH[k]:
        return _FONT_PATH[k]
    if k:
        cands = [r'C:\Windows\Fonts\msyhbd.ttc',
                 r'C:\Windows\Fonts\simhei.ttf',
                 r'C:\Windows\Fonts\Deng.ttf',
                 r'C:\Windows\Fonts\simsun.ttc']
    else:
        cands = [r'C:\Windows\Fonts\msyh.ttc',
                 r'C:\Windows\Fonts\simhei.ttf',
                 r'C:\Windows\Fonts\Deng.ttf',
                 r'C:\Windows\Fonts\simsun.ttc']
    for c in cands:
        if os.path.exists(c):
            _FONT_PATH[k] = c
            return c
    _FONT_PATH[k] = pygame.font.match_font('microsoftyahei,simhei,arial', bold=k)
    return _FONT_PATH[k]

_fonts = {}

def font(size, bold=False):
    key = (size, bool(bold))
    if key not in _fonts:
        path = find_font(bold)
        try:
            f = pygame.font.Font(path, size)
        except Exception:
            f = pygame.font.Font(None, size)
        # 有真正的粗体字重就用，只有缺粗体文件时才用伪粗体
        if bold and not (path and 'msyhbd' in os.path.basename(path).lower()):
            f.set_bold(True)
        _fonts[key] = f
    return _fonts[key]

_text_cache = {}

def text_img(s, size, color, bold=False):
    s = tr(s)
    key = (s, size, color, bold)
    if key not in _text_cache:
        if len(_text_cache) > 1400:
            # 分数每帧变化，缓存会无限膨胀；满了就丢掉一半老的
            for k in list(_text_cache.keys())[:700]:
                _text_cache.pop(k, None)
        _text_cache[key] = font(size, bold).render(s, True, color)
    return _text_cache[key]

def draw_text(surf, s, size, color, pos, align='left', bold=False, shadow=None):
    img = text_img(s, size, color, bold)
    x, y = pos
    if align == 'center':
        x -= img.get_width() // 2
    elif align == 'right':
        x -= img.get_width()
    if shadow:
        sh = text_img(s, size, shadow, bold)
        surf.blit(sh, (x + 1, y + 2))
    surf.blit(img, (x, y))
    return img.get_width()

def text_w(s, size, bold=False):
    return font(size, bold).size(tr(s))[0]


def fit_size(s, size, maxw, bold=False, floor=8):
    """框不够大时自动收字号，保证字不会跑到框外。"""
    size = int(size)
    while size > floor and text_w(s, size, bold) > maxw:
        size -= 1
    return size

# ---------------------------------------------------------------- 光晕
_GLOW_CACHE = {}
_GLOW_BASE = {}
GLOW_R = [5, 9, 14, 20, 28, 38, 52, 70, 95, 130, 180]


def _glow_base(col, lvl):
    key = (col, lvl)
    b = _GLOW_BASE.get(key)
    if b:
        return b
    S = 48
    s = pygame.Surface((S, S))
    s.fill((0, 0, 0))
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - 23.5, y - 23.5) / 24.0
            if d >= 1.0:
                continue
            a = ((1.0 - d) ** 2.6) * lvl * .42
            if a <= 0.004:
                continue
            s.set_at((x, y), (min(255, int(col[0] * a)), min(255, int(col[1] * a)),
                              min(255, int(col[2] * a))))
    _GLOW_BASE[key] = s
    return s


def glow_at(dest, col, x, y, size, lvl=2, add=True):
    r = GLOW_R[-1]
    for cand in GLOW_R:
        if cand >= size * 0.5:
            r = cand
            break
    key = (col, r, lvl)
    surf = _GLOW_CACHE.get(key)
    if not surf:
        surf = pygame.transform.smoothscale(_glow_base(col, lvl), (r * 2, r * 2))
        _GLOW_CACHE[key] = surf
    dest.blit(surf, (int(x - r), int(y - r)), special_flags=pygame.BLEND_ADD if add else 0)

# ---------------------------------------------------------------- 音频
class Audio:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.master = 1.0
        self.sounds = {}
        self.bgm = None
        self.bgm_ch = None
        self.voice = {}
        self.voice_paths = {}
        self.voice_ch = None
        self.voice_t = 0.0
        self.voice_last = ''

    def boot(self):
        if HEADLESS:
            self.ok = False
            return
        try:
            pygame.mixer.pre_init(SR, -16, 1, 512)
            pygame.mixer.init()
        except Exception:
            self.ok = False
            return
        self.ok = True
        self._build()

    def set_master(self, v):
        self.master = clamp(float(v), 0.0, 1.0)
        if self.bgm_ch:
            try:
                self.bgm_ch.set_volume(0 if self.muted else self.master * .32)
            except Exception:
                pass

    def set_muted(self, muted):
        self.muted = bool(muted)
        if self.bgm_ch:
            try:
                self.bgm_ch.set_volume(0 if self.muted else self.master * .32)
            except Exception:
                pass

    def _tone(self, f0, dur, amp, f1=None, kind='sine', noise=0.0, attack=0.006):
        n = int(SR * dur)
        buf = array.array('h')
        phase = 0.0
        f1 = f0 if f1 is None else f1
        for i in range(n):
            p = i / max(1, n - 1)
            f = f0 * (1 - p) + f1 * p
            phase += 2 * math.pi * f / SR
            if kind == 'sine':
                v = math.sin(phase)
            elif kind == 'sq':
                v = 1.0 if math.sin(phase) > 0 else -1.0
            elif kind == 'saw':
                v = ((phase / (2 * math.pi)) % 1.0) * 2 - 1
            else:
                v = math.sin(phase)
            if noise:
                v += random.uniform(-1, 1) * noise
            env = min(1.0, (i / SR) / attack) * ((1 - p) ** 2)
            s = v * env * amp
            s = -1.0 if s < -1.0 else (1.0 if s > 1.0 else s)
            buf.append(int(s * 32767))
        return buf.tobytes()

    def _bed(self, dur=8.0):
        n = int(SR * dur)
        buf = array.array('h')
        for i in range(n):
            t = i / SR
            s = (math.sin(2 * math.pi * 48 * t) * .48
                 + math.sin(2 * math.pi * 73.5 * t) * .24
                 + math.sin(2 * math.pi * 110 * t) * .14)
            s *= .5 + .5 * math.sin(2 * math.pi * .09 * t)
            env = min(1.0, t / 1.2, (dur - t) / 1.2)
            s *= env * .10
            s = -1.0 if s < -1.0 else (1.0 if s > 1.0 else s)
            buf.append(int(s * 32767))
        return buf.tobytes()

    AUDIO_FILES = {
        'shoot': 'sfx_shoot.wav', 'shoot2': 'sfx_shoot2.wav', 'hit': 'sfx_hit.wav',
        'kill': 'sfx_kill.wav', 'big': 'sfx_big.wav', 'hurt': 'sfx_hurt.wav',
        'skill': 'sfx_skill.wav', 'pick': 'sfx_pick.wav', 'card': 'sfx_card.wav',
        'boss': 'sfx_boss.wav',
    }

    def _audio_dirs(self):
        return (asset_path('assets', 'audio'), os.path.join(data_dir(), 'audio_cache'))

    def _load_audio(self):
        """优先读取预生成 WAV；启动时不再用 Python 逐样本合成 8 秒音频。"""
        for d in self._audio_dirs():
            if not os.path.isdir(d):
                continue
            if not all(os.path.exists(os.path.join(d, fn)) for fn in self.AUDIO_FILES.values()):
                continue
            if not os.path.exists(os.path.join(d, 'bgm.wav')):
                continue
            try:
                for k, fn in self.AUDIO_FILES.items():
                    self.sounds[k] = pygame.mixer.Sound(os.path.join(d, fn))
                self.bgm = pygame.mixer.Sound(os.path.join(d, 'bgm.wav'))
                return True
            except Exception:
                self.sounds = {}
                self.bgm = None
        return False

    def _init_channels(self):
        self.bgm_ch = pygame.mixer.Channel(0)
        self.bgm_ch.set_volume(0 if self.muted else self.master * .32)
        self.bgm_ch.play(self.bgm, loops=-1)
        self.voice_ch = pygame.mixer.Channel(1)

    def _scan_voice(self):
        """语音只记录路径，第一次播报时才加载，避免启动时读 14 个大 WAV。"""
        self.voice_paths = {}
        vdir = asset_path('assets', 'voice')
        if os.path.isdir(vdir):
            for fn in sorted(os.listdir(vdir)):
                if fn.lower().endswith(('.wav', '.ogg')):
                    self.voice_paths[os.path.splitext(fn)[0]] = os.path.join(vdir, fn)

    def _persist_audio(self, payload, bed):
        """源码运行时没有缓存目录，就把合成结果写下来，下次启动直接读。"""
        try:
            d = os.path.join(data_dir(), 'audio_cache')
            os.makedirs(d, exist_ok=True)
            for k, data in payload.items():
                p = os.path.join(d, self.AUDIO_FILES[k])
                if not os.path.exists(p):
                    with wave.open(p, 'wb') as w:
                        w.setnchannels(1)
                        w.setsampwidth(2)
                        w.setframerate(SR)
                        w.writeframes(data)
            p = os.path.join(d, 'bgm.wav')
            if not os.path.exists(p):
                with wave.open(p, 'wb') as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(SR)
                    w.writeframes(bed)
        except Exception:
            pass

    def _build(self):
        try:
            if self._load_audio():
                self._init_channels()
                self._scan_voice()
                return
            payload = {
                'shoot': self._tone(1150, .06, .35, 430, 'sine'),
                'shoot2': self._tone(760, .07, .3, 260, 'sq'),
                'hit': self._tone(1600, .04, .25, 900, 'sine', noise=.4),
                'kill': self._tone(260, .2, .3, 70, 'sine', noise=.3),
                'big': self._tone(150, .5, .45, 36, 'sine', noise=.35),
                'hurt': self._tone(190, .3, .5, 48, 'sq', noise=.2),
                'skill': self._tone(120, .45, .45, 1500, 'sine'),
                'pick': self._tone(680, .12, .3, 1200, 'sine'),
                'card': self._tone(420, .16, .28, 640, 'sine'),
                'boss': self._tone(90, 1.0, .4, 44, 'saw', noise=.15),
            }
            bed = self._bed(8.0)
            for k, data in payload.items():
                self.sounds[k] = pygame.mixer.Sound(buffer=data)
            self.bgm = pygame.mixer.Sound(buffer=bed)
            self._init_channels()
            self._scan_voice()
            self._persist_audio(payload, bed)
        except Exception:
            self.ok = False

    def play(self, name, vol=1.0):
        if not self.ok or self.muted:
            return
        s = self.sounds.get(name)
        if s:
            s.set_volume(clamp(vol * self.master, 0, 1))
            s.play()

    def say(self, key, force=False):
        if not self.ok or self.muted or not META.get('voice', 1):
            return
        now = time.time()
        if not force and now - self.voice_t < .65 and self.voice_last == key:
            return
        lang = 'en' if META.get('lang', 0) else 'zh'
        vkey = '%s_%s' % (lang, key)
        s = self.voice.get(vkey)
        if s is None:
            path = self.voice_paths.get(vkey) or self.voice_paths.get('zh_' + key)
            if path:
                try:
                    s = pygame.mixer.Sound(path)
                    self.voice[vkey] = s
                except Exception:
                    s = None
        if not s or self.voice_ch is None:
            return
        self.voice_t = now
        self.voice_last = key
        try:
            self.voice_ch.stop()
            s.set_volume(clamp(self.master * .92, 0, 1))
            self.voice_ch.play(s)
        except Exception:
            pass

AUD = Audio()


def init_joystick():
    try:
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            j = pygame.joystick.Joystick(0)
            j.init()
            G.joy = j
            G.joy_name = j.get_name()
            return True
    except Exception:
        G.joy = None
        G.joy_name = ''
    return False


def apply_display(fullscreen):
    global SCREEN
    META['fullscreen'] = 1 if fullscreen else 0
    try:
        flags = pygame.FULLSCREEN if fullscreen else 0
        SCREEN = pygame.display.set_mode((W, H), flags)
    except Exception:
        pass


# ---------------------------------------------------------------- 存档
def app_dir():
    """游戏本体所在目录；绿色版的数据全部留在这里，不写 C 盘用户目录。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    d = os.path.join(app_dir(), 'saves')
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def save_file():
    p = os.environ.get('ABYSS_SAVE')
    if p:
        return p
    return os.path.join(data_dir(), 'save.json')


SLOT_COUNT = 3


def slot_file(slot):
    """每个存档槽一个独立文件，互不覆盖。"""
    return os.path.join(os.path.dirname(save_file()), 'slot%d.json' % (int(slot) + 1))


def _stamp():
    return time.strftime('%Y-%m-%d %H:%M')


def blank_profile():
    """一个全新存档的账号内进度；工坊与结晶都在这里，不跨槽共享。"""
    return {
        'shards': 0,
        'shards_total': 0,
        'upg': {},
        'intro_seen': 0,
        'runs': 0,
        'best_layer': 0,
        'best_score': 0,
        'created': _stamp(),
        'updated': _stamp(),
    }


def normalize_profile(p):
    q = blank_profile()
    if isinstance(p, dict):
        for k in q:
            if k in p and isinstance(p[k], type(q[k])):
                q[k] = p[k]
            elif k in p and k in ('shards', 'shards_total', 'intro_seen', 'runs', 'best_layer', 'best_score'):
                try:
                    q[k] = int(p[k])
                except Exception:
                    pass
        if isinstance(p.get('upg'), dict):
            q['upg'] = {k: max(0, int(v)) for k, v in p['upg'].items()
                        if k in UPG_BY_ID and isinstance(v, (int, float))}
    q['shards'] = max(0, int(q.get('shards', 0)))
    q['shards_total'] = max(q['shards'], int(q.get('shards_total', 0)))
    q['intro_seen'] = 1 if q.get('intro_seen') else 0
    q['runs'] = max(0, int(q.get('runs', 0)))
    q['best_layer'] = max(0, int(q.get('best_layer', 0)))
    q['best_score'] = max(0, int(q.get('best_score', 0)))
    return q


def new_slot_profile():
    """老版本全局结晶/工坊只迁移一次；之后每个新存档从零开始。"""
    p = blank_profile()
    if not META.get('slot_migrated', 0):
        p['shards'] = max(0, int(META.get('shards', 0) or 0))
        p['shards_total'] = p['shards']
        p['upg'] = dict(META.get('upg', {})) if isinstance(META.get('upg'), dict) else {}
        p['intro_seen'] = 0
        META['slot_migrated'] = 1
        save_meta()
    p = normalize_profile(p)
    return p


def slot_profile(slot):
    d = read_slot(slot)
    return normalize_profile(d.get('profile')) if d else None


def read_slot(slot):
    try:
        with open(slot_file(slot), 'r', encoding='utf-8') as f:
            d = json.load(f)
        if not isinstance(d, dict) or d.get('empty'):
            return None
        if not isinstance(d.get('profile'), dict):
            # v3.1 的扁平局内存档：补一个 profile，并视为已经看过序章
            p = new_slot_profile()
            p['intro_seen'] = 1
            d['profile'] = normalize_profile(p)
        else:
            d['profile'] = normalize_profile(d['profile'])
        if 'run_active' not in d:
            d['run_active'] = bool(d.get('ship') or d.get('layer'))
        return d
    except Exception:
        return None


def write_slot(slot, d):
    try:
        path = slot_file(slot)
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        try:
            if all(read_slot(i) for i in (0, 1, 2)):
                grant_ach('saves3')
        except Exception:
            pass
        return True
    except Exception:
        return False


def save_profile(slot, profile, clear_run=False):
    d = read_slot(slot) or {'empty': False, 'run_active': False}
    p = normalize_profile(profile)
    p['updated'] = _stamp()
    d['profile'] = p
    d['empty'] = False
    if clear_run:
        d = {'ver': VERSION, 'empty': False, 'run_active': False,
             'profile': p, 'updated': p['updated']}
    else:
        d['updated'] = p['updated']
    return write_slot(slot, d)


def slot_summary(slot):
    d = read_slot(slot)
    if not d:
        return None
    p = d.get('profile', blank_profile())
    return {
        'slot': int(slot),
        'ship': d.get('ship', 'echo'),
        'ship_name': d.get('ship_name', d.get('ship', '—')),
        'mode': int(d.get('mode', 0)),
        'diff': int(d.get('diff', 0)),
        'layer': int(d.get('layer', 1)),
        'wave': int(d.get('wave', 1)),
        'score': int(d.get('score', 0)),
        'time': float(d.get('time', 0)),
        'updated': d.get('updated', p.get('updated', '')),
        'ended': bool(d.get('ended', False)),
        'run_active': bool(d.get('run_active', False)),
        'profile': p,
    }



def diag_dir():
    return data_dir()


def report_crash(text):
    """把崩溃信息写进日志，并弹一个可截图的窗口，避免无控制台时无声退出。"""
    p = ''
    try:
        p = os.path.join(diag_dir(), 'crash.log')
        info = []
        try:
            info.append('pygame %s' % pygame.version.ver)
            info.append('video=%s' % pygame.display.get_driver())
            info.append('mixer=%s' % (pygame.mixer.get_init(),))
            surf = pygame.display.get_surface()
            info.append('screen=%s' % (surf.get_size() if surf else None))
        except Exception:
            pass
        with open(p, 'a', encoding='utf-8') as f:
            f.write('\n' + '=' * 60 + '\n')
            f.write(' '.join(info) + '\n')
            f.write(text + '\n')
    except Exception:
        p = ''
    try:
        import ctypes
        body = text.strip().splitlines()
        head = body[-1] if body else text[:200]
        msg = ('游戏出错了。把这段内容截图发给开发者即可定位：\n\n'
               + head[:300]
               + ('\n\n完整日志：\n' + p if p else ''))
        ctypes.windll.user32.MessageBoxW(0, msg, '深渊回廊 · 出错', 0x10)
    except Exception:
        pass

def load_meta():
    m = {'best_layer': 0, 'best_score': 0, 'runs': 0, 'kills': 0, 'diff': 0, 'mode': 0,
         'vol': .7, 'shake': 1, 'flash': 1, 'fullscreen': 0, 'aim': 0,
         'lang': 0, 'voice': 1, 'intro_seen': 0,
         'shards': 0, 'upg': {}, 'slot_migrated': 0,
         'best_by_diff': {}, 'ach': []}
    try:
        with open(save_file(), 'r', encoding='utf-8') as f:
            d = json.load(f)
        for k in m:
            if k == 'ach':
                if isinstance(d.get(k), list):
                    m[k] = [x for x in d[k] if isinstance(x, str)]
            elif k in d and isinstance(d[k], (int, float, dict)):
                m[k] = d[k]
        if not isinstance(m.get('best_by_diff'), dict):
            m['best_by_diff'] = {}
        m['mode'] = int(clamp(m.get('mode', 0), 0, len(MODES) - 1))
        m['diff'] = int(clamp(m.get('diff', 0), 0, len(DIFFS) - 1))
        m['vol'] = clamp(float(m.get('vol', .7)), 0, 1)
        m['shake'] = 1 if m.get('shake', 1) else 0
        m['flash'] = 1 if m.get('flash', 1) else 0
        m['fullscreen'] = 1 if m.get('fullscreen', 0) else 0
        m['aim'] = 1 if m.get('aim', 0) else 0
        m['lang'] = 1 if m.get('lang', 0) else 0
        m['voice'] = 1 if m.get('voice', 1) else 0
        m['intro_seen'] = 1 if m.get('intro_seen', 0) else 0
        m['slot_migrated'] = 1 if m.get('slot_migrated', 0) else 0
        m['shards'] = max(0, int(m.get('shards', 0) or 0))
        if not isinstance(m.get('upg'), dict):
            m['upg'] = {}
        else:
            m['upg'] = {k: max(0, int(v)) for k, v in m['upg'].items()
                        if k in UPG_BY_ID and isinstance(v, (int, float))}
        # 老存档（v1.x）没有分难度记录，把历史最好成绩归到巡航
        if not m['best_by_diff'] and m.get('best_layer', 0) > 0:
            m['best_by_diff']['0'] = {'layer': int(m['best_layer']),
                                     'score': int(m['best_score'])}
        # 把老存档已经达成的里程碑补成成就
        retro = []
        if m.get('runs', 0) > 0:
            retro.append('first_dive')
        if m.get('kills', 0) >= 100:
            retro.append('slayer')
        if m.get('best_layer', 0) >= 3:
            retro.append('deep3')
        if m.get('best_layer', 0) >= 6:
            retro.append('deep6')
        for aid in retro:
            if aid not in m['ach']:
                m['ach'].append(aid)
    except Exception:
        pass
    return m

def save_meta():
    try:
        with open(save_file(), 'w', encoding='utf-8') as f:
            json.dump(META, f, ensure_ascii=False)
    except Exception:
        pass

META = load_meta()


INTRO_PAGES = [
    ('第七码头。最后一次校准完成。\n\n深潜器「回声号」被缓缓推入黑色的水面。',
     'PIER SEVEN. Final calibration complete.\n\nThe diver ECHO is lowered into the black water.'),
    ('声呐第一次下探，回波却从更深的地方折返。\n\n海沟底部裂开了一道回廊，向下没有尽头。',
     'The first sonar pulse returns from something far below.\n\nA corridor has opened under the trench. It has no bottom.'),
    ('锈潮、菌沼、熔窟、镜城……\n\n二十八层异域，每一层都在重写自己。',
     'Rust Tide. Fungal Marsh. Molten Vault. Mirror City...\n\nTwenty-eight strata, each rewriting itself.'),
    ('你的任务只有一句：带回最深处的回声。\n\n或者，成为回声。',
     'Your order is one line: bring back the echo from the bottom.\n\nOr become the echo.'),
    ('下潜开始。\n\n活着回来。',
     'Dive.\n\nCome back alive.'),
]


def intro_page_text(page):
    pair = INTRO_PAGES[page]
    return L(pair[0], pair[1])



def L(zh, en):
    return en if META.get('lang', 0) else zh


def name_l(d):
    return d.get('en', d['name']) if META.get('lang', 0) else d['name']


def desc_l(d):
    return d.get('desc_en', d.get('desc', '')) if META.get('lang', 0) else d.get('desc', '')


# ---------------- 中英双语：所有界面文字统一从这里过一遍 ----------------
# 不逐行改绘制调用：在 text_img / text_w 里拦截，既保证按钮收字宽度一致，
# 也保证图鉴、提示、结算这些动态字符串不会漏翻。
_UI_EN = {
    '深渊回廊': 'ABYSS CORRIDOR',
    '回声回廊': 'ECHO CORRIDOR',
    '进入回廊': 'ENTER THE CORRIDOR',
    '开始下潜': 'START DIVE',
    '选择下潜器': 'SELECT DIVER',
    '系统设置': 'SYSTEM SETTINGS',
    '操作手册': 'FIELD MANUAL',
    '深渊档案': 'ARCHIVE',
    '设置': 'SETTINGS',
    '档案': 'ARCHIVE',
    '说明': 'MANUAL',
    '回声工坊': 'ECHO WORKSHOP',
    '工坊': 'WORKSHOP',
    '永久升级': 'PERMANENT UPGRADES',
    '回声结晶': 'ECHO SHARDS',
    '升级': 'UPGRADE',
    '已满级': 'MAXED',
    '返回标题': 'BACK TO TITLE',
    '选择一项永久升级，下一次下潜自动生效': 'Pick a permanent upgrade; it applies on the next dive',
    '击败敌机、抵达更深层、完成下潜都会获得回声结晶': 'Earn shards by clearing waves, descending, and finishing runs',
    '工坊升级只在下一局生效，不会消耗局内增幅': 'Workshop upgrades apply to the next run and never consume in-run augments',
    '返回': 'BACK',
    '继续': 'RESUME',
    '继续下潜': 'RESUME DIVE',
    '放弃本次': 'ABANDON RUN',
    '再次进入': 'DIVE AGAIN',
    '更换飞船': 'CHANGE SHIP',
    '下潜': 'DIVE',
    '上一页': '‹ PREV',
    '下一页': 'NEXT ›',
    '未解锁': 'LOCKED',
    '初始可用': 'STARTER',
    '初始': 'STARTER',
    '难度': 'DIFFICULTY',
    '模式': 'MODE',
    '选择增幅': 'SELECT AUGMENT',
    '已选': 'TAKEN',
    '按 1 / 2 / 3 或点击选择': 'PRESS 1 / 2 / 3 OR CLICK',
    '回声中断': 'SONAR PAUSED',
    '静默': 'SIGNAL LOST',
    '抵达回廊之底': 'THE END OF THE CORRIDOR',
    '急行通关': 'RUSH CLEARED',
    '猎王归途': 'HUNT COMPLETE',
    '再来一趟': 'DIVE AGAIN',
    '本层区域': 'LOCAL ZONE',
    '回廊事件': 'CORRIDOR EVENT',
    '增幅': 'AUGMENTS',
    '基础操作': 'BASIC CONTROLS',
    '局内成长': 'IN-RUN GROWTH',
    '设置与发行版': 'SETTINGS & BUILD',
    '四种模式': 'SIX MODES',
    '五种模式': 'SIX MODES',
    '六种模式': 'SIX MODES',
    '每层 BOSS 后三选一，收益与代价同时生效。':
        'After each boss, choose 1 of 3 pacts; boons and costs both apply.',
    '模式说明': 'MODES',
    '推荐增幅': 'RECOMMENDED AUGMENTS',
    '回廊记录': 'CORRIDOR RECORD',
    '最深': 'DEEPEST',
    '最高分': 'BEST SCORE',
    '出击': 'SORTIES',
    '尚未下潜': 'NO DIVE YET',
    '本局回廊事件': 'RUN MUTATOR',
    '本层区域事件': 'STRATUM EVENT',
    '随机回廊事件': 'RANDOM MUTATOR',
    '随机区域事件': 'RANDOM ZONE EVENT',
    '随机 Boss 顺序': 'RANDOM BOSS ORDER',
    '随机波次风格': 'RANDOM WAVE STYLE',
    '大地图探索': 'LARGE MAP EXPLORATION',
    '每局随机回廊事件 · 每层随机区域事件 · 随机 Boss 顺序 · 随机波次风格 · 大地图探索':
        'RANDOM MUTATOR · RANDOM ZONE EVENT · RANDOM BOSS ORDER · RANDOM WAVE STYLE · LARGE MAP',
    '仍未有记录': 'NO RECORD',
    '未检测到手柄': 'No controller detected',
    '已连接': 'CONNECTED',
    '手柄': 'CONTROLLER',
    '语言': 'LANGUAGE',
    '语音播报': 'VOICE LINES',
    '主音量': 'MASTER VOLUME',
    '屏幕震动': 'SCREEN SHAKE',
    '闪光强度': 'FLASH INTENSITY',
    '显示模式': 'DISPLAY MODE',
    '默认瞄准': 'DEFAULT AIM',
    '重新检测': 'DETECT',
    '开启': 'ON',
    '关闭': 'OFF',
    '全屏': 'Fullscreen',
    '窗口': 'Windowed',
    '自动索敌': 'Auto-aim',
    '鼠标瞄准': 'Mouse',
    '旅行者': 'VOYAGER',
    '巡航': 'CRUISE',
    '深渊': 'ABYSS',
    '噩梦': 'NIGHTMARE',
    '远航': 'VOYAGE',
    '无尽': 'ENDLESS',
    '急行': 'RUSH',
    '猎王': 'HUNT',
    '每日': 'DAILY',
    '契约': 'PACT',
    '常见': 'COMMON',
    '稀有': 'RARE',
    '传说': 'LEGENDARY',
    '飞船': 'SHIPS',
    '敌机': 'ENEMIES',
    '绝技一': 'SIG I',
    '绝技二': 'SIG II',
    '第二阶段解锁第二绝技，第三阶段双绝技连携':
        'Tier 2 unlocks Sig II · Tier 3 links both signatures',
    '第 %d 层王座': 'THRONE OF STRATUM %d',
    '王座': 'THRONE',
    'BOSS': 'BOSS',
    '未连接手柄（支持 Xbox / DS4 标准映射）':
        'No controller (Xbox / DS4 standard mapping supported)',
    'SELECT DIVER  ·  已解锁 %d / %d': 'SELECT DIVER  ·  UNLOCKED %d / %d',
    'Tab 切换难度': 'Tab: switch difficulty',
    '上下键 切换  ·  1-6 切模式  ·  PgUp / PgDn 翻页  ·  Enter 进入':
        'UP/DOWN select  ·  1-6 mode  ·  PgUp / PgDn page  ·  Enter dive',
    '艇体': 'HULL',
    '速度': 'SPEED',
    '伤害': 'DAMAGE',
    '射速': 'RATE',
    '穿透': 'PIERCE',
    '弹道': 'SHOTS',
    '技能': 'SKILL',
    '推荐增幅': 'RECOMMENDED AUGMENTS',
    '本局回廊事件 · 每局随机（Boss 顺序与波次风格同样随机）':
        'RUN MUTATOR · randomized each dive (boss order and wave style too)',
    '‹ 上一页': '‹ PREV',
    '下一页 ›': 'NEXT ›',
    '未解锁': 'LOCKED',
    '通关第 %d 层后开放': 'UNLOCKED AFTER STRATUM %d',
    '第 %d 层解锁': 'UNLOCK AT STRATUM %d',
    '初始可用': 'STARTER',
    '本层区域 · %s    %s': 'LOCAL ZONE · %s    %s',
    '回廊事件 · %s    %s    SEED %06X': 'MUTATOR · %s    %s    SEED %06X',
    'SONAR PAUSED  ·  %s  ·  %s  ·  第 %d 层 第 %d 波':
        'SONAR PAUSED  ·  %s  ·  %s  ·  STRATUM %d WAVE %d',
    '鼠标瞄准  ·  T 切换自动索敌  ·  空格 / 手柄 A / RT 释放技能':
        'Mouse aim  ·  T toggles auto-aim  ·  SPACE / pad A / RT casts skill',
    'ESC 继续  ·  手柄 B / Start 继续': 'ESC resume  ·  pad B / Start resume',
    '按 1 / 2 / 3 或点击选择': 'PRESS 1 / 2 / 3 OR CLICK',
    '第 %d 层结束 · 艇体回升': 'STRATUM %d CLEARED · HULL RESTORED',
    '第 %d 层 · 战斗间隙': 'STRATUM %d · BETWEEN WAVES',
    '回廊记录 · %s · %s': 'RECORD · %s · %s',
    'PLAY': 'PLAY',
    '层数': 'DEPTH',
    '得分': 'SCORE',
    '击杀': 'KILLS',
    '连击': 'COMBO',
    '用时': 'TIME',
    '增幅': 'AUGMENTS',
    '第 %d 层': 'STRATUM %d',
    '第 %d 波': 'WAVE %d',
    '第 %d 层王座': 'THRONE OF STRATUM %d',
    '未连接手柄（支持 Xbox / DS4 标准映射）':
        'No controller (Xbox / DS4 standard mapping supported)',
    '回廊从海沟底下裂开，向下没有尽头。\n锈潮、菌沼、熔窟、镜城、冻原、机冢、数据雨、归墟、\n回廊之核、血潮、星骸、白洞、霓虹雨、灰烬海、终焉之门、虚空花园、\n时间残骸、深渊之底、星海墓场、熔核、回廊尽头、静默深空、创世熔炉、门后、\n盐霜圣堂、齿轮海沟、虚数潮、终末之眼——\n二十八层，每层都是一张大地图；六种模式：远航 / 无尽 / 急行 / 猎王 / 每日 / 契约。':
        'The corridor opened under the trench. There is no bottom.\n'
        '28 strata, each a large map. Six modes:\n'
        'VOYAGE / ENDLESS / RUSH / HUNT / DAILY / PACT.\n'
        'Every dive rerolls events, bosses and waves.',
    'Enter / 点击开始   ·   方向键 ← → 切换难度   ·   模式在选船页切换':
        'Enter / click to start   ·   ← → difficulty   ·   modes are chosen on the diver screen',
    'WASD / 左摇杆 移动    鼠标 / 右摇杆 瞄准    T 自动索敌    空格 / A 技能    Shift 减速    ESC 暂停    M 静音    F11 全屏    O 设置    C 档案    H 说明':
        'WASD / left stick MOVE   mouse / right stick AIM   T auto-aim   SPACE / A skill   Shift slow   ESC pause   M mute   F11 fullscreen   O settings   C archive   H manual',
    'FIELD MANUAL  ·  第一次下潜前看一遍就够': 'FIELD MANUAL  ·  one read before your first dive is enough',
    'WASD / 左摇杆': 'WASD / LEFT STICK',
    '移动；Shift / LB 减速，便于穿弹。': 'Move. Shift / LB slows you down for bullet weaving.',
    '鼠标 / 右摇杆': 'MOUSE / RIGHT STICK',
    '决定船头方向，主炮与光束跟随船头。': 'Sets the nose. Guns and beams follow the nose.',
    '自动开火': 'AUTO FIRE',
    '主炮持续射击，不需要按住鼠标。': 'Main guns fire continuously. No trigger to hold.',
    '空格 / A / RT': 'SPACE / A / RT',
    '释放飞船技能。': 'Cast the ship skill.',
    'T / 手柄 Y': 'T / PAD Y',
    '切换鼠标瞄准与自动索敌。': 'Switch between mouse aim and auto-aim.',
    'ESC / Start': 'ESC / START',
    '暂停；暂停里可看档案、设置和说明。': 'Pause; archive, settings and manual are available there.',
    'M / F11': 'M / F11',
    '静音 / 切换全屏。': 'Mute / toggle fullscreen.',
    '击杀与拾取': 'KILLS & PICKUPS',
    '敌机掉落回声，靠近自动吸收。': 'Enemies drop echoes; get close to vacuum them in.',
    '三选一增幅': 'PICK 1 OF 3',
    '每波结束选择一张卡，构筑本局。': 'After every wave, take one card and build the run.',
    'BOSS 双绝技': 'BOSS SIGNATURES',
    '第二阶段解锁第二绝技，第三阶段连携。': 'Tier 2 unlocks the second signature; Tier 3 links both.',
    '护盾': 'SHIELDS',
    '优先吸收伤害；护盾清空后才扣艇体。': 'Shields eat damage first; only then does the hull take hits.',
    '危险感知': 'DANGER SENSE',
    '低血量时画面边缘变红，别硬吃弹。': 'At low hull the screen edges turn red. Do not eat that volley.',
    '主音量、震动、闪光、全屏、默认瞄准都可调；': 'Master volume, shake, flash, fullscreen and default aim are adjustable;',
    '设置即时写入本地存档，不会影响已有记录。': 'settings save locally and never touch your existing records.',
    '28 层完整回廊，标准流程。': '28 strata, the full corridor. Standard run.',
    '越过 28 层后循环主题，直到静默。': 'Past stratum 28 the themes loop until silence.',
    '12 层、每层 3 波，高压速通。': '12 strata, 3 waves each. High-pressure speedrun.',
    '12 层，每层直接进 BOSS 战。': '12 strata, straight into a boss every stratum.',
    '每日固定种子，和大家跑同一条回廊。': 'A fixed daily seed. Everyone runs the same corridor.',
    '已连接：': 'CONNECTED: ',
    '手柄：左摇杆移动 · 右摇杆瞄准 · A / RT 技能 · Y 自动索敌 · Start 暂停。':
        'PAD: left stick move · right stick aim · A / RT skill · Y auto-aim · Start pause.',
    '数据来自当前版本，随内容更新自动扩充': 'Data from the current build; expands as content grows',
    'ARCHIVE  ·  数据来自当前版本，随内容更新自动扩充':
        'ARCHIVE  ·  data from the current build; expands as content grows',
    'AI 自动瞄准': 'AI AUTO-AIM',
    '鼠标瞄准': 'MOUSE AIM',
    '手柄已连接：右摇杆瞄准 · A / RT 技能 · Y 自动索敌':
        'Controller connected: right stick aim · A / RT skill · Y auto-aim',
    '首次下潜：WASD 移动 · 鼠标瞄准 · 自动开火 · 空格技能 · ESC 暂停后可看说明':
        'First dive: WASD move · mouse aim · auto fire · SPACE skill · ESC pause opens the manual',
    '重创！': 'CRITICAL HIT!',
    '备用核心启动 · 你还没有死透': 'BACKUP CORE ONLINE · not dead yet',
    '档案更新': 'ARCHIVE UPDATED',
    '版本 v%s  ·  桌面发行版  ·  ESC / B 返回' % VERSION:
        'v%s  ·  DESKTOP RELEASE  ·  ESC / B BACK' % VERSION,
}
_TR_ALL = dict(_UI_EN)
_TR_READY = False
_TR_CONTENT = {}

# v3.2：补齐长尾内容的英文名，避免英文界面里残留中文
_MORE_EN = {
    # 成就
    '初次下潜': 'FIRST DIVE', '百人斩': 'CENTURY KILL', '连击狂潮': 'COMBO FRENZY',
    '增幅收藏家': 'AUGMENT COLLECTOR', '锈潮之下': 'BENEATH THE RUST',
    '穿过机冢': 'THROUGH THE MACHINE TOMB', '噩梦生还': 'NIGHTMARE SURVIVOR',
    '全舰队': 'FULL FLEET', '白洞尽头': "WHITE HOLE'S END", '增幅洪流': 'AUGMENT FLOOD',
    '增幅狂潮': 'AUGMENT FRENZY', '增幅风暴': 'AUGMENT STORM',
    '五百葬场': 'FIVE HUNDRED GRAVES', '千机葬场': 'THOUSAND GRAVES',
    '增幅深渊': 'AUGMENT ABYSS', '千五葬场': 'FIFTEEN HUNDRED GRAVES',
    '门后之物': 'WHAT LIES BEYOND', '两千五葬场': 'TWENTY-FIVE HUNDRED GRAVES',
    '无尽十层': 'ENDLESS TEN', '无尽二十层': 'ENDLESS TWENTY',
    '越界者': 'BOUNDARY BREAKER', '没有尽头': 'NO END',
    '猎王归位': "HUNTER'S RETURN", '回廊档案员': 'CORRIDOR ARCHIVIST',
    '按手册操作': 'BY THE MANUAL', '校准完成': 'CALIBRATION COMPLETE',
    '王座研究者': 'THRONE RESEARCHER', '增幅研究者': 'AUGMENT RESEARCHER',
    '今日回声': "TODAY'S ECHO", '今日下潜': "TODAY'S DIVE",
    '双语潜航': 'BILINGUAL DIVE', '回声频道': 'ECHO CHANNEL',
    '轮回者': 'CYCLER', '回声工程师': 'ECHO ENGINEER',
    '工坊大师': 'WORKSHOP MASTER', '结晶收藏': 'SHARD COLLECTOR',
    '结晶富翁': 'SHARD TYCOON', '全模块校准': 'FULL CALIBRATION',
    '结晶之海': 'SHARD SEA', '结晶汪洋': 'SHARD OCEAN',
    '三线潜航': 'THREE-LINE DIVE', '全员集结': 'ALL HANDS',
    '契约收藏家': 'PACT COLLECTOR', '契约深渊': 'PACT ABYSS',
    '契约履行': 'PACT KEPT', '五千葬场': 'FIVE THOUSAND GRAVES',
    '百层回廊': 'HUNDRED-STRATUM CORRIDOR',
    # 突变
    '盐霜回廊': 'SALT-FROST CORRIDOR', '齿轮回廊': 'GEAR CORRIDOR',
    '虚数回廊': 'IMAGINARY CORRIDOR', '终末回廊': 'FINAL CORRIDOR',
    '庇护回廊': 'SHELTER CORRIDOR', '棱镜回廊': 'PRISM CORRIDOR',
    '超跑回廊': 'OVERRUN CORRIDOR', '丰收回廊': 'HARVEST CORRIDOR',
    # 层事件
    '脉冲星带': 'PULSAR BELT', '护盾雨': 'SHIELD RAIN', '超载井': 'OVERLOAD WELL',
    '浓雾带': 'FOG BANK', '血潮带': 'BLOOD TIDE', '金瞳区': 'GOLDEN EYE',
    '静核区': 'QUIET CORE', '镜雨区': 'MIRROR RAIN',
    # 增幅名称（长尾补齐）
    '时间淤滞': 'TIME DILATION', '低温弹': 'CRYO ROUND', '跳弹': 'RICOCHET ROUND',
    '再生护盾': 'REGEN SHIELD', '生物寄生': 'BIO PARASITE', '双重射击': 'DOUBLE SHOT',
    '深潜代谢': 'DEEP METABOLISM', '湮灭弹': 'ANNIHILATION ROUND', '内爆': 'IMPLOSION',
    '玻璃大炮': 'GLASS CANNON', '环绕卫星': 'ORBIT SATELLITE',
    '连锁放电': 'CHAIN DISCHARGE', '燃烧弹': 'INCENDIARY ROUND',
    '镜面分裂': 'MIRROR SPLIT', '背水一战': 'LAST STAND', '相位装甲': 'PHASE ARMOR',
    '暴击强化': 'CRIT AMP', '荆棘护体': 'THORN GUARD', '纳米修复': 'NANO REPAIR',
    '缠滞力场': 'STASIS FIELD', '巨型弹芯': 'MASSIVE CORE', '备用核心': 'SPARE CORE',
    '幸运罗盘': 'LUCKY COMPASS', '技能强化': 'SKILL AMP', '处决弹': 'EXECUTION ROUND',
    '余烬尾迹': 'EMBER TRAIL', '相位跃迁': 'PHASE JUMP', '长矛弹': 'LANCE ROUND',
    '母巢协议': 'HIVE PROTOCOL', '赌徒筹码': 'GAMBLER CHIP', '过载核心': 'OVERLOAD CORE',
    '冷却矩阵': 'COOLANT MATRIX', '先手校准': 'FIRST-STRIKE CALIBRATION',
    '溢出爆裂': 'OVERFLOW BURST', '战利护盾': 'SPOILS SHIELD', '扇面发射': 'FAN ARRAY',
    '回收修复': 'SALVAGE REPAIR', '暴击内爆': 'CRIT IMPLOSION',
    '灵魂配额': 'SOUL QUOTA', '受伤反击': 'PAIN COUNTER', '临界过载': 'CRITICAL OVERLOAD',
    '霜蚀': 'FROST EROSION', '弑主者': 'SOVEREIGN SLAYER', '极速扳机': 'RAPID TRIGGER',
    '轻量艇体': 'LIGHT HULL', '复合装甲': 'COMPOSITE ARMOR', '精密瞄准': 'PRECISION AIM',
    '高燃弹头': 'HIGH-OCTANE WARHEAD', '冻蚀弹头': 'CRYO WARHEAD',
    '寻的模块': 'HOMING MODULE', '重型弹体': 'HEAVY BODY', '终局处决': 'FINAL EXECUTION',
    '护盾发生器': 'SHIELD GENERATOR', '疾行推进': 'RUSH THRUSTER', '大口径': 'LARGE BORE',
    '暴击核心': 'CRIT CORE', '厚壳装甲': 'THICK SHELL', '引力拾取': 'GRAVITY PICKUP',
    '护盾核心': 'SHIELD CORE', '贯穿弹芯': 'PIERCING CORE',
    '轨道卫星': 'ORBITAL SATELLITE', '爆裂核心': 'BURST CORE', '超速弹芯': 'HYPER CORE',
    '处决协议': 'EXECUTION PROTOCOL', '超压弹头': 'OVERPRESSURE WARHEAD',
    '自动装填': 'AUTO-LOADER', '硬化艇壳': 'HARDENED HULL', '幸运回路': 'LUCKY CIRCUIT',
    '灵魂追缴': 'SOUL COLLECTION', '汲取装甲': 'SIPHON ARMOR', '链式雷暴': 'CHAIN STORM',
    '轨道增援': 'ORBITAL REINFORCEMENT', '反射甲片': 'REFLECT PLATE',
    '再生膜': 'REGEN MEMBRANE', '回旋刃': 'BOOMERANG BLADE', '追踪雷': 'TRACKING MINE',
    '环绕刃': 'ORBIT BLADE', '散射炮': 'SCATTER CANNON', '分裂弹': 'SPLIT ROUND',
    '寻敌弹头': 'SEEKER WARHEAD', '高速弹道': 'HYPER BALLISTICS',
    '穿甲弹芯': 'ARMOR-PIERCE CORE', '冻结弹头': 'FREEZE WARHEAD',
    '燃烧弹头': 'BURN WARHEAD', '冲击弹头': 'IMPACT WARHEAD', '活体装甲': 'LIVING ARMOR',
    '蜂群增援': 'SWARM REINFORCEMENT', '尖刺装甲': 'SPIKE ARMOR', '幸运齿轮': 'LUCKY GEAR',
    '虚空长矛': 'VOID LANCE', '超驱引擎': 'OVERDRIVE ENGINE', '三叉戟': 'TRIDENT',
    '日冕火种': 'CORONA EMBER', '霜核': 'FROST CORE', '寻猎弹头': 'HUNT SEEKER',
    '收割者': 'REAPER', '堡垒膜': 'BULWARK MEMBRANE', '蜂群协议': 'SWARM PROTOCOL',
    '切割环': 'CUTTING RING', '命运准星': 'FATE RETICLE', '折射涂层': 'REFRACTION COATING',
    '超频枪机': 'OVERCLOCKED ACTION', '长管加速': 'LONG BARREL', '攻城弹': 'SIEGE ROUND',
    '破片套件': 'FRAGMENT KIT', '磁轨套件': 'RAIL KIT', '魂火': 'SOULFIRE',
    '霜新星': 'FROST NOVA', '第三环刃': 'THIRD BLADE', '链式电弧': 'CHAIN ARC',
    '腐蚀光环': 'CORROSION AURA', '先手猎杀': 'FIRST HUNT', '豪赌筹码': 'HIGH ROLLER',
    '弑王弹头': 'KING SLAYER WARHEAD', '深潜磁石': 'DEEP MAGNET',
    '老练装填': 'VETERAN RELOAD', '超载弹头': 'OVERLOAD WARHEAD',
    '循环供弹': 'LOOP FEED', '聚焦准星': 'FOCUS RETICLE', '弱点标记': 'WEAKPOINT MARK',
    '齐射阵列': 'VOLLEY ARRAY', '双层钻头': 'DOUBLE DRILL', '顺流推进': 'CURRENT THRUSTER',
    '深渊红利': 'ABYSS DIVIDEND', '自愈凝胶': 'SELF-HEAL GEL', '神盾回路': 'AEGIS CIRCUIT',
    '散热旁路': 'HEAT SINK BYPASS', '猎王校准': 'BOSS CALIBRATION',
    '虚空烙印': 'VOID BRAND', '助燃剂': 'ACCELERANT', '命运编织': 'FATE WEAVE',
    '护盾编织': 'SHIELD WEAVE', '血契': 'BLOOD PACT', '暮色回路': 'EVENTIDE CIRCUIT',
    '集束阵列': 'CLUSTER ARRAY', '超跑推进': 'OVERRUN THRUSTER', '锁定协议': 'TARGET LOCK',
    '四重穿透': 'QUAD PIERCE', '余烬弹头': 'EMBER WARHEAD', '霜纹弹头': 'RIME WARHEAD',
    '重力井弹': 'GRAVITY WELL', '回收矩阵': 'RECLAIM MATRIX', '终言弹': 'LAST WORD',
    '反击甲片': 'COUNTER PLATE',
    # 成就描述
    '完成一次出击': 'Complete one sortie', '累计击毁 100 架敌机': 'Destroy 100 enemies total',
    '单局打出 50 连击': 'Reach a 50 combo in one run',
    '单局拿到 15 个增幅': 'Collect 15 augments in one run',
    '抵达第 3 层': 'Reach stratum 3', '抵达第 6 层': 'Reach stratum 6',
    '通关任意难度': 'Clear any difficulty', '在噩梦难度通关': 'Clear on Nightmare',
    '解锁全部下潜器': 'Unlock all divers',
    '抵达第 9 层': 'Reach stratum 9', '抵达第 12 层': 'Reach stratum 12',
    '抵达第 15 层': 'Reach stratum 15', '抵达第 18 层': 'Reach stratum 18',
    '单局拿到 25 个增幅': 'Collect 25 augments in one run',
    '单局拿到 40 个增幅': 'Collect 40 augments in one run',
    '单局拿到 60 个增幅': 'Collect 60 augments in one run',
    '单局击毁 500 架敌机': 'Destroy 500 enemies in one run',
    '单局击毁 1000 架敌机': 'Destroy 1000 enemies in one run',
    '抵达第 21 层': 'Reach stratum 21',
    '单局拿到 80 个增幅': 'Collect 80 augments in one run',
    '单局击毁 1500 架敌机': 'Destroy 1500 enemies in one run',
    '抵达第 24 层': 'Reach stratum 24',
    '单局拿到 100 个增幅': 'Collect 100 augments in one run',
    '单局击毁 2500 架敌机': 'Destroy 2500 enemies in one run',
    '在无尽模式抵达第 10 层': 'Reach stratum 10 in Endless',
    '在无尽模式抵达第 20 层': 'Reach stratum 20 in Endless',
    '在无尽模式抵达第 30 层': 'Reach stratum 30 in Endless',
    '在无尽模式抵达第 50 层': 'Reach stratum 50 in Endless',
    '通关 12 层急行模式': 'Clear 12 strata in Rush',
    '通关 12 层猎王模式': 'Clear 12 strata in Hunt',
    '打开深渊档案': 'Open the Abyss Archive', '打开操作手册': 'Open the manual',
    '修改任意一项设置': 'Change any setting',
    '查看 BOSS 档案': 'View a BOSS archive entry',
    '查看增幅档案': 'View an augment archive entry',
    '通关每日回廊': 'Clear the Daily Corridor', '进入每日回廊': 'Enter the Daily Corridor',
    '切换界面语言': 'Switch UI language', '开启语音播报': 'Enable voice narration',
    '在无尽模式进入第二轮主题': 'Reach the second theme cycle in Endless',
    '在回声工坊购买一次永久升级': 'Buy a permanent upgrade in the Echo Workshop',
    '把任意一项永久升级点满': 'Max out any permanent upgrade',
    '持有 100 枚回声结晶': 'Hold 100 Echo Shards',
    '持有 300 枚回声结晶': 'Hold 300 Echo Shards',
    '持有 500 枚回声结晶': 'Hold 500 Echo Shards',
    '持有 800 枚回声结晶': 'Hold 800 Echo Shards',
    '所有永久升级至少 1 级': 'Every permanent upgrade at least level 1',
    '抵达第 28 层': 'Reach stratum 28',
    '建立 3 个独立存档': 'Create 3 independent saves',
    '解锁全部 40 艘下潜器': 'Unlock all 40 divers',
    '签订 5 份深渊契约': 'Sign 5 abyss pacts',
    '签订 10 份深渊契约': 'Sign 10 abyss pacts',
    '通关契约模式': 'Clear Pact mode',
    '单局击毁 5000 架敌机': 'Destroy 5000 enemies in one run',
    '在无尽模式抵达第 100 层': 'Reach stratum 100 in Endless',
    # 突变长尾描述
    '开局随机获得一件增幅': 'Start with a random augment',
    '持续缓慢回血，敌人艇体 +18%': 'Slow hull regen, enemy hull +18%',
    # v3.5 重命名内容
    '星流带': 'STAR CURRENT BELT', '日蚀带': 'ECLIPSE BELT', '幸运矿脉': 'LUCKY VEIN',
    '冷却导管': 'COOLANT DUCT', '自愈纤维': 'SELF-HEAL FIBER', '活体修补': 'LIVING PATCH',
    '燃焰弹芯': 'FLARE CORE', '冻蚀弹芯': 'CRYO CORE', '跳弹镀层': 'RICOCHET PLATING',
    '护盾阵列': 'SHIELD ARRAY', '猎杀协议': 'HUNT PROTOCOL',
}


def _build_tr_content():
    global _TR_READY
    needed = ('SHIP_I18N', 'SHIPS', 'BOSSCFG', 'LAYER_THEME', '_THEME_SUFFIX', 'ENEMY_NAMES', 'ENEMY_EN')
    if any(n not in globals() for n in needed):
        return
    _TR_READY = True
    # 飞船：名字 / 定位 / 技能 / 描述
    for sid, (nm, role, skill, desc) in SHIP_I18N.items():
        s = next((x for x in SHIPS if x['id'] == sid), None)
        if not s:
            continue
        _TR_ALL[s['name']] = nm
        _TR_ALL[s['role']] = role
        _TR_ALL[s['skill']] = skill
        _TR_ALL[s['desc']] = desc
    for b in BOSSCFG:
        _TR_ALL[b['name']] = b['en']
    for i, n in enumerate(BOSS_SIG_NAMES):
        _TR_ALL[n] = _BOSS_SIG_EN.get(n, n)
    for i, n in enumerate(BOSS_SIG2_NAMES):
        _TR_ALL[n] = _BOSS_SIG2_EN.get(n, n)
    for t in LAYER_THEME:
        _TR_ALL[t['name']] = t['en']
        for suf in _THEME_SUFFIX:
            _TR_ALL[t['name'] + '·' + suf] = t['en'] + ' · ' + {'回响': 'ECHO', '余烬': 'EMBER',
                                                                '逆潮': 'REVERSE', '深潜': 'DEEP',
                                                                '耳鸣': 'TINNITUS'}.get(suf, suf)
    for k, v in ENEMY_EN.items():
        if k in ENEMY_NAMES:
            _TR_ALL[ENEMY_NAMES[k]] = v
    for d in DIFFS:
        _TR_ALL[d['desc']] = d.get('desc_en', d['desc'])
    for d in MODES:
        _TR_ALL[d['desc']] = d.get('desc_en', d['desc'])
    for p in PACTS:
        _TR_ALL[p['name']] = p['en']
        _TR_ALL[p['desc']] = p.get('desc_en', p['desc'])
    for m in MUTS:
        _TR_ALL[m['name']] = _MUT_EN.get(m['name'], m['name'])
        _TR_ALL[m['desc']] = _stat_en(m['desc'])
    for w in WAVE_TAGS:
        if w['name']:
            _TR_ALL[w['name']] = _WAVE_EN.get(w['name'], w['name'])
    for e in LAYER_EVENTS:
        _TR_ALL[e['name']] = _EV_EN.get(e['name'], e['name'])
        _TR_ALL[e['desc']] = _stat_en(e['desc'])
    for zh, en in (('战斗间隙', 'BETWEEN WAVES'), ('就绪', 'READY'),
                   ('第二阶段解锁', 'UNLOCKS AT PHASE II'),
                   ('护航', 'ESCORT'), ('刺客', 'ASSASSIN'), ('堡垒', 'FORTRESS'), ('星网', 'STAR NET'),
                   ('星槎', 'STARFERRY'), ('蚀影', 'ECLIPSE'), ('磐舟', 'BULWARK'), ('织星', 'WEAVER'),
                   ('星图校准', 'STAR CHART CALIBRATION'), ('暗面突袭', 'DARK SIDE RAID'),
                   ('磐石展开', 'BULWARK DEPLOY'), ('星网奇点', 'STAR NET SINGULARITY'),
                   ('第二阶段解锁第二绝技，第三阶段双绝技连携',
                    'Tier 2 unlocks the second signature; Tier 3 links both.')):
        _TR_ALL[zh] = en
    for a in AUGS:
        _TR_ALL[a[2]] = _aug_en(a)
    for zh, en in _AUG_NAME_EN.items():
        _TR_ALL[zh] = en
    for v in FLAVOR.values():
        _TR_ALL.setdefault(v, '')
    _TR_ALL.update(_MORE_EN)


_AUG_NAME_EN = {
    '僚机': 'WINGMAN', '冲击波': 'SHOCKWAVE', '冷却回路': 'COOLANT LOOP',
    '分叉弹道': 'SPLIT PATH', '制导弹头': 'HOMING WARHEAD', '备用舱段': 'SPARE HULL',
    '弱点扫描': 'WEAKPOINT SCAN', '快速循环': 'QUICK CYCLE', '流体力学': 'HYDRODYNAMICS',
    '磁力回收': 'MAGNETIC SALVAGE', '穿透弹芯': 'PENETRATOR CORE',
    '过热弹头': 'OVERHEAT WARHEAD',
    '嗜血弹头': 'BLOODLUST WARHEAD', '磁轨弹芯': 'RAIL CORE', '磁轨炮': 'RAIL CANNON',
    '寒霜力场': 'FROST FIELD', '致命准星': 'DEADEYE RETICLE',
    '汲能线圈': 'SIPHON COIL', '贪婪': 'GREED', '远距校准': 'LONG-RANGE CALIBRATION',
    '穿甲钻头': 'PENETRATOR DRILL', '玻璃炮': 'GLASS CANNON', '跳弹涂层': 'RICOCHET COATING',
    '护盾爆裂': 'SHIELD BURST', '超频弹道': 'OVERCLOCK PATH',
    '侧舷齐射': 'BROADSIDE', '磁力拾取': 'MAGNETIC PICKUP', '轻质框架': 'LIGHT FRAME',
    '精算火控': 'PRECISION FIRE CONTROL', '贴脸火力': 'POINT-BLANK FIREPOWER',
    '超频供弹': 'OVERCLOCKED FEED',
    '虚空引擎': 'VOID ENGINE', '回声心脏': 'ECHO HEART', '蜂群之魂': 'SWARM SOUL',
    '绯红弹头': 'CRIMSON WARHEAD', '冰川弹芯': 'GLACIER CORE', '风暴线圈': 'TEMPEST COIL',
    '神盾矩阵': 'AEGIS MATRIX', '猎王视界': 'HUNTER VISION', '终光': 'LAST LIGHT',
    '镜核': 'MIRROR CORE', '超磁轨': 'HYPER RAIL', '幸运刃': 'FORTUNE BLADE',
}


_MUT_EN = {
    '静默带': 'SILENT BELT', '富集层': 'RICH STRATA', '密集回响': 'DENSE ECHO',
    '精英潮': 'ELITE TIDE', '深压带': 'PRESSURE BELT', '电子风暴': 'ION STORM',
    '遗骸场': 'WRECK FIELD', '无声猎场': 'SILENT HUNT', '急流': 'TORRENT',
    '古菌层': 'ANCIENT BLOOM', '长夜回廊': 'LONG NIGHT', '猎场协议': 'HUNT PROTOCOL',
    '脆壳层': 'FRAGILE SHELL', '悬赏回廊': 'BOUNTY RUN', '蜂拥层': 'SWARM LAYER',
    '薄壳层': 'THIN SHELL', '幸运回廊': 'LUCKY RUN', '静默回廊': 'SILENT RUN',
    '狂潮回廊': 'FRENZY RUN', '真空回廊': 'VACUUM RUN', '血偿回廊': 'BLOOD PACT',
    '星落回廊': 'STARFALL', '熔核回廊': 'MOLTEN CORE', '回声回廊': 'ECHO RUN',
    '超载回廊': 'OVERDRIVE', '蜂群回廊': 'HIVE RUN', '潮汐回廊': 'TIDE RUN',
    '静水回廊': 'STILL WATER', '超频回廊': 'OVERCLOCK', '铁壁回廊': 'IRON WALL',
    '幻影回廊': 'PHANTOM', '拾荒回廊': 'SCAVENGER', '噩梦回廊': 'NIGHTMARE',
    '重装回廊': 'JUGGERNAUT', '狂怒回廊': 'FURY', '弃子回廊': 'GAMBIT',
    '时序乱流': 'TIME SLIP', '红线回廊': 'REDLINE', '霜蚀回廊': 'FROSTBITE',
    '头奖回廊': 'JACKPOT', '双子回廊': 'TWIN', '深静回廊': 'DEEP QUIET',
    '镜约回廊': 'MIRROR PACT', '墓风回廊': 'GRAVE WIND', '耀斑回廊': 'SOLAR FLARE',
    '深潜回廊': 'DEEP DIVE', '回声叠层': 'ECHO STACK', '余烬回廊': 'CINDER',
    '深渊回廊': 'ABYSS RUN', '风暴前沿': 'STORM FRONT', '雷暴回廊': 'THUNDER RUN',
    '烈阳回廊': 'SOLAR RUN', '墓园回廊': 'GRAVEYARD RUN', '零度回廊': 'ZERO RUN',
    '烬火回廊': 'EMBER RUN',
    '蜃景回廊': 'MIRAGE RUN', '铁潮回廊': 'IRON TIDE RUN', '塞壬回廊': 'SIREN RUN',
    '裂隙回廊': 'FRACTURE RUN', '蝗群回廊': 'LOCUST RUN', '烛火回廊': 'CANDLE RUN',
    '暗流回廊': 'UNDERTOW RUN', '漂移回廊': 'DRIFT RUN', '空壳回廊': 'HOLLOW RUN',
    '圣歌回廊': 'HYMN RUN', '熔炉回廊': 'FURNACE RUN', '终局回廊': 'FINAL RUN',
}

_WAVE_EN = {
    '冲锋潮': 'CHARGE TIDE', '碎裂群': 'SHATTER SWARM', '织网带': 'WEB BELT',
    '炮台阵': 'TURRET ARRAY', '蜂群': 'SWARM', '重装队': 'HEAVY SQUAD',
    '俯冲队': 'DIVE SQUAD', '光栅带': 'LASER BELT', '巢群': 'NEST SWARM',
    '游魂群': 'WRAITH SWARM', '光栅阵': 'LASER ARRAY', '守门群': 'GATE WARDENS',
    '吸取巢': 'SIPHON NEST', '枪林': 'SPEAR LINE', '雷区': 'MINEFIELD',
    '巨影': 'COLOSSUS', '龙骑队': 'DRAKE SQUAD', '迫击阵': 'MORTAR ARRAY',
    '幽影群': 'SHADE SWARM', '光蛾群': 'MOTH SWARM', '破城队': 'SIEGE SQUAD',
    '织网阵': 'WEB ARRAY', '棱镜阵': 'PRISM ARRAY', '蜂巢群': 'HIVE SWARM',
    '冲骑队': 'LANCER SQUAD', '冰晶群': 'CRYO SWARM', '炬火队': 'TORCH SQUAD',
    '虚空群': 'VOID SWARM', '狙击线': 'SNIPER LINE', '炸弹雨': 'BOMB RAIN',
    '钩爪群': 'HOOK SWARM', '光矛阵': 'LANCE ARRAY', '铁壁阵': 'IRON ARRAY',
    '深潜群': 'DEEP SWARM',
}

_EV_EN = {
    '补给空投': 'SUPPLY DROP', '离子风暴': 'ION STORM', '富矿脉': 'RICH VEIN',
    '低重力区': 'LOW GRAVITY', '过载场': 'OVERLOAD FIELD', '静默带': 'SILENT BELT',
    '裂解层': 'FRACTURE LAYER', '猎场令': 'HUNT ORDER', '湍流带': 'TURBULENCE',
    '悬赏区': 'BOUNTY ZONE', '回收站': 'SALVAGE BAY', '伏击区': 'AMBUSH ZONE',
    '漂流带': 'DRIFT BELT', '维修站': 'REPAIR BAY', '日冕带': 'CORONA BELT',
    '霜冻区': 'FROST ZONE', '黄金回廊': 'GOLDEN RUN', '镜像场': 'MIRROR FIELD',
    '熔火带': 'MOLTEN BELT', '虚空静域': 'VOID CALM', '无光区': 'BLACKOUT',
    '超频带': 'OVERCLOCK', '血月': 'BLOOD MOON', '镜海': 'MIRROR SEA',
    '地热喷泉': 'GEYSER', '回声增幅': 'ECHO BOOST', '雷区': 'MINEFIELD',
    '奇点潮': 'SINGULARITY', '黑日': 'BLACK SUN', '避难所': 'SANCTUM',
    '虫群': 'SWARM', '天顶': 'ZENITH', '星云带': 'NEBULA BELT',
    '骨场': 'BONEYARD', '时序裂隙': 'TIME RIFT', '深层避难所': 'DEEP SANCTUM',
    '镜面回廊': 'MIRROR RUN', '塞壬回廊': 'SIREN RUN', '潮汐井': 'TIDAL WELL',
    '回声室': 'ECHO CHAMBER', '铁雨': 'IRON RAIN', '白蚀区': 'WHITEOUT',
    '裸反应堆': 'BARE REACTOR', '灰烬雨': 'ASHFALL', '脉冲带': 'PULSE BELT',
    '深流': 'DEEP CURRENT', '塞壬合唱': 'SIREN CHOIR',
    '星云带': 'NEBULA BELT', '日冕带': 'CORONA BELT', '墓风区': 'GRAVE WIND ZONE',
    '回声叠层': 'ECHO STACK', '余烬带': 'CINDER BELT', '深静带': 'DEEP QUIET ZONE',
    '伏击带': 'AMBUSH BELT', '熄灯区': 'LIGHTS OUT', '狙击巢': 'SNIPER NEST',
    '回收场': 'RECLAIM YARD', '熔炉带': 'FURNACE BELT', '洋流带': 'CURRENT BELT',
    '骸骨滩': 'BONE SHALLOWS', '镜面区': 'MIRROR ZONE', '失重区': 'WEIGHTLESS ZONE',
    '金矿带': 'GOLD VEIN BELT', '寂流带': 'HUSH CURRENT', '过载带': 'OVERLOAD BELT',
    '星流带': 'STAR CURRENT BELT', '日蚀带': 'ECLIPSE BELT', '幸运矿脉': 'LUCKY VEIN',
    '冷却导管': 'COOLANT DUCT', '自愈纤维': 'SELF-HEAL FIBER', '活体修补': 'LIVING PATCH',
    '燃焰弹芯': 'FLARE CORE', '冻蚀弹芯': 'CRYO CORE', '跳弹镀层': 'RICOCHET PLATING',
    '护盾阵列': 'SHIELD ARRAY', '猎杀协议': 'HUNT PROTOCOL',
}


def _stat_en(s):
    s = s.replace('进入本层时修复 1 格艇体', 'Repair 1 hull on entry')
    s = s.replace('进入本层修复 1 艇体并获 1 护盾', 'Repair 1 hull and gain 1 shield on entry')
    s = s.replace('进入本层修复 1 艇体并获得 1 护盾', 'Repair 1 hull and gain 1 shield on entry')
    s = s.replace('进入本层获得 1 枚护盾', 'Gain 1 shield on entry')
    for zh, en in (('移动速度', 'Move speed'), ('敌弹速度', 'Enemy bullet speed'),
                   ('技能冷却', 'Cooldown'), ('精英出现率', 'Elite rate'),
                   ('敌人密度', 'Enemy density'), ('每波敌人', 'Enemies per wave'), ('掉落率', 'Drop rate'),
                   ('敌弹', 'Enemy bullets'), ('射速', 'Fire rate'),
                   ('伤害', 'Damage'), ('得分', 'Score'), ('掉落', 'Drop rate'),
                   ('敌人', 'Enemies'), ('敌机', 'Enemies'), ('精英', 'Elite'), ('艇体', 'Hull'),
                   ('翻倍', 'doubled'), ('上限', 'cap'),
                   ('护盾', 'Shield'), ('移动', 'Move')):
        s = s.replace(zh, en)
    return s


_BOSS_SIG_EN = {
    '巡夜探照': 'NIGHT WATCHLIGHT', '钟摆横扫': 'PENDULUM SWEEP',
    '深渊吞吸': 'ABYSSAL INTAKE', '回声定位': 'ECHO LOCATOR',
    '迟到回声': 'DELAYED ECHO', '归墟漩涡': 'MAELSTROM',
    '蚀骨酸雨': 'BONE ACID RAIN', '零号协议': 'PROTOCOL ZERO',
    '核心过载': 'CORE OVERLOAD', '赤潮拍岸': 'RED TIDE CRASH',
    '星骸坠雨': 'STARFALL', '白洞引力': 'WHITE HOLE GRAVITY',
    '霓虹矩阵': 'NEON MATRIX', '灰烬风暴': 'ASH STORM',
    '终焉钟声': 'FINAL BELL', '花母绽放': 'BLOOM',
    '时骸回拨': 'TIME REWIND', '深渊触手': 'ABYSS TENTACLES',
    '星墓坍缩': 'TOMB COLLAPSE', '熔核喷发': 'CORE ERUPTION',
    '尽头合拢': 'END CLOSURE', '静默凝视': 'SILENT GAZE',
    '铸世锤击': 'WORLD HAMMER', '门扉全开': 'DOOR WIDE OPEN',
    '盐柱审判': 'SALT PILLAR JUDGMENT', '齿轮碾压': 'GEAR CRUSH',
    '虚数抹除': 'IMAGINARY ERASURE', '终末凝视': 'FINAL GAZE',
}

_BOSS_SIG2_EN = {
    '熄灯搜查': 'LIGHTS OUT', '双摆夹击': 'DOUBLE PENDULUM',
    '巨口回流': 'MAW REFLUX', '回声牢笼': 'ECHO CAGE',
    '残响复写': 'RESIDUAL COPY', '沉没': 'SINKING',
    '骨刺之墙': 'BONE WALL', '协议封锁': 'PROTOCOL LOCK',
    '核心坍缩': 'CORE COLLAPSE', '血浪回卷': 'BLOOD BACKWASH',
    '星屑轨道': 'STARDUST ORBIT', '事件视界': 'EVENT HORIZON',
    '霓虹囚笼': 'NEON CAGE', '王座余烬': 'THRONE EMBERS',
    '审判日': 'JUDGMENT DAY', '孢子云': 'SPORE CLOUD',
    '时间倒带': 'TIME REVERSAL', '触手收网': 'TENTACLE NET',
    '墓碑阵列': 'TOMB ARRAY', '地脉喷涌': 'LEYLINE ERUPTION',
    '闭门': 'CLOSED GATE', '零声场': 'ZERO SOUND',
    '重锻': 'REFORGE', '门扉倒影': 'DOOR REFLECTION',
    '霜蚀圣咏': 'FROST HYMN', '反向传动': 'REVERSE DRIVE',
    '潮汐悖论': 'TIDAL PARADOX', '视界闭合': 'HORIZON CLOSURE',
}


_AUG_KEY_EN = {
    'dmg': ('Damage', 'pct'), 'rate': ('Fire rate', 'rate'), 'hull': ('Hull', 'int'),
    'maxhp': ('Max hull', 'int'), 'bullets': ('Projectiles', 'int'),
    'pierce': ('Pierce', 'int'), 'speed': ('Move speed', 'pct'),
    'crit': ('Crit chance', 'pct'), 'pick': ('Pickup radius', 'pct'),
    'cd': ('Skill cooldown', 'cd'), 'homing': ('Homing', 'int'),
    'shock': ('Impact shock', 'int'), 'vamp': ('Kill heal', 'int'),
    'drone': ('Drones', 'int'), 'orbit': ('Orbit blades', 'int'),
    'chain': ('Chain lightning', 'int'), 'burn': ('Burn', 'int'),
    'freeze': ('Freeze', 'int'), 'ricochet': ('Ricochet', 'int'),
    'shieldgen': ('Shield regen', 'int'), 'double': ('Double shot', 'int'),
    'nova': ('Nova burst', 'int'), 'bigshot': ('Shot size', 'int'),
    'bspd': ('Bullet speed', 'pct'), 'spread': ('Spread', 'int'),
    'rail': ('Rail pierce', 'int'), 'exec': ('Execute', 'int'),
    'soul': ('Soul cap', 'int'), 'bossbane': ('Boss damage', 'pct'),
    'first': ('First-strike damage', 'pct'), 'gambler': ('Greed', 'int'),
    'thorns': ('Thorns', 'int'), 'regen': ('Hull regen', 'int'),
    'aura': ('Corrosion aura', 'int'), 'retaliate': ('Retaliation', 'int'),
    'fragile': ('Fragility', 'int'), 'chill': ('Chill', 'int'),
    'shieldburst': ('Shield burst', 'int'), 'luck': ('Luck', 'int'),
    'skillpow': ('Skill power', 'int'), 'afterburn': ('Afterburn', 'int'),
    'warp': ('Warp', 'int'), 'siphon': ('Siphon', 'int'),
    'lance': ('Lance', 'int'), 'counter': ('Counter', 'int'),
    'close': ('Close-range damage', 'pct'), 'far': ('Long-range damage', 'pct'),
    'finisher': ('Finisher', 'int'), 'boomer': ('Boomerang', 'int'),
    'mine': ('Mines', 'int'), 'blade': ('Orbit blade', 'int'),
    'shot': ('Extra shot', 'int'), 'shieldkill': ('Shield on kill', 'int'),
    'glass': ('Glass cannon', 'int'), 'critboom': ('Crit explosion', 'int'),
}


def _aug_en(a):
    key, val, stack = a[4], a[5], a[6]
    label, kind = _AUG_KEY_EN.get(key, (key.replace('_', ' ').title(), 'int'))
    if key == 'glass':
        return 'Damage +45% · max hull -1'
    if key in ('dmg', 'speed'):
        return '%s +%d%%' % (label, round((val - 1) * 100) if val >= 1 else round(val * 100))
    if key == 'pick':
        if val < 1:
            return '%s +%d%%' % (label, round(val * 100))
        return '%s +%s' % (label, val)
    if kind == 'pct':
        return '%s +%d%%' % (label, round(val * 100))
    if kind in ('rate', 'cd'):
        return '%s ×%.2f' % (label, val)
    if kind == 'int':
        return '%s +%s' % (label, val)
    return '%s %s' % (label, val)


def _pattern_tr(s):
    # 动态句子：层数、波数、阶段、页数、数值行
    m = re.fullmatch(r'飞船 (\d+)', s)
    if m:
        return 'SHIPS %s' % m.group(1)
    m = re.fullmatch(r'BOSS (\d+)', s)
    if m:
        return 'BOSSES %s' % m.group(1)
    m = re.fullmatch(r'增幅 (\d+)', s)
    if m:
        return 'AUGMENTS %s' % m.group(1)
    m = re.fullmatch(r'敌机 (\d+)', s)
    if m:
        return 'ENEMIES %s' % m.group(1)
    m = re.fullmatch(r'SELECT DIVER  ·  已解锁 (\d+) / (\d+)', s)
    if m:
        return 'SELECT DIVER  ·  UNLOCKED %s / %s' % (m.group(1), m.group(2))
    m = re.fullmatch(r'难度 · (.+)  (.+)', s)
    if m:
        return 'DIFFICULTY · %s  %s' % (_TR_ALL.get(m.group(1), m.group(1)), m.group(2))
    m = re.fullmatch(r'(.+)  ·  技能冷却 (.+)s', s)
    if m:
        return '%s  ·  COOLDOWN %ss' % (_TR_ALL.get(m.group(1), m.group(1)), m.group(2))
    m = re.fullmatch(r'本层区域 · (.+)    (.+)', s)
    if m:
        return 'LOCAL ZONE · %s    %s' % (_TR_ALL.get(m.group(1), m.group(1)),
                                          _TR_ALL.get(m.group(2), m.group(2)))
    m = re.fullmatch(r'回廊事件 · (.+)    (.+)    SEED ([0-9A-F]+)', s)
    if m:
        return 'MUTATOR · %s    %s    SEED %s' % (_TR_ALL.get(m.group(1), m.group(1)),
                                                  _TR_ALL.get(m.group(2), m.group(2)),
                                                  m.group(3))
    m = re.fullmatch(r'SONAR PAUSED  ·  (.+)  ·  (.+)  ·  第 (\d+) 层 第 (\d+) 波', s)
    if m:
        return 'SONAR PAUSED  ·  %s  ·  %s  ·  STRATUM %s WAVE %s' % (
            _TR_ALL.get(m.group(1), m.group(1)), _TR_ALL.get(m.group(2), m.group(2)),
            m.group(3), m.group(4))
    m = re.fullmatch(r'获得增幅 · (.+)', s)
    if m:
        return 'AUGMENT · ' + m.group(1)
    m = re.fullmatch(r'契约生效 · (.+)', s)
    if m:
        return 'PACT SIGNED · ' + _TR_ALL.get(m.group(1), m.group(1))
    m = re.fullmatch(r'第 (\d+) / (\d+) 波', s)
    if m:
        return 'WAVE %s / %s' % (m.group(1), m.group(2))
    m = re.fullmatch(r'增幅 (\d+)  ·  (.+)', s)
    if m:
        return 'AUGMENTS %s  ·  %s' % (m.group(1), _TR_ALL.get(m.group(2), m.group(2)))
    m = re.fullmatch(r'(.+) · (.+) · (CRUISE|ABYSS|NIGHTMARE)', s)
    if m and m.group(1) in ('远航', '无尽', '急行', '猎王', '每日', '契约'):
        return '%s · %s' % (_TR_ALL.get(m.group(1), m.group(1)), m.group(3))
    m = re.fullmatch(r'击杀 (\d+)', s)
    if m:
        return 'KILLS %s' % m.group(1)
    m = re.fullmatch(r'× (\d+) 连击', s)
    if m:
        return '× %s COMBO' % m.group(1)
    m = re.fullmatch(r'瞄准 (.+)  ·  (.+)  ·  航向 (\d+)°', s)
    if m:
        return 'AIM %s  ·  %s  ·  HEADING %s°' % (
            'AUTO' if m.group(1) == '自动' else 'MOUSE',
            'T MOUSE' if m.group(1) == '自动' else 'T AUTO',
            m.group(3))
    m = re.fullmatch(r'(.+)  ·  空格', s)
    if m:
        return '%s  ·  SPACE' % _TR_ALL.get(m.group(1), m.group(1))
    m = re.fullmatch(r'区域 · (.+)', s)
    if m:
        return 'ZONE · ' + _TR_ALL.get(m.group(1), m.group(1))
    m = re.fullmatch(r'本层事件 · (.+)  (.+)', s)
    if m:
        return 'LOCAL EVENT · %s  %s' % (_TR_ALL.get(m.group(1), m.group(1)),
                                          _TR_ALL.get(m.group(2), m.group(2)))
    m = re.fullmatch(r'(.+) · 本层事件 · (.+)  (.+)', s)
    if m:
        return '%s · LOCAL EVENT · %s  %s' % (_TR_ALL.get(m.group(1), m.group(1)),
                                               _TR_ALL.get(m.group(2), m.group(2)),
                                               _TR_ALL.get(m.group(3), m.group(3)))
    m = re.fullmatch(r'第 (\d+) 层 · (.+)', s)
    if m:
        return 'STRATUM %s · %s' % (m.group(1), _TR_ALL.get(m.group(2), m.group(2)))
    m = re.fullmatch(r'第 (\d+) 层 / (\d+|∞)', s)
    if m:
        return 'STRATUM %s / %s' % (m.group(1), m.group(2))
    m = re.fullmatch(r'(\d+) / (\d+|∞) 层 · (.+) · 第 (\d+) 波(.*)', s)
    if m:
        suffix = m.group(5)
        if suffix.startswith(' · '):
            suffix = ' · ' + _TR_ALL.get(suffix[3:], suffix[3:])
        return '%s / %s · %s · WAVE %s%s' % (
            m.group(1), m.group(2), _TR_ALL.get(m.group(3), m.group(3)),
            m.group(4), suffix)
    m = re.fullmatch(r'第 (\d+) 层', s)
    if m:
        return 'STRATUM %s' % m.group(1)
    m = re.fullmatch(r'第 (\d+) 波', s)
    if m:
        return 'WAVE %s' % m.group(1)
    m = re.fullmatch(r'第 (\d+) 阶段', s)
    if m:
        return 'PHASE %s' % m.group(1)
    m = re.fullmatch(r'BOSS 进入第 (\d+) 阶段', s)
    if m:
        return 'BOSS ENTERS PHASE %s' % m.group(1)
    m = re.fullmatch(r'回廊轮回 (\d+) · 主题开始复写', s)
    if m:
        return 'CORRIDOR CYCLE %s · THEMES BEGIN TO REPEAT' % m.group(1)
    m = re.fullmatch(r'已连接：(.+)', s)
    if m:
        return 'CONNECTED: ' + m.group(1)
    m = re.fullmatch(r'技能 · (.+)', s)
    if m:
        return 'SKILL · ' + _TR_ALL.get(m.group(1), m.group(1))
    m = re.fullmatch(r'增幅  (.+)', s)
    if m:
        return 'AUGMENTS  ' + m.group(1)
    m = re.fullmatch(r'第 (\d+) 层解锁', s)
    if m:
        return 'UNLOCK AT STRATUM %s' % m.group(1)
    m = re.fullmatch(r'通关第 (\d+) 层后开放', s)
    if m:
        return 'UNLOCKED AFTER STRATUM %s' % m.group(1)
    m = re.fullmatch(r'已解锁 (\d+) / (\d+)', s)
    if m:
        return 'UNLOCKED %s / %s' % (m.group(1), m.group(2))
    m = re.fullmatch(r'第 (\d+) / (\d+) 页', s)
    if m:
        return 'PAGE %s / %s' % (m.group(1), m.group(2))
    m = re.fullmatch(r'可叠加上限 (\d+)', s)
    if m:
        return 'STACK LIMIT %s' % m.group(1)
    m = re.fullmatch(r'已选 (\d+) / (\d+)', s)
    if m:
        return 'TAKEN %s / %s' % (m.group(1), m.group(2))
    m = re.fullmatch(r'成就 (\d+) / (\d+)', s)
    if m:
        return 'ACHIEVEMENTS %s / %s' % (m.group(1), m.group(2))
    m = re.fullmatch(r'累计 (\d+) 次出击', s)
    if m:
        return '%s TOTAL SORTIES' % m.group(1)
    m = re.fullmatch(r'(\d+) 次', s)
    if m:
        return '%s RUNS' % m.group(1)
    m = re.fullmatch(r'艇体 (\d+)   ·   航速 (\d+)   ·   伤害 (.*)   ·   CD (.*)', s)
    if m:
        return 'HULL %s · SPEED %s · DMG %s · CD %s' % tuple(m.groups())
    m = re.fullmatch(r'HP (\d+)   ·   半径 (\d+)   ·   第 (\d+) 层王座', s)
    if m:
        return 'HP %s · RADIUS %s · THRONE OF STRATUM %s' % tuple(m.groups())
    m = re.fullmatch(r'射速 (.*)/s   ·   穿透 (\d+)   ·   弹道 (\d+)', s)
    if m:
        return 'RATE %s/s · PIERCE %s · SHOTS %s' % tuple(m.groups())
    m = re.fullmatch(r'解锁：累计 (\d+) 次出击', s)
    if m:
        return 'UNLOCK: %s SORTIES' % m.group(1)
    m = re.fullmatch(r'解锁：抵达第 (\d+) 层', s)
    if m:
        return 'UNLOCK: REACH STRATUM %s' % m.group(1)
    m = re.fullmatch(r'解锁：初始', s)
    if m:
        return 'UNLOCK: STARTER'
    m = re.fullmatch(r'解锁：(.+)', s)
    if m:
        return 'UNLOCK: ' + _TR_ALL.get(m.group(1), m.group(1))
    m = re.fullmatch(r'基础血量 ([\d.]+)\s+·\s+半径 (\d+)\s+·\s+击破分 (\d+)', s)
    if m:
        return 'BASE HP %s · RADIUS %s · SCORE %s' % tuple(m.groups())
    m = re.fullmatch(r'高危度 ([\d.]+)', s)
    if m:
        return 'THREAT %s' % m.group(1)
    m = re.fullmatch(r'绝技([一二]) · (.+)', s)
    if m:
        return 'SIG %s · %s' % ('I' if m.group(1) == '一' else 'II',
                                  _TR_ALL.get(m.group(2), m.group(2)))
    m = re.fullmatch(r'绝技 II · 第二阶段解锁', s)
    if m:
        return 'SIG II · UNLOCKS AT PHASE II'
    m = re.fullmatch(r'绝技 II · (.+)', s)
    if m:
        return 'SIG II · ' + _TR_ALL.get(m.group(1), m.group(1))
    m = re.fullmatch(r'绝技 · (.+)   ([\d.]+)s', s)
    if m:
        return 'SIG I · %s   %ss' % (_TR_ALL.get(m.group(1), m.group(1)), m.group(2))
    m = re.fullmatch(r'绝技 II · (.+)   ([\d.]+)s', s)
    if m:
        return 'SIG II · %s   %ss' % (_TR_ALL.get(m.group(1), m.group(1)), m.group(2))
    m = re.fullmatch(r'狂怒 · 双绝技同奏', s)
    if m:
        return 'ENRAGED · BOTH SIGNATURES'
    m = re.fullmatch(r'(.+) · (.+)', s)
    if m and m.group(1) in _TR_ALL and m.group(2) in _TR_ALL:
        return '%s · %s' % (_TR_ALL[m.group(1)], _TR_ALL[m.group(2)])
    m = re.fullmatch(r'· (.+)', s)
    if m:
        return '· ' + _TR_ALL.get(m.group(1), m.group(1))
    m = re.fullmatch(r'第 (\d+) 层结束 · 艇体回升', s)
    if m:
        return 'STRATUM %s CLEARED · HULL RESTORED' % m.group(1)
    m = re.fullmatch(r'第 (\d+) 层 · 战斗间隙', s)
    if m:
        return 'STRATUM %s · BETWEEN WAVES' % m.group(1)
    m = re.fullmatch(r'回廊记录 · (.+) · (.+)', s)
    if m:
        return 'RECORD · %s · %s' % (_TR_ALL.get(m.group(1), m.group(1)),
                                    _TR_ALL.get(m.group(2), m.group(2)))
    m = re.fullmatch(r'(.+) · 难度 (.+) · 本局层域 (.+)    SEED ([0-9A-F]+)', s)
    if m:
        return '%s · DIFFICULTY %s · MUTATOR %s · SEED %s' % (
            _TR_ALL.get(m.group(1), m.group(1)), _TR_ALL.get(m.group(2), m.group(2)),
            _TR_ALL.get(m.group(3), m.group(3)), m.group(4))
    return None


def tr(s):
    if not isinstance(s, str) or not META.get('lang', 0):
        return s
    global _TR_READY
    if not _TR_READY:
        _build_tr_content()
    hit = _TR_ALL.get(s)
    if hit is not None:
        return hit
    hit = _pattern_tr(s)
    if hit:
        return hit
    # 统一的量词收尾
    if '艘下潜器' in s:
        s = (s.replace('艘下潜器', ' DIVERS').replace('项增幅', ' AUGMENTS')
             .replace('种敌机', ' ENEMY TYPES').replace('层异域', ' STRATA')
             .replace('位 BOSS', ' BOSSES').replace('种模式', ' MODES'))
    return s

ACHIEVEMENTS = [
    ('first_dive', '初次下潜', '完成一次出击'),
    ('slayer', '百人斩', '累计击毁 100 架敌机'),
    ('combo50', '连击狂潮', '单局打出 50 连击'),
    ('collector', '增幅收藏家', '单局拿到 15 个增幅'),
    ('deep3', '锈潮之下', '抵达第 3 层'),
    ('deep6', '穿过机冢', '抵达第 6 层'),
    ('clear', '回廊尽头', '通关任意难度'),
    ('nightmare', '噩梦生还', '在噩梦难度通关'),
    ('fleet', '全舰队', '解锁全部下潜器'),
    ('deep9', '回廊之核', '抵达第 9 层'),
    ('deep12', '白洞尽头', '抵达第 12 层'),
    ('deep15', '终焉之门', '抵达第 15 层'),
    ('deep18', '深渊之底', '抵达第 18 层'),
    ('aug25', '增幅洪流', '单局拿到 25 个增幅'),
    ('aug40', '增幅狂潮', '单局拿到 40 个增幅'),
    ('aug60', '增幅风暴', '单局拿到 60 个增幅'),
    ('kills500', '五百葬场', '单局击毁 500 架敌机'),
    ('kills1000', '千机葬场', '单局击毁 1000 架敌机'),
    ('deep21', '回廊尽头', '抵达第 21 层'),
    ('aug80', '增幅深渊', '单局拿到 80 个增幅'),
    ('kills1500', '千五葬场', '单局击毁 1500 架敌机'),
    ('deep24', '门后之物', '抵达第 24 层'),
    ('aug100', '增幅深渊', '单局拿到 100 个增幅'),
    ('kills2500', '两千五葬场', '单局击毁 2500 架敌机'),
    ('endless10', '无尽十层', '在无尽模式抵达第 10 层'),
    ('endless20', '无尽二十层', '在无尽模式抵达第 20 层'),
    ('endless30', '越界者', '在无尽模式抵达第 30 层'),
    ('endless50', '没有尽头', '在无尽模式抵达第 50 层'),
    ('rush_clear', '急行通关', '通关 12 层急行模式'),
    ('hunt_clear', '猎王归位', '通关 12 层猎王模式'),
    ('curator', '回廊档案员', '打开深渊档案'),
    ('sop', '按手册操作', '打开操作手册'),
    ('calibrated', '校准完成', '修改任意一项设置'),
    ('boss_lore', '王座研究者', '查看 BOSS 档案'),
    ('aug_lore', '增幅研究者', '查看增幅档案'),
    ('daily_clear', '今日回声', '通关每日回廊'),
    ('daily_first', '今日下潜', '进入每日回廊'),
    ('polyglot', '双语潜航', '切换界面语言'),
    ('voice_link', '回声频道', '开启语音播报'),
    ('cycle1', '轮回者', '在无尽模式进入第二轮主题'),
    ('workshop', '回声工程师', '在回声工坊购买一次永久升级'),
    ('workshop_max', '工坊大师', '把任意一项永久升级点满'),
    ('shards100', '结晶收藏', '持有 100 枚回声结晶'),
    ('shards300', '结晶富翁', '持有 300 枚回声结晶'),
    ('lab_all', '全模块校准', '所有永久升级至少 1 级'),
    ('shards500', '结晶之海', '持有 500 枚回声结晶'),
    ('shards800', '结晶汪洋', '持有 800 枚回声结晶'),
    ('deep28', '终末之眼', '抵达第 28 层'),
    ('saves3', '三线潜航', '建立 3 个独立存档'),
    ('allhands', '全员集结', '解锁全部 40 艘下潜器'),
    ('pact5', '契约收藏家', '签订 5 份深渊契约'),
    ('pact10', '契约深渊', '签订 10 份深渊契约'),
    ('pact_clear', '契约履行', '通关契约模式'),
    ('kills5000', '五千葬场', '单局击毁 5000 架敌机'),
    ('endless100', '百层回廊', '在无尽模式抵达第 100 层'),
]

# -*- coding: utf-8 -*-
# ================================================================
#  飞船 / 增幅 / 状态
# ================================================================
SHIPS = [
    dict(id='echo', name='回声号', role='均衡', hp=4, speed=298, dmg=1.0, rate=.105, bullets=1,
         pierce=0, skill='回声脉冲', cd=9.0, col='aqua', unlock=0,
         desc='清空全部敌弹，并对场上所有目标造成伤害。'),
    dict(id='talon', name='猎隼', role='突进', hp=3, speed=382, dmg=.82, rate=.074, bullets=1,
         pierce=0, skill='相位冲刺', cd=6.0, col='amber', unlock=0,
         desc='向移动方向高速冲刺，无敌并撞穿沿途敌人。'),
    dict(id='anvil', name='铁砧', role='重装', hp=6, speed=230, dmg=1.42, rate=.168, bullets=1,
         pierce=0, skill='力场护盾', cd=12.0, col='coral', unlock=0,
         desc='展开 3 枚护盾，7 秒内替你吸收所有伤害。'),
    dict(id='swarm', name='蜂群', role='机群', hp=3, speed=300, dmg=.68, rate=.1, bullets=1,
         pierce=0, skill='蜂群出击', cd=13.0, col='violet', unlock=2,
         desc='召唤 2 架环绕无人机，持续射击 12 秒。'),
    dict(id='prism', name='棱镜', role='光矛', hp=3, speed=292, dmg=1.15, rate=.13, bullets=1,
         pierce=1, skill='折射光矛', cd=10.0, col='green', unlock=3,
         desc='短暂蓄力后射出贯穿全场的折射光束。'),
    dict(id='thorn', name='荆棘', role='弹幕', hp=4, speed=288, dmg=.8, rate=.095, bullets=2,
         pierce=0, skill='荆棘绽放', cd=11.0, col='steel', unlock=4,
         desc='向四面八方绽放十六根尖刺，每根可穿透两个目标。'),
    dict(id='halo', name='光环', role='支援', hp=4, speed=300, dmg=.9, rate=.11, bullets=1,
         pierce=0, skill='治愈脉冲', cd=14.0, col='gold', unlock=5,
         desc='释放治愈脉冲：回复艇体、清空周围弹幕，并短暂无敌。'),
    dict(id='void', name='虚空', role='控场', hp=3, speed=302, dmg=1.05, rate=.115, bullets=1,
         pierce=1, skill='引力井', cd=12.0, col='white', unlock=6,
         desc='在前方张开引力井，把敌人拖向中心并持续撕扯三秒。'),
    dict(id='pyre', name='烛龙', role='焚海', hp=3, speed=290, dmg=1.08, rate=.12, bullets=1,
         pierce=0, skill='焚海脉冲', cd=10.0, col='amber', unlock=7,
         desc='向四周撒出燃烧弹，并在脚下留下短暂火海。'),
    dict(id='frost', name='霜环', role='冰控', hp=3, speed=300, dmg=.9, rate=.105, bullets=1,
         pierce=0, skill='霜环', cd=11.0, col='steel', unlock=7,
         desc='冻缓周围敌人三秒，并清空附近弹幕。'),
    dict(id='rift', name='裂空', role='斩击', hp=3, speed=330, dmg=1.02, rate=.09, bullets=1,
         pierce=1, skill='裂空斩', cd=8.0, col='green', unlock=8,
         desc='向前斩出三道高速月刃，每道可穿透六个目标。'),
    dict(id='bastion', name='磐石', role='堡垒', hp=6, speed=215, dmg=1.25, rate=.17, bullets=1,
         pierce=1, skill='磐石壁垒', cd=13.0, col='steel', unlock=8,
         desc='展开壁垒，获得 3 枚护盾并清空周围弹幕，震伤近身敌人。'),
    dict(id='tide', name='潮汐', role='潮控', hp=4, speed=300, dmg=1.0, rate=.11, bullets=1,
         pierce=0, skill='潮涌', cd=11.0, col='aqua', unlock=8,
         desc='掀起环形潮涌，推开并冻缓周围敌人，同时造成伤害。'),
    dict(id='star', name='星火', role='连射', hp=3, speed=315, dmg=.7, rate=.055, bullets=2,
         pierce=0, skill='星火暴雨', cd=11.0, col='gold', unlock=8,
         desc='向四周撒出二十四枚追踪星火，自动扑向最近的目标。'),
    dict(id='nova', name='新星', role='爆发', hp=3, speed=295, dmg=.95, rate=.12, bullets=1,
         pierce=0, skill='超新星', cd=15.0, col='coral', unlock=8,
         desc='引爆超新星，清空周围弹幕并重创大范围敌人。'),
    dict(id='lumen', name='流明', role='光域', hp=4, speed=305, dmg=.85, rate=.095, bullets=2,
         pierce=0, skill='灼光领域', cd=12.0, col='gold', unlock=8,
         desc='在脚下铺开灼光领域，持续灼伤并冻缓敌人。'),
    dict(id='corona', name='日冕', role='爆发', hp=3, speed=300, dmg=1.0, rate=.11, bullets=1,
         pierce=0, skill='日冕喷发', cd=13.0, col='amber', unlock=8,
         desc='在四周引爆日冕火环，并留下三片灼烧领域。'),
    dict(id='refract', name='折光', role='折射', hp=3, speed=310, dmg=.85, rate=.09, bullets=2,
         pierce=0, skill='折光矩阵', cd=12.0, col='aqua', unlock=8,
         desc='向四周射出十二枚折光弹，每枚可弹跳四次。'),
    dict(id='vortex', name='涡流', role='控场', hp=4, speed=300, dmg=.90, rate=.10, bullets=2,
         pierce=0, skill='奇点涡流', cd=13.0, col='violet', unlock=8,
         desc='在前方制造奇点，吸住弹幕并持续撕裂范围内的敌人。'),
    dict(id='forge', name='铸炉', role='火力', hp=4, speed=290, dmg=1.15, rate=.12, bullets=1,
         pierce=1, skill='熔铸炮台', cd=14.0, col='amber', unlock=8,
         desc='召唤两座熔铸无人机，并在脚下留下灼热熔炉。'),
    dict(id='storm', name='雷暴', role='链电', hp=3, speed=305, dmg=.90, rate=.10, bullets=1,
         pierce=0, skill='雷暴链', cd=11.0, col='aqua', unlock=8,
         desc='雷链在敌群间跳跃，最多灼穿八个目标。'),
    dict(id='decoy', name='镜影', role='分身', hp=3, speed=310, dmg=.85, rate=.09, bullets=2,
         pierce=0, skill='镜影分身', cd=12.0, col='violet', unlock=8,
         desc='召出三架临时僚机，同时替你挡下一轮弹幕。'),
    dict(id='titan', name='泰坦', role='重装', hp=7, speed=205, dmg=1.30, rate=.16, bullets=1,
         pierce=1, skill='泰坦碾压', cd=14.0, col='steel', unlock=8,
         desc='三秒内几乎不可摧毁，并把靠近的敌机碾成碎屑。'),
    dict(id='oracle', name='先知', role='时控', hp=3, speed=300, dmg=.90, rate=.10, bullets=1,
         pierce=0, skill='时间停滞', cd=14.0, col='white', unlock=8,
         desc='让整片战场的敌弹与敌人慢下来，并全体标记弱点。'),
    dict(id='lark', name='云雀', role='侦察', hp=3, speed=345, dmg=.78, rate=.075, bullets=2,
         pierce=0, skill='裂空突袭', cd=8.0, col='green', unlock=10, skill_key='rift',
         desc='轻装高速侦察艇，向前斩出月刃；适合穿插与抢节奏。'),
    dict(id='manta', name='蝠鲼', role='游击', hp=4, speed=318, dmg=.92, rate=.095, bullets=2,
         pierce=0, skill='潮汐回旋', cd=11.0, col='aqua', unlock=12, skill_key='tide',
         desc='贴着敌群游走，用环形潮涌推开近身目标，再回头补枪。'),
    dict(id='kraken', name='渊主', role='重炮', hp=5, speed=252, dmg=1.34, rate=.15, bullets=1,
         pierce=1, skill='壁垒展开', cd=13.0, col='steel', unlock=14, skill_key='bastion',
         desc='慢，但每一发都像压舱铁；壁垒展开后可以硬顶一轮。'),
    dict(id='solar', name='曜日', role='焚天', hp=3, speed=300, dmg=1.06, rate=.115, bullets=1,
         pierce=0, skill='日冕风暴', cd=11.0, col='amber', unlock=16, skill_key='pyre',
         desc='把整片水域点燃，用火海切断敌人的追击路线。'),
    dict(id='starferry', name='星槎', role='护航', hp=4, speed=318, dmg=.88, rate=.095, bullets=2,
         pierce=0, skill='星图校准', cd=10.0, col='green', unlock=18, skill_key='halo',
         desc='以星图校准护住艇身，清除近身弹幕并回复艇体。'),
    dict(id='eclipse', name='蚀影', role='刺客', hp=3, speed=352, dmg=1.08, rate=.115, bullets=1,
         pierce=1, skill='暗面突袭', cd=8.5, col='violet', unlock=20, skill_key='talon',
         desc='沿暗面高速切入，用无敌冲刺撕开敌阵。'),
    dict(id='bulwark', name='磐舟', role='堡垒', hp=7, speed=238, dmg=1.22, rate=.15, bullets=2,
         pierce=1, skill='磐石展开', cd=12.0, col='steel', unlock=22, skill_key='anvil',
         desc='把整艘船变成移动堡垒，三枚护盾替它吃下整轮齐射。'),
    dict(id='weaver', name='织星', role='星网', hp=4, speed=300, dmg=.92, rate=.10, bullets=1,
         pierce=0, skill='星网奇点', cd=13.0, col='aqua', unlock=24, skill_key='void',
         desc='在最密集的敌群里织出奇点，把弹幕和敌机一起拖进星网。'),
    dict(id='requiem', name='安魂曲', role='时控', hp=4, speed=306, dmg=.92, rate=.103, bullets=1,
         pierce=0, skill='安魂时滞', cd=13.0, col='white', unlock=18, skill_key='oracle',
         desc='把整片战场拖进慢速安魂曲，在弹幕缝隙里从容收割。'),
    dict(id='glaive', name='环刃', role='斩击', hp=4, speed=326, dmg=.97, rate=.096, bullets=2,
         pierce=0, skill='环刃裂空', cd=9.0, col='green', unlock=20, skill_key='rift',
         desc='高速双刃艇，以月刃切开弹幕，再贴脸补上两轮齐射。'),
    dict(id='seraph', name='炽天使', role='支援', hp=4, speed=300, dmg=.86, rate=.10, bullets=2,
         pierce=0, skill='炽天圣咏', cd=12.0, col='gold', unlock=22, skill_key='halo',
         desc='以圣咏修复艇体、清空弹幕，并用余光点燃靠近的敌人。'),
    dict(id='abysseye', name='渊眼', role='爆发', hp=4, speed=294, dmg=1.12, rate=.12, bullets=1,
         pierce=1, skill='渊眼超新星', cd=14.0, col='coral', unlock=26, skill_key='nova',
         desc='把深渊的目光压成一枚超新星，清空周围弹幕并重创大范围目标。'),
    dict(id='sepulcher', name='守墓人', role='重装', hp=7, speed=218, dmg=1.38, rate=.165, bullets=1,
         pierce=1, skill='守墓壁垒', cd=13.0, col='steel', unlock=28, skill_key='bastion',
         desc='慢得像一座墓碑，但壁垒展开时能把整轮齐射挡在壳外。'),
    dict(id='hivemind', name='蜂后', role='机群', hp=4, speed=292, dmg=.78, rate=.09, bullets=2,
         pierce=0, skill='蜂后号令', cd=12.0, col='violet', unlock=30, skill_key='swarm',
         desc='两支蜂群同时出巢，用数量把弹幕缝起来。'),
    dict(id='dawn', name='晨曦', role='支援', hp=5, speed=300, dmg=.86, rate=.10, bullets=2,
         pierce=0, skill='晨曦圣咏', cd=13.0, col='gold', unlock=32, skill_key='halo',
         desc='一边修复艇体一边清弹，把长局拖成自己的节奏。'),
    dict(id='breakwater', name='断潮', role='斩击', hp=4, speed=332, dmg=1.04, rate=.092, bullets=1,
         pierce=1, skill='断潮裂空', cd=8.0, col='green', unlock=34, skill_key='rift',
         desc='贴着潮头切开敌阵，月刃之后还有一轮贴脸齐射。'),
]

def _sident(trait, trait_en, desc, desc_en, pattern, **mods):
    d = dict(trait=trait, trait_en=trait_en, desc=desc, desc_en=desc_en, pattern=pattern)
    d.update(mods)
    return d


# 每艘船不只是换色：名字对应的外形、专属特性、专属弹道都在这里。
# mul/add 作用到本局 run.st；maxhp/shield 在开局结算；echo 是复制齐射的概率。
SHIP_IDENTITIES = {
    'echo': _sident('声呐余波', 'SONAR AFTERGLOW', '每次射击有 16% 概率复制一轮回声弹。',
                    '16% chance to echo an extra volley.', 'echo', echo=.16),
    'talon': _sident('猎杀俯冲', 'FALCON DIVE', '冲刺冷却 -8%，暴击率 +4%。',
                     'Dash cooldown -8%, crit +4%.', 'twin', mul={'cd': .92}, add={'crit': .04}),
    'anvil': _sident('砧座稳定', 'ANVIL POISE', '开局获得 1 枚护盾，重弹伤害 +4%。',
                     'Start with 1 shield; heavy rounds +4% damage.', 'heavy', shield=1, mul={'dmg': 1.04}),
    'swarm': _sident('蜂巢协同', 'HIVE SYNC', '基础弹道 +1，射速 +6%。',
                     '+1 base projectile; fire rate +6%.', 'swarm', add={'bullets': 1}, mul={'rate': 1.06}),
    'prism': _sident('光谱校准', 'SPECTRUM LOCK', '穿透 +1，光矛伤害 +6%。',
                     'Pierce +1; lance damage +6%.', 'lance', add={'pierce': 1}, mul={'dmg': 1.06}),
    'thorn': _sident('尖刺外壳', 'THORN SHELL', '接触反伤 +0.6，近身更危险。',
                     'Contact thorns +0.6; punish close enemies.', 'spike', add={'thorns': .6}),
    'halo': _sident('治愈余辉', 'HEALING HALO', '艇体 +1，拾取治疗 +1。',
                    '+1 hull; pickup healing +1.', 'wave', maxhp=1, add={'pickheal': 1}),
    'void': _sident('引力余量', 'GRAVITY RESERVE', '敌人减速 +0.15，控场更久。',
                    'Enemy slow +0.15; longer crowd control.', 'orb', add={'slow': .15}),
    'pyre': _sident('龙息延烧', 'DRAGON BREATH', '灼烧 +1，火焰伤害 +4%。',
                    'Burn +1; flame damage +4%.', 'furnace', add={'burn': 1}, mul={'dmg': 1.04}),
    'frost': _sident('霜核', 'FROST CORE', '冻结 +1，减速 +0.1。',
                     'Freeze +1; slow +0.1.', 'wave', add={'freeze': 1, 'slow': .1}),
    'rift': _sident('空间裂隙', 'RIFT EDGE', '暴击 +6%，射速 +3%。',
                    'Crit +6%; fire rate +3%.', 'blade', add={'crit': .06}, mul={'rate': 1.03}),
    'bastion': _sident('岩层装甲', 'BEDROCK ARMOR', '艇体 +1，开局获得 1 枚护盾。',
                       '+1 hull; start with 1 shield.', 'heavy', maxhp=1, shield=1),
    'tide': _sident('潮汐节律', 'TIDAL RHYTHM', '射速 +8%，冻结 +1。',
                    'Fire rate +8%; freeze +1.', 'wave', mul={'rate': 1.08}, add={'freeze': 1}),
    'star': _sident('星火连锁', 'STAR CHAIN', '基础弹道 +1，射速 +3%。',
                    '+1 base projectile; fire rate +3%.', 'swarm', add={'bullets': 1}, mul={'rate': 1.03}),
    'nova': _sident('超新星余波', 'NOVA AFTERMATH', '伤害 +10%，暴击 +3%。',
                    'Damage +10%; crit +3%.', 'orb', mul={'dmg': 1.10}, add={'crit': .03}),
    'lumen': _sident('流明尾迹', 'LUMEN WAKE', '移动速度 +8%，拾取范围 +8%。',
                     'Move speed +8%; pickup range +8%.', 'echo', mul={'speed': 1.08, 'pick': 1.08}),
    'corona': _sident('日冕环', 'CORONA RING', '灼烧 +1，光环伤害 +0.1。',
                      'Burn +1; aura damage +0.1.', 'sun', add={'burn': 1, 'aura': .1}),
    'refract': _sident('折射棱面', 'FACET BOUNCE', '弹射 +1，暴击 +3%。',
                       'Ricochet +1; crit +3%.', 'mirror', add={'ricochet': 1, 'crit': .03}),
    'vortex': _sident('涡心', 'VORTEX CORE', '追踪 +1，减速 +0.1。',
                      'Homing +1; slow +0.1.', 'orb', add={'homing': 1, 'slow': .1}),
    'forge': _sident('炉心过载', 'FURNACE OVERLOAD', '巨弹 +1，射速 -5%。',
                     'Big shot +1; fire rate -5%.', 'furnace', add={'bigshot': 1}, mul={'rate': .95}),
    'storm': _sident('导电云', 'CONDUCTIVE CLOUD', '链电 +1，弹速 +0.1。',
                     'Chain +1; projectile speed +0.1.', 'rail', add={'chain': 1, 'bspd': .1}),
    'decoy': _sident('镜面残像', 'MIRROR AFTERIMAGE', '镜像 +1，残影会替你挡弹。',
                     'Mirror +1; afterimages soak bullets.', 'mirror', add={'mirror': 1}),
    'titan': _sident('泰坦骨架', 'TITAN FRAME', '艇体 +2，移动速度 -4%。',
                     '+2 hull; move speed -4%.', 'heavy', maxhp=2, mul={'speed': .96}),
    'oracle': _sident('预知弹道', 'ORACLE SIGHT', '暴击 +8%，减速 +0.1。',
                      'Crit +8%; slow +0.1.', 'harp', add={'crit': .08, 'slow': .1}),
    'lark': _sident('轻羽', 'LIGHT FEATHER', '移动速度 +8%，射速 +5%。',
                    'Move speed +8%; fire rate +5%.', 'twin', mul={'speed': 1.08, 'rate': 1.05}),
    'manta': _sident('滑翔翼', 'GLIDE WING', '移动速度 +10%，基础弹道 +1。',
                     'Move speed +10%; +1 base projectile.', 'wave', mul={'speed': 1.1}, add={'bullets': 1}),
    'kraken': _sident('深压', 'ABYSSAL PRESSURE', '伤害 +12%，穿透 +1。',
                      'Damage +12%; pierce +1.', 'tomb', mul={'dmg': 1.12}, add={'pierce': 1}),
    'solar': _sident('曜斑', 'SUNSPOT', '灼烧 +2，伤害 +3%。',
                     'Burn +2; damage +3%.', 'sun', add={'burn': 2}, mul={'dmg': 1.03}),
    'starferry': _sident('星图护航', 'STARMAP ESCORT', '艇体 +1，拾取治疗 +1。',
                         '+1 hull; pickup healing +1.', 'echo', maxhp=1, add={'pickheal': 1}),
    'eclipse': _sident('暗面', 'DARK SIDE', '暴击 +10%，伤害 +4%。',
                       'Crit +10%; damage +4%.', 'blade', add={'crit': .10}, mul={'dmg': 1.04}),
    'bulwark': _sident('双壳', 'DOUBLE HULL', '艇体 +2，开局获得 1 枚护盾。',
                       '+2 hull; start with 1 shield.', 'heavy', maxhp=2, shield=1),
    'weaver': _sident('星网', 'STAR WEAVE', '追踪 +1，减速 +0.15。',
                      'Homing +1; slow +0.15.', 'web', add={'homing': 1, 'slow': .15}),
    'requiem': _sident('安魂节拍', 'REQUIEM TEMPO', '技能冷却 -10%，减速 +0.1。',
                       'Skill cooldown -10%; slow +0.1.', 'harp', mul={'cd': .9}, add={'slow': .1}),
    'glaive': _sident('环刃回旋', 'RINGBLADE SPIN', '穿透 +1，暴击 +3%。',
                      'Pierce +1; crit +3%.', 'blade', add={'pierce': 1, 'crit': .03}),
    'seraph': _sident('圣咏', 'SERAPH CHORUS', '艇体 +1，再生 +1。',
                      '+1 hull; regeneration +1.', 'twin', maxhp=1, add={'regen': 1}),
    'abysseye': _sident('凝视', 'ABYSS GAZE', '暴击 +4%，暴击伤害 +25%。',
                        'Crit +4%; crit damage +25%.', 'lance', add={'crit': .04, 'critdmg': 1.0}),
    'sepulcher': _sident('墓壳', 'TOMB SHELL', '艇体 +3，移动速度 -3%。',
                         '+3 hull; move speed -3%.', 'tomb', maxhp=3, mul={'speed': .97}),
    'hivemind': _sident('王台', 'ROYAL CRADLE', '基础弹道 +1，并多带 1 架开局无人机。',
                        '+1 base projectile; start with 1 extra drone.', 'queen',
                        add={'bullets': 1}, drone=1),
    'dawn': _sident('破晓', 'DAYBREAK', '艇体 +2，再生 +1。',
                    '+2 hull; regeneration +1.', 'twin', maxhp=2, add={'regen': 1}),
    'breakwater': _sident('破浪', 'BREAKWATER EDGE', '移动速度 +6%，暴击 +4%。',
                          'Move speed +6%; crit +4%.', 'blade', mul={'speed': 1.06}, add={'crit': .04}),
}

SHIP_PATTERN_NAMES = {
    'echo': ('回声扇面', 'ECHO FAN'), 'twin': ('双联直射', 'TWIN LINK'),
    'heavy': ('重锤弹', 'HAMMER ROUND'), 'swarm': ('蜂群散射', 'SWARM SPRAY'),
    'lance': ('光矛贯射', 'LANCE PIERCE'), 'spike': ('荆棘侧刺', 'THORN SIDE'),
    'wave': ('潮涌扇面', 'TIDAL FAN'), 'orb': ('引力球', 'GRAVITY ORB'),
    'furnace': ('熔炉锥射', 'FURNACE CONE'), 'blade': ('双刃切击', 'BLADE CUT'),
    'mirror': ('镜面回响', 'MIRROR ECHO'), 'rail': ('电磁轨道', 'RAIL SHOT'),
    'tomb': ('墓壳重炮', 'TOMB CANNON'), 'web': ('星网追踪', 'STAR WEB'),
    'harp': ('安魂交替', 'REQUIEM ALTERNATE'), 'sun': ('日冕环爆', 'CORONA BURST'),
    'queen': ('王台齐射', 'ROYAL VOLLEY'),
}


def apply_ship_identity(run):
    """把船的专属特性结算到本局属性上；存档载入时沿用存档里的已结算数值。"""
    ident = SHIP_IDENTITIES.get(run.ship.get('id'))
    run.identity = ident
    if not ident:
        return
    run.max_hp = max(2, run.max_hp + int(ident.get('maxhp', 0)))
    run.hp = run.max_hp
    for key, val in ident.get('add', {}).items():
        run.st[key] = run.st.get(key, 0) + val
    for key, val in ident.get('mul', {}).items():
        run.st[key] = run.st.get(key, 0) * val
    run.start_shield = int(ident.get('shield', 0))
    run.start_drone = int(ident.get('drone', 0))
    run.fire_echo = float(ident.get('echo', 0))


SHIPS_PER_PAGE = 12

SHIP_I18N = {
    'echo': ('ECHO', 'BALANCED', 'ECHO PULSE',
             'A balanced diver with a reliable pulse. Nothing to prove, everything to survive.'),
    'talon': ('TALON', 'DASH', 'PHASE DASH',
              'Dashes forward, invulnerable, ramming through everything on the way.'),
    'anvil': ('ANVIL', 'HEAVY', 'FORCE SHIELD',
              'Raises three shields that absorb every hit for seven seconds.'),
    'swarm': ('SWARM', 'SWARM', 'SWARM SORTIE',
              'Deploys two orbiting drones that keep firing for twelve seconds.'),
    'prism': ('PRISM', 'LANCE', 'REFRACT LANCE',
              'Charges briefly, then fires a corridor-wide refracting beam.'),
    'thorn': ('THORN', 'BARRAGE', 'THORN BLOOM',
              'Blooms sixteen spikes in every direction; each pierces two targets.'),
    'halo': ('HALO', 'SUPPORT', 'HEAL PULSE',
               'Heals the hull, clears nearby bullets and grants brief invulnerability.'),
    'void': ('VOID', 'CONTROL', 'GRAVITY WELL',
              'Opens a gravity well ahead, dragging enemies in and tearing them for three seconds.'),
    'pyre': ('PYRE', 'PYRE', 'PYRE PULSE',
              'Scatters burning shots and leaves a short-lived sea of fire underfoot.'),
    'frost': ('FROST', 'CRYO', 'FROST RING',
               'Freezes nearby enemies for three seconds and clears the surrounding bullets.'),
    'rift': ('RIFT', 'SLASH', 'RIFT SLASH',
              'Cuts three fast crescent blades forward; each pierces six targets.'),
    'bastion': ('BASTION', 'BASTION', 'BASTION WALL',
                 'Raises a wall, gains three shields, clears bullets and shocks close enemies.'),
    'tide': ('TIDE', 'TIDE', 'TIDAL SURGE',
              'Summons a circular surge that pushes, slows and damages everything nearby.'),
    'star': ('STAR', 'RAPID', 'STARFALL',
              'Scatters twenty-four homing starfires that seek the nearest targets.'),
    'nova': ('NOVA', 'BURST', 'SUPERNOVA',
              'Detonates a supernova, clearing bullets and devastating a huge area.'),
    'lumen': ('LUMEN', 'LUMEN', 'GLOW FIELD',
               'Lays a burning light field that scorches and slows everything inside.'),
    'corona': ('CORONA', 'BURST', 'CORONA BURST',
                'Detonates fire rings around the hull and leaves three burning fields.'),
    'refract': ('REFRACT', 'REFRACT', 'REFRACT MATRIX',
                 'Fires twelve refracting shots in every direction; each bounces four times.'),
    'vortex': ('VORTEX', 'CONTROL', 'SINGULARITY',
                'Creates a singularity ahead that eats bullets and shreds enemies inside.'),
    'forge': ('FORGE', 'FIREPOWER', 'FORGE TURRET',
               'Summons two forge drones and leaves a burning furnace underfoot.'),
    'storm': ('STORM', 'CHAIN', 'STORM CHAIN',
               'Lightning chains between enemies, scorching up to eight targets.'),
    'decoy': ('DECOY', 'DECOY', 'MIRROR DECOY',
               'Summons three temporary wingmen and blocks one volley for you.'),
    'titan': ('TITAN', 'HEAVY', 'TITAN CRUSH',
               'Nearly indestructible for three seconds, crushing anything that comes close.'),
    'oracle': ('ORACLE', 'TIME', 'TIME STOP',
                'Slows every enemy and bullet on the field, marking all weak points.'),
    'lark': ('LARK', 'SCOUT', 'RIFT RAID',
             'A light, fast scout that cuts crescent blades forward. Built for weaving and tempo.'),
    'manta': ('MANTA', 'SKIRMISH', 'TIDAL SPIN',
              'Skims around packs, pushes close enemies away with a ring surge, then swings back.'),
    'kraken': ('KRAKEN', 'SIEGE', 'BULWARK DEPLOY',
               'Slow, but every shot hits like ballast iron; the bulwark can eat a full volley.'),
    'solar': ('SOLAR', 'PYRE', 'CORONA STORM',
              'Sets the water alight, using fire fields to cut off the enemies chasing you.'),
    'starferry': ('STARFERRY', 'ESCORT', 'STARMAP CALIBRATION',
                  'A starmap-calibrated escort that clears close bullets and restores hull.'),
    'eclipse': ('ECLIPSE', 'ASSASSIN', 'UMBRA RAID',
                'Dashes along the dark side, using invulnerable speed to tear open the pack.'),
    'bulwark': ('BULWARK', 'FORTRESS', 'BASTION DEPLOY',
                'Turns the hull into a moving fortress with three shields against full volleys.'),
    'weaver': ('WEAVER', 'STARWEB', 'STARWEB SINGULARITY',
               'Weaves a singularity into the densest pack, dragging bullets and enemies into it.'),
    'requiem': ('REQUIEM', 'TIME', 'REQUIEM LAG',
                'Drags the battlefield into a slow requiem and harvests from the gaps.'),
    'glaive': ('GLAIVE', 'SLASH', 'GLAIVE RIFT',
               'A fast twin-blade diver that cuts through bullet walls, then closes for twin volleys.'),
    'seraph': ('SERAPH', 'SUPPORT', 'SERAPH HYMN',
               'Restores hull, clears bullets and burns nearby enemies with its hymn.'),
    'abysseye': ('ABYSS EYE', 'BURST', 'ABYSS SUPERNOVA',
                 'Compresses the abyss gaze into a supernova that clears bullets and ruins packs.'),
    'sepulcher': ('SEPULCHER', 'GRAVE', 'SEPULCHER WALL',
                  'Slow as a tombstone, but the wall can eat a full volley before it cracks.'),
    'hivemind': ('HIVEMIND', 'SWARM', 'HIVE COMMAND',
                 'Two broods leave the nest at once, stitching the bullet wall with numbers.'),
    'dawn': ('DAWN', 'SUPPORT', 'DAWN HYMN',
             'Repairs the hull while clearing bullets, dragging long runs into your tempo.'),
    'breakwater': ('BREAKWATER', 'SLASH', 'BREAKWATER RIFT',
                   'Cuts along the tide head, then closes in for a point-blank volley.'),
}

def ship_by_id(sid):
    for s in SHIPS:
        if s['id'] == sid:
            return s
    return SHIPS[0]

def ship_unlocked(s):
    return META.get('best_layer', 0) >= s['unlock']

def default_stats():
    return {
        'dmg': 1.0, 'rate': 1.0, 'bullets': 1, 'pierce': 0, 'crit': 0.0,
        'speed': 1.0, 'pick': 80, 'cd': 1.0, 'homing': 0, 'shock': 0,
        'leech': 0, 'drone': 0, 'slow': 0, 'freeze': 0, 'ricochet': 0,
        'shieldgen': 0, 'double': 0, 'vamp': 0, 'pierce_all': 0, 'nova': 0,
        'orbit': 0, 'chain': 0, 'burn': 0, 'mirror': 0, 'frost': 0,
        'berserk': 0, 'greed': 0, 'phase': 0,
        'critdmg': 0, 'thorns': 0, 'regen': 0, 'aura': 0, 'bspd': 0,
        'bigshot': 0, 'revive': 0, 'luck': 0, 'skillpow': 0, 'exec': 0,
        'afterburn': 0, 'warp': 0, 'siphon': 0, 'lance': 0, 'gambler': 0,
        'first': 0, 'overk': 0, 'shieldkill': 0, 'spread': 0, 'rail': 0,
        'pickheal': 0, 'critboom': 0, 'soul': 0, 'retaliate': 0, 'fragile': 0,
        'chill': 0, 'shieldburst': 0, 'bossbane': 0,
        'close': 0, 'far': 0, 'finisher': 0,
        'boomer': 0, 'mine': 0, 'blade': 0, 'shot': 0,
    }


def default_lmod():
    return {'budget': 1.0, 'drop': 1.0, 'speed': 1.0, 'dmg': 1.0,
            'espd': 1.0, 'rate': 1.0, 'score': 1.0, 'name': '静稳区', 'desc': '本层无异常'}


# 每层随机区域事件：同一套地图，每局走进来的规则都不一样
LAYER_EVENTS = [
    dict(id='supply', name='补给空投', desc='进入本层时修复 1 格艇体', mods={}, entry='heal'),
    dict(id='storm', name='离子风暴', desc='敌弹速度 -18%', mods={'espd': .82}),
    dict(id='rich', name='富矿脉', desc='掉落 +50%', mods={'drop': 1.5}),
    dict(id='lowgrav', name='低重力区', desc='移动速度 +20%', mods={'speed': 1.2}),
    dict(id='overload', name='过载场', desc='伤害 +20% · 敌弹 +8%', mods={'dmg': 1.2, 'espd': 1.08}),
    dict(id='quiet', name='静默带', desc='敌机 -18% · 掉落 +30%', mods={'budget': .82, 'drop': 1.3}),
    dict(id='fracture', name='裂解层', desc='射速 +15% · 得分 +15%', mods={'rate': 1.15, 'score': 1.15}),
    dict(id='hunt', name='猎场令', desc='得分 +30% · 敌机 +10%', mods={'score': 1.3, 'budget': 1.1}),
    dict(id='gale', name='湍流带', desc='移动速度 +15% · 敌弹 -10%', mods={'speed': 1.15, 'espd': .9}),
    dict(id='bounty', name='悬赏区', desc='得分 +25% · 掉落 +20%', mods={'score': 1.25, 'drop': 1.2}),
    dict(id='cache', name='回收站', desc='进入本层获得 1 枚护盾', mods={}, entry='shield'),
    dict(id='ambush', name='伏击区', desc='敌机 +20% · 得分 +30%', mods={'budget': 1.2, 'score': 1.3}),
    dict(id='drift', name='漂流带', desc='移动速度 +18% · 敌弹 -15%', mods={'speed': 1.18, 'espd': .85}),
    dict(id='repair', name='维修站', desc='进入本层修复 1 艇体并获 1 护盾', mods={}, entry='repair'),
    dict(id='solar', name='日冕带', desc='伤害 +20% · 敌弹 +10%', mods={'dmg': 1.2, 'espd': 1.1}),
    dict(id='frost', name='霜冻区', desc='敌弹 -18% · 掉落 +20%', mods={'espd': .82, 'drop': 1.2}),
    dict(id='gold', name='黄金回廊', desc='掉落 +40% · 敌机 +10%', mods={'drop': 1.4, 'budget': 1.1}),
    dict(id='mirrorfield', name='镜像场', desc='得分 +25% · 掉落 +20%', mods={'score': 1.25, 'drop': 1.2}),
    dict(id='inferno', name='熔火带', desc='伤害 +25% · 敌人 +10%', mods={'dmg': 1.25, 'budget': 1.1}),
    dict(id='voidcalm', name='虚空静域', desc='敌弹 -15% · 射速 +10%', mods={'espd': .85, 'rate': 1.1}),
    dict(id='blackout', name='无光区', desc='敌弹 -18% · 得分 +20%', mods={'espd': .82, 'score': 1.2}),
    dict(id='overclock', name='超频带', desc='射速 +15% · 敌人 +10%', mods={'rate': 1.15, 'budget': 1.1}),
    dict(id='bloodmoon', name='血月', desc='得分 +25% · 伤害 +10%', mods={'score': 1.25, 'dmg': 1.1}),
    dict(id='mirrorsea', name='镜海', desc='得分 +30% · 掉落 +15%', mods={'score': 1.3, 'drop': 1.15}),
    dict(id='geyser', name='地热喷泉', desc='伤害 +18% · 敌弹 -8%', mods={'dmg': 1.18, 'espd': .92}),
    dict(id='echo', name='回声增幅', desc='射速 +20% · 得分 +20%', mods={'rate': 1.2, 'score': 1.2}),
    dict(id='minefield', name='雷区', desc='敌机 -10% · 掉落 +40%', mods={'budget': .9, 'drop': 1.4}),
    dict(id='singularity', name='奇点潮', desc='伤害 +30% · 移动 -10%', mods={'dmg': 1.3, 'speed': .9}),
    dict(id='blacksun', name='黑日', desc='得分 +40% · 敌弹 +10%', mods={'score': 1.4, 'espd': 1.1}),
    dict(id='sanctum', name='避难所', desc='进入本层修复 1 艇体并获得 1 护盾', mods={}, entry='repair'),
    dict(id='swarm', name='虫群', desc='敌机 +30% · 掉落 +30%', mods={'budget': 1.3, 'drop': 1.3}),
    dict(id='zenith', name='天顶', desc='伤害 +20% · 射速 +15% · 敌机 +15%',
         mods={'dmg': 1.2, 'rate': 1.15, 'budget': 1.15}),
    dict(id='nebula', name='星云带', desc='移动 +22% · 敌弹 -10%', mods={'speed': 1.22, 'espd': .9}),
    dict(id='boneyard', name='骨场', desc='掉落 +35% · 敌机 -5%', mods={'drop': 1.35, 'budget': .95}),
    dict(id='chrono', name='时序裂隙', desc='射速 +12% · 得分 +22%', mods={'rate': 1.12, 'score': 1.22}),
    dict(id='deep_shelter', name='深层避难所', desc='进入本层修复 1 艇体并获得 1 护盾', mods={}, entry='repair'),
    dict(id='mirrorcorr', name='镜面回廊', desc='得分 +35% · 掉落 +15%', mods={'score': 1.35, 'drop': 1.15}),
    dict(id='siren', name='塞壬回廊', desc='掉落 +30% · 敌弹 -15%', mods={'drop': 1.3, 'espd': .85}),
    dict(id='tidal', name='潮汐井', desc='得分 +30% · 掉落 +25%', mods={'score': 1.3, 'drop': 1.25}),
    dict(id='echo_chamber', name='回声室', desc='射速 +25% · 敌弹 +10%', mods={'rate': 1.25, 'espd': 1.1}),
    dict(id='ironrain', name='铁雨', desc='掉落 +50% · 敌机 +15%', mods={'drop': 1.5, 'budget': 1.15}),
    dict(id='whiteout', name='白蚀区', desc='敌弹 -25% · 得分 +10%', mods={'espd': .75, 'score': 1.1}),
    dict(id='reactor', name='裸反应堆', desc='伤害 +35% · 敌弹 +15%', mods={'dmg': 1.35, 'espd': 1.15}),
    dict(id='ashfall', name='灰烬雨', desc='敌机 -15% · 掉落 +35%', mods={'budget': .85, 'drop': 1.35}),
    dict(id='pulse', name='脉冲带', desc='移动 +25% · 得分 +10%', mods={'speed': 1.25, 'score': 1.1}),
    dict(id='deep_current', name='深流', desc='掉落 +30% · 敌弹 -10%', mods={'drop': 1.3, 'espd': .9}),
    dict(id='siren2', name='塞壬合唱', desc='得分 +30% · 掉落 +20%', mods={'score': 1.3, 'drop': 1.2}),
    dict(id='nebularush', name='星流带', desc='射速 +15% · 掉落 +20%', mods={'rate': 1.15, 'drop': 1.2}),
    dict(id='eclipsebelt', name='日蚀带', desc='得分 +25% · 敌弹 -10%', mods={'score': 1.25, 'espd': .9}),
    dict(id='gravewind2', name='墓风区', desc='掉落 +35% · 敌机 -10%', mods={'drop': 1.35, 'budget': .9}),
    dict(id='echostack', name='回声叠层', desc='得分 +30% · 射速 -8%', mods={'score': 1.3, 'rate': .92}),
    dict(id='cinder2', name='余烬带', desc='伤害 +25% · 得分 +15%', mods={'dmg': 1.25, 'score': 1.15}),
    dict(id='deepquiet', name='深静带', desc='敌机 -15% · 得分 +20%', mods={'budget': .85, 'score': 1.2}),
    dict(id='voidpulse', name='脉冲星带', desc='射速 +18% · 敌弹 -12%', mods={'rate': 1.18, 'espd': .88}),
    dict(id='shieldrain', name='护盾雨', desc='进入本层获得 1 枚护盾', mods={}, entry='shield'),
    dict(id='overdrive', name='超载井', desc='伤害 +30% · 射速 +10% · 敌机 +15%',
         mods={'dmg': 1.3, 'rate': 1.1, 'budget': 1.15}),
    dict(id='fogbank', name='浓雾带', desc='敌弹 -20% · 得分 +15%', mods={'espd': .8, 'score': 1.15}),
    dict(id='bloodtide', name='血潮带', desc='伤害 +22% · 掉落 +15% · 得分 +10%',
         mods={'dmg': 1.22, 'drop': 1.15, 'score': 1.1}),
    dict(id='goldeneye', name='金瞳区', desc='掉落 +55% · 敌机 +12%', mods={'drop': 1.55, 'budget': 1.12}),
    dict(id='quietcore', name='静核区', desc='敌机 -20% · 敌弹 -12% · 得分 +25%',
         mods={'budget': .8, 'espd': .88, 'score': 1.25}),
    dict(id='mirrorrain', name='镜雨区', desc='得分 +40% · 敌弹 +10%', mods={'score': 1.4, 'espd': 1.1}),
    # v3.4 新增 12 种层域事件
    dict(id='ambushbelt', name='伏击带', desc='敌机 +25% · 掉落 +25%', mods={'budget': 1.25, 'drop': 1.25}),
    dict(id='lightsout', name='熄灯区', desc='敌弹 -25% · 得分 -10%', mods={'espd': .75, 'score': .9}),
    dict(id='snipernest', name='狙击巢', desc='敌弹 +10% · 伤害 +25%', mods={'espd': 1.1, 'dmg': 1.25}),
    dict(id='reclaimfield', name='回收场', desc='掉落 +40% · 敌机 -10%', mods={'drop': 1.4, 'budget': .9}),
    dict(id='furnacebelt', name='熔炉带', desc='伤害 +30% · 敌弹 +12%', mods={'dmg': 1.3, 'espd': 1.12}),
    dict(id='currentbelt', name='洋流带', desc='移动 +18% · 射速 +10%', mods={'speed': 1.18, 'rate': 1.1}),
    dict(id='bonefield', name='骸骨滩', desc='掉落 +20% · 得分 +20%', mods={'drop': 1.2, 'score': 1.2}),
    dict(id='mirrorzone', name='镜面区', desc='得分 +30% · 敌弹 +5%', mods={'score': 1.3, 'espd': 1.05}),
    dict(id='weightless', name='失重区', desc='移动 +25% · 伤害 -10%', mods={'speed': 1.25, 'dmg': .9}),
    dict(id='goldvein', name='金矿带', desc='掉落 +60% · 敌机 +15%', mods={'drop': 1.6, 'budget': 1.15}),
    dict(id='silentbelt', name='寂流带', desc='敌弹 -18% · 射速 -5%', mods={'espd': .82, 'rate': .95}),
    dict(id='overloadbelt', name='过载带', desc='伤害 +35% · 敌弹 +10% · 得分 +15%',
         mods={'dmg': 1.35, 'espd': 1.1, 'score': 1.15}),
]


def roll_layer_event(layer):
    ev = random.choice(LAYER_EVENTS)
    lm = default_lmod()
    lm.update(ev.get('mods', {}))
    lm['name'], lm['desc'] = ev['name'], ev['desc']
    G.run.lmod = lm
    if ev.get('entry') == 'heal':
        heal_player(1, quiet=True)
    elif ev.get('entry') == 'shield' and G.player:
        G.player.shield = min(3, G.player.shield + 1)
        G.player.shield_t = max(G.player.shield_t, 18)
    elif ev.get('entry') == 'repair' and G.player:
        heal_player(1, quiet=True)
        G.player.shield = min(3, G.player.shield + 1)
        G.player.shield_t = max(G.player.shield_t, 18)
    return ev

# id, name, desc, rarity, key, val, maxstack
AUGS = [
    ('dmg',    '过热弹头', '子弹伤害 +22%',              'c', 'dmg',        1.22, 3),
    ('rate',   '快速循环', '射速 +18%',                  'c', 'rate',       1.18, 3),
    ('hull',   '备用舱段', '艇体上限 +1，并立即回复 1',   'c', 'maxhp',      1,    3),
    ('spd',    '流体力学', '移动速度 +12%',              'c', 'speed',      1.12, 3),
    ('crit',   '弱点扫描', '暴击率 +10%（双倍伤害）',     'c', 'crit',       .10,  4),
    ('pick',   '磁力回收', '拾取范围 +70%',              'c', 'pick',       70,   2),
    ('cdr',    '冷却导管', '技能冷却 -16%',              'c', 'cd',         .84,  3),
    ('multi',  '分叉弹道', '弹道 +1',                    'r', 'bullets',    1,    3),
    ('pierce', '穿透弹芯', '子弹可多穿透 1 个目标',       'r', 'pierce',     1,    3),
    ('homing', '制导弹头', '子弹缓慢追踪最近的敌人',      'r', 'homing',     1,    2),
    ('shock',  '冲击波',   '击杀时产生范围爆炸',          'r', 'shock',      1,    3),
    ('drone',  '僚机',     '增加 1 架环绕无人机',         'r', 'drone',      1,    2),
    ('slow',   '时间淤滞', '击杀后全场减速 0.5 秒',       'r', 'slow',       1,    2),
    ('freeze', '低温弹',   '命中使敌人减速 45%',          'r', 'freeze',     1,    2),
    ('ricochet','跳弹',    '命中后弹向最近的其他敌人',     'r', 'ricochet',   1,    2),
    ('shieldg','再生护盾', '每 10 秒获得 1 枚护盾',       'r', 'shieldgen',  1,    2),
    ('leech',  '生物寄生', '击杀时 20% 概率回复 1 艇体',  'r', 'leech',      1,    2),
    ('dbl',    '双重射击', '32% 概率追加一轮齐射',        'l', 'double',     .32,  2),
    ('vamp',   '深潜代谢', '每 4 次击杀回复 1 艇体',      'l', 'vamp',       1,    2),
    ('pall',   '湮灭弹',   '子弹穿透所有目标',            'l', 'pierce_all', 1,    1),
    ('nova',   '内爆',     '技能命中引发二次冲击',        'l', 'nova',       1,    2),
    ('glass',  '玻璃大炮', '伤害 +45%，艇体上限 -1',      'l', 'glass',      1,    1),
    ('orbit',  '环绕卫星', '两枚光球环绕艇体，接触即灼伤', 'l', 'orbit',     1,    2),
    ('chain',  '连锁放电', '击杀时电弧跳向附近三个目标',   'r', 'chain',     1,    2),
    ('burn',   '燃烧弹',   '命中附加灼烧，两秒内持续掉血', 'r', 'burn',      1,    2),
    ('mirror', '镜面分裂', '子弹命中后向两侧分裂弱化弹',   'l', 'mirror',    1,    1),
    ('frost',  '霜环',     '每六秒释放一次减速冰环',       'r', 'frost',     1,    2),
    ('berserk','背水一战', '艇体越低伤害越高，最多 +60%',  'r', 'berserk',   1,    2),
    ('greed',  '贪婪',     '掉落率 +30%，得分 +15%',       'c', 'greed',     1,    2),
    ('phase',  '相位装甲', '12% 概率完全闪避一次伤害',     'l', 'phase',     1,    2),
    ('critdmg','暴击强化', '暴击伤害 +25%（基础双倍）',     'r', 'critdmg',  1,    2),
    ('thorns', '荆棘护体', '受伤时向四周爆出尖刺',          'r', 'thorns',   1,    2),
    ('regen',  '自愈纤维', '每 26 秒自动回复 1 点艇体',      'r', 'regen',    1,    2),
    ('aura',   '缠滞力场', '身边的敌人持续减速',             'c', 'aura',     1,    2),
    ('bspd',   '超频弹道', '子弹速度 +15%',                  'c', 'bspd',     1,    2),
    ('bigshot','巨型弹芯', '子弹体积 +35%，伤害 +12%',       'r', 'bigshot',  1,    2),
    ('revive', '备用核心', '死亡时以 3 点艇体重生一次',      'l', 'revive',   1,    1),
    ('luck',   '幸运罗盘', '传说增幅出现率 +35%',            'l', 'luck',     1,    2),
    ('skillpow','技能强化','技能伤害与效果 +25%',            'r', 'skillpow', 1,    2),
    ('exec',   '处决弹',   '对残血目标伤害 +35%',            'c', 'exec',     1,    3),
    ('afterburn','余烬尾迹','击杀处留下持续灼烧的火圈',       'r', 'afterburn',1,    2),
    ('warp',   '相位跃迁', '每 7 秒自动向前闪现，短暂无敌',    'l', 'warp',     1,    2),
    ('siphon', '汲能线圈', '拾取掉落时技能冷却 -1.5 秒',      'c', 'siphon',   1,    2),
    ('lance',  '长矛弹',   '穿透 +2、弹速 +25%、射速 -10%',   'r', 'lance',    1,    1),
    ('brood',  '母巢协议', '额外召唤 1 架环绕无人机',          'l', 'drone',    1,    1),
    ('gambler','赌徒筹码', '得分 +35%，掉落率 -20%',          'c', 'gambler',  1,    2),
    ('core',   '过载核心', '子弹伤害 +30%',                   'r', 'dmg',      1.3,  2),
    ('cool',   '冷却矩阵', '技能冷却 -18%',                    'c', 'cd',       .82,  2),
    ('first',  '先手校准', '对满血目标伤害 +35%',              'r', 'first',    1,    2),
    ('overk',  '溢出爆裂', '击杀时溢出伤害引发爆炸',            'r', 'overk',    1,    2),
    ('shkill', '战利护盾', '每 7 次击杀获得 1 枚护盾',          'c', 'shieldkill', 1,  2),
    ('spread', '扇面发射', '弹道 +1，单发伤害 -14%',            'r', 'spread',   1,    2),
    ('rail',   '磁轨弹芯', '穿透 +1，弹速 +18%',                'c', 'rail',     1,    2),
    ('pickheal','回收修复', '每 9 次拾取回复 1 艇体',           'c', 'pickheal', 1,    2),
    ('critboom','暴击内爆', '暴击击杀引发范围爆炸',             'l', 'critboom', 1,    1),
    ('soul',   '灵魂配额', '每 30 击杀，艇体上限 +1',           'l', 'soul',     1,    1),
    ('retaliate','受伤反击', '受伤时向四周射出 10 发子弹',      'r', 'retaliate',1,    2),
    ('fragile','临界过载', '伤害 +55%，每次受伤 +1',            'l', 'fragile',  1,    1),
    ('chill',  '霜蚀',     '对减速目标伤害 +25%',              'r', 'chill',    1,    2),
    ('shburst','护盾爆裂', '护盾被击破时引发冲击波',            'r', 'shieldburst', 1, 2),
    ('bossbane','弑主者',  '对 BOSS 伤害 +25%',                'r', 'bossbane', 1,    2),
    ('rapid',  '极速扳机', '射速 +18%',                        'c', 'rate',     .82,  2),
    ('lite',   '轻量艇体', '移动速度 +18%',                    'c', 'speed',    1.18, 2),
    ('magnet', '磁力拾取', '拾取范围 +50',                     'c', 'pick',     50,   2),
    ('plating','复合装甲', '艇体上限 +1',                      'r', 'maxhp',    1,    2),
    ('deadeye','精密瞄准', '暴击率 +8%',                       'r', 'crit',     .08,  2),
    ('hot',    '高燃弹头', '燃烧层数 +1',                      'r', 'burn',     1,    2),
    ('frostbite','冻蚀弹头','冻结层数 +1',                     'r', 'freeze',   1,    2),
    ('bounce', '跳弹涂层', '弹跳次数 +1',                      'c', 'ricochet', 1,    2),
    ('drill',  '穿甲钻头', '穿透 +1',                          'c', 'pierce',   1,    2),
    ('seeker', '寻的模块', '追踪强度 +1',                      'r', 'homing',   1,    2),
    ('heavy',  '重型弹体', '弹体体积 +1',                      'r', 'bigshot',  1,    2),
    ('pointblank','贴脸火力','280 范围内伤害 +30%',            'r', 'close',    .3,   2),
    ('longshot','远距校准','520 范围外伤害 +25%',              'r', 'far',      .25,  2),
    ('finisher','终局处决','对 25% 以下目标伤害 +40%',         'l', 'finisher', .4,   1),
    ('guard',  '护盾发生器','每 10 秒生成 1 枚护盾',           'l', 'shieldgen',1,    1),
    ('swift',  '疾行推进', '移动速度 +15%',                     'c', 'speed',    1.15, 2),
    ('overclock','超频供弹','射速 +15%',                        'c', 'rate',     .85,  2),
    ('broadside','侧舷齐射','弹道 +1，单发伤害 -12%',          'r', 'spread',   1,    2),
    ('caliber','大口径',   '子弹伤害 +25%',                    'r', 'dmg',      1.25, 2),
    ('critpower','暴击核心','暴击伤害 +35%',                    'r', 'critdmg',  .35,  2),
    ('cooling','冷却回路', '技能冷却 -10%',                    'c', 'cd',       .9,   2),
    ('hullplate','厚壳装甲','艇体上限 +1',                     'r', 'maxhp',    1,    2),
    ('magnet2','引力拾取', '拾取范围 +40',                     'c', 'pick',     40,   2),
    ('shieldgen2','护盾核心','每 10 秒生成 1 枚护盾',          'l', 'shieldgen',1,    1),
    ('pierceall','贯穿弹芯','所有子弹额外穿透 +1',              'l', 'pierce_all',1,   1),
    ('orbital','轨道卫星', '召唤 1 架环绕无人机',              'r', 'drone',    1,    2),
    ('boom',   '爆裂核心', '暴击击杀引发范围爆炸',              'l', 'critboom', 1,    1),
    ('freeze2','冻蚀弹芯', '冻结层数 +1',                      'r', 'freeze',   1,    2),
    ('burn2',  '燃焰弹芯', '燃烧层数 +1',                      'r', 'burn',     1,    2),
    ('repair', '纳米修复', '每秒缓慢回复艇体',                  'l', 'regen',    1,    1),
    ('velocity','超速弹芯','子弹速度 +30%',                    'c', 'bspd',     1.3,  2),
    ('precision','精算火控','暴击率 +8%',                      'r', 'crit',     .08,  2),
    ('execution','处决协议','对低血目标伤害 +35%',              'r', 'exec',     1,    2),
    ('overpressure','超压弹头','子弹伤害 +20%',                 'r', 'dmg',      1.2,  2),
    ('lightframe','轻质框架','移动速度 +12%',                   'c', 'speed',    1.12, 2),
    ('autoloader','自动装填','射速 +10%',                       'c', 'rate',     .90,  2),
    ('hardened','硬化艇壳','艇体上限 +1',                       'r', 'maxhp',    1,    2),
    ('lucky','幸运回路', '掉落与拾取收益提升',                  'c', 'luck',     1,    2),
    ('frostfield','寒霜力场','附近敌人持续减速',                'r', 'aura',     1,    2),
    ('soulclaim','灵魂追缴','击杀累积艇体上限',                 'l', 'soul',     1,    1),
    ('leech2', '汲取装甲', '击杀回复艇体',                      'r', 'leech',    1,    2),
    ('chain2', '链式雷暴', '子弹命中时弹射闪电',                'l', 'chain',    1,    2),
    ('drone2', '轨道增援', '额外召唤 1 架环绕无人机',           'r', 'drone',    1,    2),
    ('thorns2','反射甲片', '受击时反弹伤害',                    'r', 'thorns',   1,    2),
    ('regen2', '再生膜',   '持续缓慢回复艇体',                  'l', 'regen',    1,    1),
    ('boomer', '回旋刃',   '定期掷出会飞回的回旋刃',              'r', 'boomer',   1,    2),
    ('mine',   '追踪雷',   '定期布下会自动引爆的感应雷',          'r', 'mine',     1,    2),
    ('blade',  '环绕刃',   '艇体周围增加一把持续切割的环绕刃',    'l', 'blade',    1,    2),
    ('shotgun','散射炮',   '每次射击额外散射两枚弹丸',            'c', 'shot',     1,    2),
    ('railgun','磁轨炮',   '子弹穿透 +1，弹速 +18%',             'c', 'rail',     1,    2),
    ('split',  '分裂弹',   '命中后分裂出两枚偏折弹',              'r', 'mirror',   1,    2),
    ('ricochet2','跳弹镀层','命中后反弹一次',                    'c', 'ricochet', 1,    2),
    ('homing3','寻敌弹头', '子弹自动追踪附近敌机',               'r', 'homing',   1,    2),
    ('crit3',  '致命准星', '暴击率 +6%',                         'r', 'crit',     .06,  2),
    ('bspd3',  '高速弹道', '子弹速度 +15%',                      'c', 'bspd',     1,    2),
    ('pierce3','穿甲弹芯', '穿透 +1',                            'c', 'pierce',   1,    2),
    ('freeze3','冻结弹头', '命中后冻缓目标',                     'r', 'freeze',   1,    2),
    ('burn3',  '燃烧弹头', '命中后附加持续燃烧',                 'r', 'burn',     1,    2),
    ('shock3', '冲击弹头', '命中时释放小范围冲击波',              'l', 'shock',    1,    2),
    ('shieldgen3','护盾阵列','每 10 秒补充 1 层护盾',          'l', 'shieldgen',1,    1),
    ('regen3', '活体装甲', '持续回复艇体',                       'l', 'regen',    1,    1),
    ('vamp3',  '嗜血弹头', '击杀回复艇体',                       'r', 'vamp',     1,    2),
    ('drone3', '蜂群增援', '额外召唤 1 架环绕无人机',            'r', 'drone',    1,    2),
    ('thorns3','尖刺装甲', '受击时反弹伤害',                     'c', 'thorns',   1,    2),
    ('luck2',  '幸运齿轮', '掉落与拾取收益提升',                  'c', 'luck',     1,    2),
    ('voidlance','虚空长矛','子弹伤害 +30%',                       'l', 'dmg',      1.3,  1),
    ('hyperdrive','超驱引擎','射速 +18%',                          'r', 'rate',     1.18, 1),
    ('trident', '三叉戟',   '弹道 +1',                              'r', 'bullets',  1,    1),
    ('sunfire', '日冕火种', '命中后附加持续燃烧',                    'l', 'burn',     1,    2),
    ('frostcore','霜核',    '命中后冻缓目标',                        'l', 'freeze',   1,    2),
    ('seeker2',  '寻猎弹头', '子弹自动追踪附近敌机',                  'r', 'homing',   1,    2),
    ('reaper',  '收割者',   '击杀回复艇体',                          'r', 'vamp',     1,    2),
    ('bastion2','堡垒膜',   '每 9 秒补充 1 层护盾',                  'l', 'shieldgen',1,    1),
    ('nanorepair','活体修补','持续缓慢回复艇体',                     'l', 'regen',    1,    1),
    ('swarm2',  '蜂群协议', '额外召唤 1 架环绕无人机',              'l', 'drone',    1,    1),
    ('blade2',  '切割环',   '艇体周围增加一把环绕刃',                'l', 'blade',    1,    1),
    ('fate',    '命运准星', '暴击率 +8%',                            'l', 'crit',     .08,  1),
    ('refract2','折射涂层', '命中后反弹一次',                        'c', 'ricochet', 1,    1),
    # v2.9 新增幅：把既有战斗系统继续往外扩，每一类都能叠出新花样
    ('glasscannon','玻璃炮', '伤害 +45% · 艇体上限 -1',              'l', 'glass',    1,    1),
    ('overclock2','超频枪机', '射速 +24% · 弹道散布略增',              'l', 'rate',     1.24, 1),
    ('longbarrel','长管加速', '子弹速度 +30%',                       'r', 'bspd',     .30,  2),
    ('siege','攻城弹', '子弹体积与伤害提升',                         'l', 'bigshot',  1,    1),
    ('flak','破片套件', '弹道 +1 · 单发伤害略降',                     'r', 'spread',   1,    2),
    ('railgun2','磁轨套件', '弹道更直、穿透更强',                    'l', 'rail',     1,    1),
    ('soulfire','魂火', '每 30 击杀 · 艇体上限 +1',                   'l', 'soul',     1,    2),
    ('frostnova','霜新星', '技能命中引发冻结冲击',                    'l', 'nova',     1,    2),
    ('orbit3','第三环刃', '再增加一把环绕刃',                        'r', 'orbit',    1,    3),
    ('chain3','链式电弧', '击杀时电弧跳向更多目标',                  'l', 'chain',    1,    2),
    ('aura2','腐蚀光环', '靠近的敌机持续受伤',                       'r', 'aura',     1,    2),
    ('exec2','猎杀协议', '低血量目标受到额外伤害',                   'l', 'exec',     1,    2),
    ('laststand','先手猎杀', '对满血目标伤害 +35%',                    'l', 'first',    1,    1),
    ('highroller','豪赌筹码', '得分 +35% · 掉落率 -20%',              'r', 'gambler',  1,    2),
    ('bossbane2','弑王弹头', '对 BOSS 伤害 +25%',                    'l', 'bossbane', 1,    2),
    ('magnet3','深潜磁石', '拾取范围 +60',                          'c', 'pick',     60,   2),
    ('veteran','老练装填', '技能冷却 -18%',                          'r', 'cd',      .82,  1),
    # v3.0 新增：12 项通用增幅，覆盖伤害、射速、暴击、弹道、生存与幸运
    ('overcharge2','超载弹头', '子弹伤害 +18%',                       'r', 'dmg',     1.18, 2),
    ('cyclic2',   '循环供弹', '射速 +16%',                           'r', 'rate',    1.16, 2),
    ('focus2',    '聚焦准星', '暴击率 +7%',                           'c', 'crit',    .07,  2),
    ('weakpoint', '弱点标记', '暴击伤害 +35%',                         'l', 'critdmg', 1,    2),
    ('salvo',     '齐射阵列', '弹道 +1',                              'l', 'bullets', 1,    1),
    ('drill2',    '双层钻头', '穿透 +1',                              'r', 'pierce',  1,    2),
    ('current2',  '顺流推进', '移动速度 +12%',                        'c', 'speed',   1.12, 2),
    ('fortune2',  '深渊红利', '幸运 +1（稀有/传说增幅更常出现）',       'l', 'luck',    1,    2),
    ('mend2',     '自愈凝胶', '每 26 秒回复 1 点艇体',                 'r', 'regen',   1,    2),
    ('aegis2',    '神盾回路', '每 10 秒补充 1 层护盾',                 'l', 'shieldgen', 1,  1),
    ('vent2',     '散热旁路', '技能冷却 -12%',                         'r', 'cd',      .88,  2),
    ('hunt3',     '猎王校准', '对 BOSS 伤害 +20%',                     'l', 'bossbane', 1,   2),
    # v3.2 新增：16 项构筑向增幅，覆盖近战、控场、暴击、护盾与贪分流
    ('voidbrand', '虚空烙印', '子弹伤害 +30%',                          'l', 'dmg',      1.30, 1),
    ('accelerant','助燃剂',   '子弹速度 +30%',                          'r', 'bspd',     .30,  2),
    ('fateweave', '命运编织', '稀有与传说增幅出现率提升',                'l', 'luck',     1,    2),
    ('shieldweave','护盾编织','每 9 秒补充 1 层护盾',                   'l', 'shieldgen', 1,  1),
    ('bloodpact', '血契',     '击杀回复艇体',                           'r', 'vamp',     1,    2),
    ('eventide',  '暮色回路', '技能冷却 -18%',                          'r', 'cd',      .82,  2),
    ('cluster',   '集束阵列', '弹道 +1',                                'l', 'bullets',  1,    1),
    ('overrun',   '超跑推进', '移动速度 +20%',                          'c', 'speed',    1.20, 2),
    ('targetlock','锁定协议', '子弹自动追踪附近敌机',                   'r', 'homing',   1,    2),
    ('pierce4',   '四重穿透', '子弹额外穿透 1 个目标',                  'c', 'pierce',   1,    3),
    ('cinder3',   '余烬弹头', '命中附加灼烧',                           'r', 'burn',     1,    2),
    ('rime3',     '霜纹弹头', '命中冻缓目标',                           'r', 'freeze',   1,    2),
    ('gravity',   '重力井弹', '击杀后全场减速',                         'r', 'slow',     1,    2),
    ('reclaim',   '回收矩阵', '拾取范围 +80',                           'c', 'pick',     80,   2),
    ('lastword',  '终言弹',   '对残血目标伤害提升',                     'l', 'exec',     1,    2),
    ('counter',   '反击甲片', '受击时反弹尖刺',                         'r', 'thorns',   1,    2),
    # v3.4 新增：12 项终局构筑，覆盖机动、蜂群、爆发与生存
    ('voidengine', '虚空引擎', '移动速度 +14%',                         'r', 'speed',    1.14, 2),
    ('echoheart',  '回声心脏', '艇体上限 +1，并立即回复 1',              'r', 'maxhp',    1,    2),
    ('swarmsoul',  '蜂群之魂', '额外召唤 1 架环绕无人机',                'l', 'drone',    1,    2),
    ('crimson',    '绯红弹头', '子弹伤害 +28%',                          'l', 'dmg',      1.28, 1),
    ('glacier',    '冰川弹芯', '命中冻缓目标',                           'r', 'freeze',   1,    2),
    ('tempest',    '风暴线圈', '击杀时电弧跳向附近目标',                 'l', 'chain',    1,    2),
    ('aegis3',     '神盾矩阵', '每 9 秒补充 1 层护盾',                   'l', 'shieldgen',1,    1),
    ('hunter3',    '猎王视界', '对 BOSS 伤害 +25%',                      'l', 'bossbane', 1,    2),
    ('lastlight',  '终光',     '艇体越低伤害越高，最多 +60%',            'l', 'berserk',  1,    1),
    ('mirrorcore', '镜核',     '命中后弹向最近的其他敌人',               'r', 'ricochet', 1,    2),
    ('rail3',      '超磁轨',   '穿透 +2，弹速 +18%',                     'l', 'pierce',   2,    1),
    ('fortuneblade','幸运刃',  '稀有与传说增幅出现率提升',               'l', 'luck',     1,    2),
]
AUG_BY_ID = {a[0]: a for a in AUGS}
RARITY_COL = {'c': 'steel', 'r': 'violet', 'l': 'gold'}
RARITY_NAME = {'c': '常见', 'r': '稀有', 'l': '传说'}

FLAVOR = {
    'dmg': '弹头在出膛前就已经烧红了。',
    'rate': '机械比心跳更耐操。',
    'hull': '焊上去的铁皮，也算艇体。',
    'spd': '水压替你让路。',
    'crit': '它眨眼的瞬间就够了。',
    'pick': '沉下去的东西，也能捞回来。',
    'cdr': '热得越慢，喊得越久。',
    'multi': '一条弹道不够，就多开几条。',
    'pierce': '第一层皮不算数。',
    'homing': '它会自己找上门。',
    'shock': '每一次死亡都带回声。',
    'drone': '多一双眼睛盯着黑水。',
    'slow': '把这片水拖进泥里。',
    'freeze': '冷到骨头发脆。',
    'ricochet': '墙也是敌人。',
    'shieldg': '伤口会自己结痂。',
    'leech': '吃掉它，就多一点自己。',
    'dbl': '扳机扣一次，枪管响两回。',
    'vamp': '深渊的规矩：吃，或者被吃。',
    'pall': '挡在路上的都不存在。',
    'nova': '光矛落下之后，还有第二下。',
    'glass': '艇体会碎，但你打得更狠。',
    'orbit': '它们不说话，只绕着转。',
    'chain': '一声雷，接着是第二声。',
    'burn': '烧到它自己熄灭为止。',
    'mirror': '子弹也照镜子。',
    'frost': '冷得连逃跑都慢半拍。',
    'berserk': '伤得越重，扣扳机越狠。',
    'greed': '深渊里没有白捡的东西。',
    'phase': '有一半的你已经不在这一层了。',
    'critdmg': '弱点对齐之后，只要一下。',
    'thorns': '碰你的人也该付出点什么。',
    'regen': '慢慢地，把裂口补回去。',
    'aura': '靠近它的东西都会变慢。',
    'bspd': '快到来不及看清弹道。',
    'bigshot': '体积越大，越难被忽略。',
    'revive': '还有一副备用的心跳。',
    'luck': '深渊偶尔也会开玩笑。',
    'skillpow': '把每一次爆发都推到底。',
    'exec': '收尾的时候不需要客气。',
    'afterburn': '它烧完，火还没有灭。',
    'warp': '你已经不在它瞄准的那个位置了。',
    'siphon': '把它们的余温抽回来。',
    'lance': '一根钉子，穿三块木板。',
    'brood': '巢里又爬出来一只。',
    'gambler': '赢的时候，回廊会多给你一点。',
    'core': '红线的尽头是更大的响声。',
    'cool': '冷静的人活得更久。',
    'first': '第一枪，永远最容易。',
    'overk': '多出来的那一截，也不会浪费。',
    'shkill': '杀够数，壳就自己长出来。',
    'spread': '把一束光拆成一把扇。',
    'rail': '一根钉子，穿过三块板。',
    'pickheal': '沉下来的残骸，也能补伤口。',
    'critboom': '弱点炸开时，周围也一起碎。',
    'soul': '每三十个亡魂，换一层新壳。',
    'retaliate': '挨了一下，就还十下。',
    'fragile': '壳薄了，拳头就更重。',
    'chill': '冻住的敌人，更容易敲碎。',
    'shburst': '壳碎的时候，碎片也会飞。',
    'bossbane': '越大的东西，越该被钉住。',
    'rapid': '扳机还没回位，下一发已经出去了。',
    'lite': '拆掉两块装甲，换一双快腿。',
    'magnet': '沉下去的东西，自己会浮上来。',
    'plating': '多一层壳，就多一条命。',
    'deadeye': '准星里只剩下一个点。',
    'hot': '烧起来之后，才轮到它们害怕。',
    'frostbite': '冷到骨髓里，连火都点不着。',
    'bounce': '墙不是障碍，是第二条弹道。',
    'drill': '一层皮不算数，两层也不算。',
    'seeker': '它会自己找过去。',
    'heavy': '弹体越大，越难被忽略。',
    'pointblank': '越近，越没有躲的余地。',
    'longshot': '在它看见你之前，先看见它。',
    'finisher': '收尾的时候，不用讲道理。',
    'guard': '每隔十秒，壳就自己长出来。',
    'swift': '轻一点，再轻一点，快得抓不住。',
    'overclock': '枪管发红也不停，停下来的都沉底了。',
    'broadside': '正面一条，旁边还有两条。',
    'caliber': '口径就是道理。',
    'critpower': '打中要害，剩下的交给爆炸。',
    'cooling': '让热量先走一步。',
    'hullplate': '再加一层，沉得慢一点。',
    'magnet2': '沉在泥里的，也给你吸上来。',
    'shieldgen2': '壳会自己长，伤会自己合。',
    'pierceall': '没有一层壳能拦住第二次。',
    'orbital': '天上多了一颗只围着你的星。',
    'boom': '暴击之后，还有一圈回声。',
    'freeze2': '冻住的不只是血。',
    'burn2': '烧起来，就没有退路。',
    'repair': '破口会自己长回去，慢一点而已。',
    'velocity': '弹丸跑得比声音快，敌人来不及听见。',
    'precision': '准星收拢，误差沉底。',
    'execution': '血少的，先处理掉。',
    'overpressure': '装药多一格，道理就多一分。',
    'lightframe': '拆掉配重，换一身轻快。',
    'autoloader': '手不用动，枪管自己续上。',
    'hardened': '再加一层硬化壳。',
    'lucky': '有些东西，天生就该落到你手里。',
    'frostfield': '靠近的东西，都会慢下来。',
    'soulclaim': '每一次死亡，都记在你账上。',
    'leech2': '咬穿它，把血补回自己身上。',
    'chain2': '命中的地方，雷会自己找下一个。',
    'drone2': '轨道上又多了一双眼睛。',
    'thorns2': '碰你一下，它自己也要掉块肉。',
    'regen2': '伤口会合，像什么都没发生。',
    'boomer': '掷出去，再让它自己回来。',
    'mine': '把死亡埋在路上，等它自己踩。',
    'blade': '贴着艇体转的刃，不认主人。',
    'shotgun': '不追求准，追求整片都疼。',
    'railgun': '一根钉子，穿过三块板。',
    'split': '打中之后，它才真正开始。',
    'ricochet2': '墙也是弹道的一部分。',
    'homing3': '跑吧，它会拐弯。',
    'crit3': '把运气校准成杀意。',
    'bspd3': '快到你来不及眨眼。',
    'pierce3': '一层甲，不够。',
    'freeze3': '让它在半空中停住。',
    'burn3': '伤口里留一点火。',
    'shock3': '命中不是结束，是扩散。',
    'shieldgen2': '壳会自己长回来。',
    'shieldgen3': '壳会自己长回来。',
    'regen3': '活着的装甲，会愈合。',
    'vamp3': '它的血，补你的洞。',
    'drone3': '轨道上又多了一双眼睛。',
    'thorns3': '碰你一下，它自己也要掉块肉。',
    'luck2': '有些东西，天生就该落到你手里。',
}

def pack_choice(rarity):
    """按稀有度产出三张互不重复的增幅卡"""
    weights = {
        'wave': {'c': 62, 'r': 30, 'l': 8},
        'boss': {'c': 28, 'r': 50, 'l': 22},
        'start': {'c': 72, 'r': 24, 'l': 4},
    }[rarity]
    pool = [a for a in AUGS if G.run.aug_count(a[0]) < a[6]]
    if not pool:
        pool = list(AUGS)
    if G.run and G.run.st['luck'] > 0:
        weights = dict(weights)
        weights['l'] = weights['l'] * (1 + .35 * G.run.st['luck'])
    out = []
    tries = 0
    while len(out) < 3 and tries < 200:
        tries += 1
        a = random.choices(pool, weights=[weights[a[3]] for a in pool], k=1)[0]
        if a not in out:
            out.append(a)
    return out

# ================================================================
#  海域事件（每局随机抽一个，改变整局规则）
# ================================================================
MUTS = [
    dict(id='calm', name='静默带', desc='敌人艇体 -12%，掉落率 -25%', ehp=.88, drop=.75),
    dict(id='rich', name='富集层', desc='掉落率 +45%，得分 -8%', drop=1.45, score=.92),
    dict(id='dense', name='密集回响', desc='每波敌人 +30%，得分 +22%', budget=1.3, score=1.22),
    dict(id='elite', name='精英潮', desc='精英出现率翻倍', elite=2.0),
    dict(id='pressure', name='深压带', desc='艇体上限 -1，伤害 +28%', maxhp=-1, dmg=1.28),
    dict(id='storm', name='电子风暴', desc='技能冷却 -30%，敌弹 -12%', cd=.7, espd=.88),
    dict(id='wreck', name='遗骸场', desc='开局随机获得一件增幅', start_aug=True, score=.9),
    dict(id='hush', name='无声猎场', desc='敌弹速度 -18%，敌人艇体 +12%', espd=.82, ehp=1.12),
    dict(id='rush', name='急流', desc='移动速度 +14%，每波敌人 +15%', speed=1.14, budget=1.15),
    dict(id='ancient', name='古菌层', desc='持续缓慢回血，敌人艇体 +18%', ehp=1.18, regen=True),
    dict(id='long', name='长夜回廊', desc='敌人密度 -12%，掉落 +30%', budget=.88, drop=1.3),
    dict(id='hunt', name='猎场协议', desc='精英出现率 +60%，得分 +25%', elite=1.6, score=1.25),
    dict(id='shell', name='脆壳层', desc='敌人艇体 -18%，敌弹速度 +12%', ehp=.82, espd=1.12),
    dict(id='bounty', name='悬赏回廊', desc='得分 +30%，掉落 -15%', score=1.3, drop=.85),
    dict(id='swarm', name='蜂拥层', desc='每波敌人 +20%，掉落 +15%', budget=1.2, drop=1.15),
    dict(id='glass', name='薄壳层', desc='艇体上限 -1，伤害 +35%', maxhp=-1, dmg=1.35),
    dict(id='luckyvein', name='幸运矿脉', desc='掉落 +40%，敌弹 +10%', drop=1.4, espd=1.1),
    dict(id='silent', name='静默回廊', desc='敌弹 -20%，技能冷却 -15%', espd=.8, cd=.85),
    dict(id='frenzy', name='狂潮回廊', desc='伤害 +28%，艇体上限 -1', dmg=1.28, maxhp=-1),
    dict(id='vacuum', name='真空回廊', desc='移动速度 +12%，敌弹 -15%', speed=1.12, espd=.85),
    dict(id='bloodpact', name='血偿回廊', desc='艇体上限 +1，敌人 +20%', maxhp=1, budget=1.2),
    dict(id='lucky', name='幸运回廊', desc='掉落 +35%，敌人 +15%', drop=1.35, budget=1.15),
    dict(id='starfall', name='星落回廊', desc='精英出现率 +50%，得分 +20%', elite=1.5, score=1.2),
    dict(id='molten', name='熔核回廊', desc='伤害 +30%，艇体上限 -1', dmg=1.3, maxhp=-1),
    dict(id='echo', name='回声回廊', desc='技能冷却 -20%，敌人 +10%', cd=.8, budget=1.1),
    dict(id='overdrive', name='超载回廊', desc='伤害 +35%，艇体上限 -1', dmg=1.35, maxhp=-1),
    dict(id='swarm2', name='蜂群回廊', desc='每波敌人 +35%，精英 -30%', budget=1.35, elite=.7),
    dict(id='tide', name='潮汐回廊', desc='敌弹速度 +20%，掉落 +25%', espd=1.2, drop=1.25),
    dict(id='still', name='静水回廊', desc='敌弹速度 -20%，掉落 +30%', espd=.8, drop=1.3),
    dict(id='overclock2', name='超频回廊', desc='技能冷却 -25%，敌弹 +10%', cd=.75, espd=1.1),
    dict(id='iron', name='铁壁回廊', desc='敌人艇体 +25%，掉落 +25%', ehp=1.25, drop=1.25),
    dict(id='phantom', name='幻影回廊', desc='移动 +20%，敌弹 -10%', speed=1.2, espd=.9),
    dict(id='scavenger', name='拾荒回廊', desc='掉落 +50%，得分 -10%', drop=1.5, score=.9),
    dict(id='nightmare2', name='噩梦回廊', desc='敌人 +40%，得分 +30%', budget=1.4, score=1.3),
    dict(id='juggernaut', name='重装回廊', desc='艇体上限 +1，敌人 +15%', maxhp=1, budget=1.15),
    dict(id='fury', name='狂怒回廊', desc='伤害 +40%，敌弹 +15%', dmg=1.4, espd=1.15),
    dict(id='gambit', name='弃子回廊', desc='艇体上限 -1，掉落 +45%', maxhp=-1, drop=1.45),
    dict(id='zeitgeist', name='时序乱流', desc='技能冷却 -25%，敌弹 -10%', cd=.75, espd=.9),
    dict(id='redline', name='红线回廊', desc='伤害 +32%，移动 +8%', dmg=1.32, speed=1.08),
    dict(id='frostbite', name='霜蚀回廊', desc='敌人艇体 -10%，敌弹 -18%', ehp=.9, espd=.82),
    dict(id='jackpot', name='头奖回廊', desc='掉落 +55%，得分 -12%', drop=1.55, score=.88),
    dict(id='twin', name='双子回廊', desc='精英出现率 +80%，敌人 +10%', elite=1.8, budget=1.1),
    dict(id='quiet2', name='深静回廊', desc='敌弹 -22%，技能冷却 -10%', espd=.78, cd=.9),
    dict(id='mirrorpact', name='镜约回廊', desc='掉落 +40%，敌弹 +12%', drop=1.4, espd=1.12),
    dict(id='gravewind', name='墓风回廊', desc='敌人 +25%，精英 +45%', budget=1.25, elite=1.45),
    dict(id='solarflare', name='耀斑回廊', desc='伤害 +38%，敌弹 +18%', dmg=1.38, espd=1.18),
    dict(id='deepdive', name='深潜回廊', desc='艇体上限 +1，敌人 +18%', maxhp=1, budget=1.18),
    dict(id='echo2', name='回声叠层', desc='技能冷却 -30%，敌弹 -12%', cd=.7, espd=.88),
    dict(id='cinder', name='余烬回廊', desc='敌人 -15%，掉落 +35%', ehp=.85, drop=1.35),
    dict(id='abyssal', name='深渊回廊', desc='敌人 +35%，得分 +35%', budget=1.35, score=1.35),
    dict(id='stormfront', name='风暴前沿', desc='敌弹 +15%，掉落 +20%', espd=1.15, drop=1.2),
    dict(id='thunder', name='雷暴回廊', desc='射速 +15%，敌人 +15%', rate=1.15, budget=1.15),
    dict(id='solar3', name='烈阳回廊', desc='伤害 +25%，得分 +20%', dmg=1.25, score=1.2),
    dict(id='grave3', name='墓园回廊', desc='掉落 +45%，移动 -10%', drop=1.45, speed=.9),
    dict(id='zero', name='零度回廊', desc='敌弹 -25%，敌人 +15%', espd=.75, budget=1.15),
    dict(id='ember', name='烬火回廊', desc='伤害 +20%，敌弹 -15%', dmg=1.2, espd=.85),
    dict(id='salt', name='盐霜回廊', desc='敌人艇体 -12%，掉落 +20%', ehp=.88, drop=1.2),
    dict(id='gear', name='齿轮回廊', desc='射速 +20%，敌人 +10%', rate=1.2, budget=1.1),
    dict(id='imaginary', name='虚数回廊', desc='技能冷却 -20%，敌弹 -10%', cd=.8, espd=.9),
    dict(id='eye', name='终末回廊', desc='伤害 +30%，艇体上限 -1', dmg=1.3, maxhp=-1),
    dict(id='shelter2', name='庇护回廊', desc='艇体上限 +1，掉落 -10%', maxhp=1, drop=.9),
    dict(id='prism3', name='棱镜回廊', desc='得分 +30%，敌弹 -10%', score=1.3, espd=.9),
    dict(id='overrun2', name='超跑回廊', desc='移动 +20%，敌人 +15%', speed=1.2, budget=1.15),
    dict(id='harvest', name='丰收回廊', desc='掉落 +50%，敌人艇体 +10%', drop=1.5, ehp=1.1),
    # v3.4 新增 12 条局内突变
    dict(id='mirage', name='蜃景回廊', desc='得分 +25%，敌弹 -10%', score=1.25, espd=.9),
    dict(id='irontide', name='铁潮回廊', desc='伤害 +20%，移动 -5%', dmg=1.2, speed=.95),
    dict(id='siren', name='塞壬回廊', desc='敌弹 -15%，掉落 +20%', espd=.85, drop=1.2),
    dict(id='fracture2', name='裂隙回廊', desc='伤害 +30%，敌人艇体 +10%', dmg=1.3, ehp=1.1),
    dict(id='locust', name='蝗群回廊', desc='敌人 +20%，掉落 +25%', budget=1.2, drop=1.25),
    dict(id='candle', name='烛火回廊', desc='艇体上限 +1，射速 +8%', maxhp=1, rate=.92),
    dict(id='deeppact', name='暗流回廊', desc='伤害 +35%，艇体上限 -1', dmg=1.35, maxhp=-1),
    dict(id='drift', name='漂移回廊', desc='移动 +25%，敌弹 +10%', speed=1.25, espd=1.1),
    dict(id='husk', name='空壳回廊', desc='敌人艇体 -10%，得分 +15%', ehp=.9, score=1.15),
    dict(id='hymn', name='圣歌回廊', desc='技能冷却 -15%，掉落 -5%', cd=.85, drop=.95),
    dict(id='furnace2', name='熔炉回廊', desc='伤害 +25%，敌弹 +15%', dmg=1.25, espd=1.15),
    dict(id='final', name='终局回廊', desc='得分 +40%，敌人 +20%', score=1.4, budget=1.2),
]

WAVE_TAGS = [
    dict(name='', w={}),
    dict(name='冲锋潮', w={'charger': 2.6, 'hunter': 2.2, 'bomber': 2.0}),
    dict(name='碎裂群', w={'splitter': 2.8, 'spark': 1.6}),
    dict(name='织网带', w={'weaver': 2.6, 'lantern': 1.8}),
    dict(name='炮台阵', w={'turret': 2.2, 'marc': 2.0, 'sniper': 2.0}),
    dict(name='蜂群', w={'spark': 3.2, 'drifter': 1.6}),
    dict(name='重装队', w={'bulwark': 2.8, 'spinner': 1.8}),
    dict(name='俯冲队', w={'dart': 3.0, 'charger': 1.8}),
    dict(name='光栅带', w={'laser': 2.6, 'sniper': 2.0}),
    dict(name='巢群', w={'spawner': 2.4, 'spark': 2.2}),
    dict(name='游魂群', w={'orb': 2.8, 'splitter': 1.6}),
    dict(name='光栅阵', w={'sweeper': 2.6, 'laser': 1.8}),
    dict(name='守门群', w={'warden': 2.6, 'bulwark': 1.8}),
    dict(name='吸取巢', w={'siphoner': 2.4, 'spawner': 1.5}),
    dict(name='枪林', w={'spear': 2.6, 'laser': 1.6}),
    dict(name='雷区', w={'miner': 2.6, 'bomber': 1.5}),
    dict(name='巨影', w={'titan': 2.0, 'bulwark': 1.8}),
    dict(name='龙骑队', w={'drake': 2.6, 'spear': 1.6}),
    dict(name='迫击阵', w={'mortar': 2.6, 'turret': 1.5}),
    dict(name='幽影群', w={'shade': 2.6, 'orb': 1.4}),
    dict(name='光蛾群', w={'wisp': 2.6, 'orb': 1.4}),
    dict(name='破城队', w={'juggernaut': 1.8, 'titan': 1.5}),
    dict(name='织网阵', w={'webber': 2.6, 'weaver': 1.4}),
    dict(name='棱镜阵', w={'prism': 2.6, 'orb': 1.4}),
    dict(name='蜂巢群', w={'hive': 2.4, 'spark': 1.5}),
    dict(name='冲骑队', w={'lancer': 2.8, 'charger': 1.3}),
    dict(name='冰晶群', w={'cryo': 2.6, 'lantern': 1.4}),
    dict(name='炬火队', w={'torch': 2.6, 'bomber': 1.4}),
    dict(name='虚空群', w={'voidling': 2.8, 'shade': 1.2}),
    dict(name='狙击线', w={'sniper': 3.0, 'laser': 1.5}),
    dict(name='炸弹雨', w={'mortar': 2.8, 'bomber': 1.6}),
    dict(name='钩爪群', w={'hunter': 2.8, 'spear': 1.6}),
    dict(name='光矛阵', w={'spear': 2.4, 'lancer': 2.0}),
    dict(name='铁壁阵', w={'bulwark': 2.6, 'warden': 1.8}),
    dict(name='深潜群', w={'shade': 2.4, 'voidling': 1.6}),
]

SHIP_TIPS = {
    'echo': ('dmg', 'multi', 'hull'),
    'talon': ('rate', 'crit', 'spd'),
    'anvil': ('hull', 'thorns', 'regen'),
    'swarm': ('drone', 'multi', 'dmg'),
    'prism': ('pierce', 'dmg', 'bigshot'),
    'thorn': ('rate', 'multi', 'bspd'),
    'halo': ('hull', 'regen', 'luck'),
    'void': ('aura', 'frost', 'slow'),
    'pyre': ('burn', 'skillpow', 'dmg'),
    'frost': ('slow', 'aura', 'cdr'),
    'rift': ('pierce', 'bspd', 'dmg'),
    'bastion': ('hull', 'thorns', 'shieldg'),
    'tide': ('aura', 'slow', 'hull'),
    'star': ('homing', 'bspd', 'dmg'),
    'nova': ('dmg', 'crit', 'skillpow'),
    'lumen': ('burn', 'aura', 'skillpow'),
    'corona': ('burn', 'dmg', 'skillpow'),
    'refract': ('bspd', 'crit', 'pierce'),
    'vortex': ('aura', 'slow', 'cdr'),
    'forge': ('burn', 'dmg', 'drone'),
    'storm': ('chain', 'bspd', 'cdr'),
    'decoy': ('drone', 'rate', 'critdmg'),
    'titan': ('hull', 'thorns', 'dmg'),
    'oracle': ('slow', 'crit', 'critdmg'),
    'sepulcher': ('hull', 'thorns', 'shieldg'),
    'hivemind': ('drone', 'rate', 'multi'),
    'dawn': ('hull', 'regen', 'luck'),
    'breakwater': ('pierce', 'crit', 'bspd'),
}
MUT_PREVIEW = random.sample(MUTS, 3)

# ================================================================
#  全局状态
# ================================================================
class Run:
    def __init__(self, ship):
        self.ship = ship
        self.mode = G.mode
        self.mode_name = MODES[self.mode]['name']
        self.waves_per_layer = MODES[self.mode]['waves']
        self.layer_cap = MODES[self.mode]['layers']
        self.score_mult = MODES[self.mode]['score']
        self.cycle = 0
        self.layer = 1
        self.wave = 1
        self.mut = {}
        self.lmod = default_lmod()
        self.boss_off = 0
        self.seed = 0
        self.max_hp = ship['hp']
        self.hp = ship['hp']
        self.st = default_stats()
        self.st['dmg'] = ship['dmg']
        self.st['rate'] = 1.0
        self.st['pierce'] = ship['pierce']
        self.st['bullets'] = ship['bullets']
        self.identity = None
        self.start_shield = 0
        self.start_drone = 0
        self.fire_echo = 0.0
        self.shot_alt = 0
        self.augs = {}
        self.pacts = []
        self.kills = 0
        self.score = 0
        self.shards_earned = 0
        self.time = 0
        self.cards_taken = 0
        self.pickups = 0
        self.waves_cleared = 0

    def aug_count(self, aid):
        return self.augs.get(aid, 0)

    def take(self, a):
        aid, key, val = a[0], a[4], a[5]
        self.augs[aid] = self.augs.get(aid, 0) + 1
        self.cards_taken += 1
        if key == 'maxhp':
            self.max_hp += val
            self.hp = min(self.max_hp, self.hp + val)
        elif key == 'glass':
            self.st['dmg'] *= 1.45
            self.max_hp = max(2, self.max_hp - 1)
            self.hp = min(self.hp, self.max_hp)
        elif key in ('dmg', 'rate', 'speed', 'cd'):
            self.st[key] *= val
        elif key == 'lance':
            self.st['lance'] = self.st.get('lance', 0) + val
            self.st['rate'] *= .90
        else:
            self.st[key] = self.st.get(key, 0) + val
        if self.cards_taken >= 25:
            grant_ach('aug25')
        if self.cards_taken >= 40:
            grant_ach('aug40')
        if self.cards_taken >= 60:
            grant_ach('aug60')
        if self.cards_taken >= 80:
            grant_ach('aug80')
        if self.cards_taken >= 100:
            grant_ach('aug100')


class State:
    def __init__(self):
        self.scene = 'title'
        self.run = None
        self.player = None
        self.enemies = []
        self.pb = []
        self.eb = []
        self.parts = []
        self.drops = []
        self.drones = []
        self.boss = None
        self.queue = []
        self.wave_t = 0
        self.wave_active = False
        self.banner = None
        self.banner2 = None
        self.shake = 0
        self.time = 0
        self.slow_t = 0
        self.beams = []
        self.well = None
        self.cards = []
        self.card_ctx = 'wave'
        self.card_kind = 'aug'
        self.hover = -1
        self.next_id = 1
        self.mode_rects = []
        self.lab_rects = []
        self.slot_rects = []
        self.save_slot = -1
        self.profile = None
        self.slot_mode = 'load'
        self.confirm_slot = -1
        self.slot_sel = 0
        self.hub_back = None
        self.hub_confirm_new = False
        self.hub_confirm_del = False
        self.intro_page = 0
        self.intro_t = 0
        self.intro_after = 'title'
        self.intro_slot = None
        self.load_error = ''
        self.menu_sel = 0
        self.slot_back = None
        self.intro_skip = None
        self.quit_requested = False
        self.lab_sel = 0
        self.sel = 0
        self.ship_page = 0
        self.t = 0
        self.flashv = 0
        self.dead_t = 0
        self.win = False
        self.pointer = (W // 2, H // 2)
        self.pdown = False
        self.pdrag = False
        self.aim_mode = 'auto' if META.get('aim', 0) else 'mouse'
        self.cursor_visible = True
        self.menu_back = 'title'
        self.codex_tab = 0
        self.codex_page = 0
        self.joy = None
        self.joy_name = ''
        self.ctrl_aim = (0.0, -1.0)
        self.ctrl_t = 0.0
        self.set_rects = []
        self.codex_rects = []
        self.set_sel = 0
        self.shake_scale = 1.0 if META.get('shake', 1) else 0.0
        self.flash_scale = 1.0 if META.get('flash', 1) else 0.0
        self.held = set()
        self.combo = 0
        self.combo_t = 0
        self.combo_best = 0
        self.wave_tag = ''
        self.start_aug_name = ''
        self.diff = int(META.get('diff', 0))
        self.mode = int(META.get('mode', 0))
        self.ww, self.wh = world_of(1)
        self.camx = 0.0
        self.camy = 0.0
        self.cam_lock = None
        self.fires = []
        self.zone_amb = 'bubble'
        self.props = []
        self.caches = []
        self.cache_total = 3
        self.cache_taken = 0
        self.landmark = None
        self.landmark_seen = False
        self.fg_props = []
        self.layer_card_t = 0.0

G = State()

# ================================================================
#  粒子 / 提示
# ================================================================
def particle(x, y, n, col, spd=140, size=18, life=.5, spread=None, direction=0):
    if len(G.parts) > 700:
        return
    for _ in range(n):
        a = random.uniform(0, math.pi * 2) if spread is None else direction + random.uniform(-spread / 2, spread / 2)
        v = spd * random.uniform(.25, 1.15)
        lf = life * random.uniform(.6, 1.25)
        G.parts.append({'x': x, 'y': y, 'vx': math.cos(a) * v, 'vy': math.sin(a) * v,
                        'life': lf, 'max': lf, 'size': size * random.uniform(.45, 1.1), 'col': col})

def ring(x, y, r0, r1, col, life=.6, width=2):
    G.parts.append({'ring': True, 'x': x, 'y': y, 'r0': r0, 'r1': r1, 'r': r0,
                    'life': life, 'max': life, 'col': col, 'w': width})

def add_beam(x, y, col, life=.28, ang=None):
    G.beams.append({'x': x, 'y': y, 'life': life, 'max': life, 'col': col,
                    'ang': ang})

def toast(s, col='aqua', life=1.9):
    G.banner2 = {'s': s, 'col': col, 't': 0, 'life': life}


def grant_ach(aid):
    if aid in META.get('ach', []):
        return
    META.setdefault('ach', []).append(aid)
    save_meta()
    for i, nm, ds in ACHIEVEMENTS:
        if i == aid:
            toast('成就解锁 · %s（%s）' % (nm, ds), 'gold')
            if G.scene == 'play':
                AUD.play('big', .55)
            break

# ================================================================
#  玩家
# ================================================================
class Player:
    def __init__(self, ship, run):
        self.x = G.ww / 2
        self.y = G.wh - 170
        self.vx = 0
        self.vy = 0
        self.r = 11
        self.hp = run.hp
        self.max_hp = run.max_hp
        self.inv = 1.4
        self.shield = 0
        self.shield_t = 0
        self.fire_t = .2
        self.skill_t = 0
        self.roll = 0
        self.aim = 0.0
        self.dash_t = 0
        self.dash_dir = (0, -1)
        self.dash_hits = set()
        self.charge_t = 0
        self.charge_need = 0.85
        self.flash = 0
        self.thrust_t = 0
        self.shieldgen_t = 0
        self.warp_t = 0
        self.od_t = 0
        self.web_t = 0
        self.slow_t = 0
        self.frost_t = 0
        self.orb_t = 0
        self.orb_ang = 0
        self.regen_t = 0
        self.boomer_t = 0
        self.mine_t = 0
        self.blade_ang = 0
        self.blade_t = 0


def player_rect_collide(x, y, r):
    p = G.player
    if not p:
        return False
    return dist2((x, y), (p.x, p.y)) <= (r + p.r) ** 2

def key_held(sk, *keys):
    """同时接受 SDL 键盘状态和事件累积状态，避免输入法/焦点吞键导致按键失效。"""
    for k in keys:
        try:
            if sk[k]:
                return True
        except Exception:
            pass
        if k in G.held:
            return True
    return False


def update_player(dt):
    p = G.player
    if not p:
        return
    sk = pygame.key.get_pressed()
    ax = ay = 0
    if key_held(sk, pygame.K_a, pygame.K_LEFT):
        ax -= 1
    if key_held(sk, pygame.K_d, pygame.K_RIGHT):
        ax += 1
    if key_held(sk, pygame.K_w, pygame.K_UP):
        ay -= 1
    if key_held(sk, pygame.K_s, pygame.K_DOWN):
        ay += 1
    if G.joy:
        try:
            lx, ly = G.joy.get_axis(0), G.joy.get_axis(1)
            if math.hypot(lx, ly) > .18:
                ax += lx
                ay += ly
            rx, ry = G.joy.get_axis(2), G.joy.get_axis(3)
            if math.hypot(rx, ry) > .22:
                G.ctrl_aim = (rx, -ry)
                G.ctrl_t = .25
            elif G.ctrl_t > 0:
                G.ctrl_t -= dt
        except Exception:
            pass
    l = math.hypot(ax, ay)
    if l:
        ax /= l
        ay /= l
    focus = key_held(sk, pygame.K_LSHIFT, pygame.K_RSHIFT)
    speed = G.run.ship['speed'] * G.run.st['speed'] * G.run.lmod['speed'] * (0.5 if focus else 1.0)
    if p.web_t > 0:
        speed *= .55
    if p.slow_t > 0:
        p.slow_t -= dt
        speed *= .55

    # 标准肉鸽式转向：鼠标指哪，船头就朝哪；自动索敌模式跟随最近目标
    target_aim = None
    if G.joy and G.ctrl_t > 0:
        target_aim = aim_to(G.ctrl_aim[0], G.ctrl_aim[1])
    elif G.aim_mode == 'auto':
        target_aim = aim_target()
        if target_aim is None and (ax or ay):
            target_aim = aim_to(ax, ay)
    else:
        mwx, mwy = G.pointer[0] + G.camx, G.pointer[1] + G.camy
        dx, dy = mwx - p.x, mwy - p.y
        if dx * dx + dy * dy > 10 * 10:
            target_aim = aim_to(dx, dy)
    if target_aim is not None:
        delta = norm_aim(target_aim - p.aim)
        p.aim = norm_aim(p.aim + delta * min(1, dt * 16))

    if p.dash_t > 0:
        p.dash_t -= dt
        p.x += p.dash_dir[0] * 820 * dt
        p.y += p.dash_dir[1] * 820 * dt
        p.vx, p.vy = p.dash_dir[0] * 820, p.dash_dir[1] * 820
        p.inv = max(p.inv, .08)
        if random.random() < .5:
            particle(p.x, p.y, 2, 'amber', 90, 26, .35)
    else:
        p.x += ax * speed * dt
        p.y += ay * speed * dt
        p.vx, p.vy = ax * speed, ay * speed

    if G.boss:
        p.x = clamp(p.x, G.camx + 36, G.camx + W - 36)
        p.y = clamp(p.y, G.camy + 70, G.camy + H - 34)
    else:
        p.x = clamp(p.x, 22, G.ww - 22)
        p.y = clamp(p.y, 56, G.wh - 26)
    p.roll = lerp(p.roll, clamp(p.vx / 900, -.9, .9) * .3, min(1, dt * 9))

    # 相位跃迁：定期自动闪现
    st0 = G.run.st
    if st0['warp'] > 0:
        p.warp_t += dt
        if p.warp_t >= max(3.6, 7.0 - 1.6 * (st0['warp'] - 1)):
            p.warp_t = 0
            dx, dy = p.vx, p.vy
            if not (dx or dy):
                dx, dy = math.sin(p.aim), -math.cos(p.aim)
            dl = math.hypot(dx, dy) or 1
            ring(p.x, p.y, 10, 96, 'violet', .38, 2)
            particle(p.x, p.y, 8, 'violet', 120, 16, .3)
            p.x = clamp(p.x + dx / dl * 130, 22, G.ww - 22)
            p.y = clamp(p.y + dy / dl * 130, 56, G.wh - 26)
            p.inv = max(p.inv, .45)
            ring(p.x, p.y, 8, 74, 'white', .3, 2)
            AUD.play('skill', .3)

    # 缠网 / 霜环 / 环绕卫星 / 缠滞力场 / 纳米修复
    st = G.run.st
    if p.web_t > 0:
        p.web_t -= dt
    if st['aura'] > 0:
        arad = 118 + 24 * st['aura']
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < arad ** 2:
                e.slow = max(e.slow, .65)
    if st['regen'] > 0:
        p.regen_t += dt
        iv = max(12.0, 26.0 - 6.0 * (st['regen'] - 1))
        if p.regen_t >= iv:
            p.regen_t = 0
            if p.hp < G.run.max_hp:
                heal_player(1, quiet=True)
                ring(p.x, p.y, 5, 64, 'green', .4, 2)
                particle(p.x, p.y, 6, 'green', 70, 16, .45)
    if st['frost'] > 0:
        p.frost_t -= dt
        if p.frost_t <= 0:
            rad = 205 + 22 * st['frost']
            p.frost_t = max(3.4, 6.0 - .8 * (st['frost'] - 1))
            ring(p.x, p.y, 12, rad, 'aqua', .55, 3)
            for e in G.enemies:
                if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                    e.slow = max(e.slow, 1.5)
            AUD.play('skill', .35)
    if st['orbit'] > 0:
        p.orb_ang += dt * 2.1
        p.orb_t -= dt
        n = 2 * int(st['orbit'])
        if p.orb_t <= 0:
            p.orb_t = .25
            doomed = []
            for i in range(n):
                a = p.orb_ang + i * math.pi * 2 / n
                ox = p.x + math.cos(a) * 58
                oy = p.y + math.sin(a) * 58 * .92
                for e in G.enemies:
                    if e.dead:
                        continue
                    if dist2((e.x, e.y), (ox, oy)) < (e.r + 13) ** 2:
                        e.hp -= 1.7 * st['dmg']
                        e.flash = .08
                        if e.hp <= 0 and e not in doomed:
                            doomed.append(e)
                        particle(ox, oy, 1, 'gold', 60, 12, .2)
            for e in doomed:
                kill_enemy(e)

    if p.boomer_t > 0:
        p.boomer_t -= dt
    if p.mine_t > 0:
        p.mine_t -= dt
    if st['blade'] > 0:
        p.blade_ang += dt * 2.6
        p.blade_t -= dt
        if p.blade_t <= 0:
            p.blade_t = .27
            n = max(1, int(st['blade']))
            for i in range(n):
                a = p.blade_ang + i * math.pi * 2 / n
                bx = p.x + math.cos(a) * 76
                by = p.y + math.sin(a) * 76
                for e in G.enemies:
                    if not e.dead and dist2((e.x, e.y), (bx, by)) < (e.r + 11) ** 2:
                        damage_enemy(e, 1.1 * st['dmg'], bx, by, False)
                particle(bx, by, 1, 'steel', 55, 9, .18)

    if p.inv > 0:
        p.inv -= dt
    if p.skill_t > 0:
        p.skill_t = max(0, p.skill_t - dt)
    if p.od_t > 0:
        p.od_t = max(0, p.od_t - dt)
    if p.flash > 0:
        p.flash -= dt
    if p.shield_t > 0:
        p.shield_t -= dt
        if p.shield_t <= 0:
            p.shield = 0

    if G.run.st['shieldgen'] > 0:
        p.shieldgen_t -= dt
        if p.shieldgen_t <= 0:
            p.shieldgen_t = 10.0 / G.run.st['shieldgen']
            if p.shield < 3:
                p.shield += 1
                toast('护盾再生', 'aqua')
                AUD.play('pick', .6)

    # 尾流
    p.thrust_t -= dt
    if p.thrust_t <= 0:
        p.thrust_t = .05
        j = rnd(5, -5)
        bx, by = -math.sin(p.aim), math.cos(p.aim)
        px = p.x + bx * 18 + math.cos(p.aim) * j
        py = p.y + by * 18 + math.sin(p.aim) * j
        particle(px, py, 1, G.run.ship.get('col', 'aqua'), 46, 14, .5, spread=1.0,
                 direction=math.pi / 2 + p.aim)

    # 蓄力技能
    if p.charge_t > 0:
        p.charge_t -= dt
        if p.charge_t <= 0 and G.run.ship['id'] == 'prism':
            cast_beam()
        return

    # 自动开火
    p.fire_t -= dt
    if p.fire_t <= 0:
        do_fire()
        p.fire_t = max(.028, G.run.ship['rate'] / G.run.st['rate'] / G.run.lmod['rate'])

    # 技能
    joy_skill = False
    if G.joy:
        try:
            joy_skill = G.joy.get_button(0) or G.joy.get_axis(5) > .55
        except Exception:
            joy_skill = False
    if (sk[pygame.K_SPACE] or joy_skill) and p.skill_t <= 0 and p.dash_t <= 0:
        cast_skill()


def do_fire():
    p = G.player
    st = G.run.st
    ident = SHIP_IDENTITIES.get(G.run.ship.get('id'), {})
    pat = ident.get('pattern', 'echo')
    n = max(1, int(st['bullets'])) + int(st['spread']) + int(st['shot']) * 2
    base = st['dmg'] * G.run.lmod['dmg'] * (1.5 if p.od_t > 0 else 1.0)
    base *= max(.5, 1 - .14 * st['spread'] - .07 * st['shot'])
    if st['berserk'] > 0:
        miss = 1 - p.hp / max(1, G.run.max_hp)
        base *= 1 + min(.6, miss * .55 * st['berserk'])
    base *= 1 + .12 * st['bigshot']
    crit = st['crit']
    critm = 2.0 + .25 * st['critdmg']
    bspd = 1 + .15 * st['bspd'] + (.25 if st['lance'] > 0 else 0) + .18 * st['rail']
    br = 4 * (1 + .35 * st['bigshot'])
    pierce = int(st['pierce']) + 2 * int(st['lance']) + int(st['rail']) + (999 if st['pierce_all'] else 0)
    aim = p.aim
    sx, sy = math.sin(aim), -math.cos(aim)   # 船头方向向量
    rx, ry = math.cos(aim), math.sin(aim)    # 船头右侧向量
    px, py = p.x + sx * 14, p.y + sy * 14

    # ---- 专属弹道：不同船不再共用同一束直线弹 ----
    spread = .12
    lateral = 0.0
    speed_mul = 1.0
    radius_mul = 1.0
    dmg_mul = 1.0
    life = 1.7
    add_side = False
    add_rear = False
    radial = 0
    homing_boost = 0
    extra_pierce = 0
    if pat == 'twin':
        n = max(n, 2)
        spread = 0.0
        lateral = .16
    elif pat == 'heavy':
        spread = .045
        speed_mul = .84
        radius_mul = 1.45
        dmg_mul = 1.16
        life = 1.9
    elif pat == 'swarm':
        n += 1
        spread = .20
        dmg_mul = .74
        radius_mul = .72
        speed_mul = .95
        life = 1.35
    elif pat == 'lance':
        spread = .035
        speed_mul = 1.55
        radius_mul = .62
        dmg_mul = 1.10
        life = 1.95
    elif pat == 'spike':
        spread = .15
        add_side = True
        add_rear = True
    elif pat == 'wave':
        spread = .24
        speed_mul = .92
        dmg_mul = .92
        life = 1.5
    elif pat == 'orb':
        speed_mul = .70
        radius_mul = 1.32
        dmg_mul = 1.20
        homing_boost = 1
        life = 2.0
    elif pat == 'furnace':
        n += 2
        spread = .30
        speed_mul = .88
        radius_mul = .82
        dmg_mul = .80
        life = 1.05
    elif pat == 'blade':
        # 本体只出两道交叉月刃；三道大月刃留给技能，避免技能和普攻同形
        n = max(n, 2)
        spread = .10
        speed_mul = 1.10
        extra_pierce = 1
        life = 1.6
    elif pat == 'mirror':
        spread = .10
        add_rear = True
    elif pat == 'rail':
        speed_mul = 1.70
        radius_mul = .55
        dmg_mul = 1.08
        life = 2.0
        extra_pierce = 1
    elif pat == 'tomb':
        speed_mul = .86
        radius_mul = 1.50
        dmg_mul = 1.18
        extra_pierce = 1
        life = 1.9
    elif pat == 'web':
        n += 1
        spread = .16
        homing_boost = 1
        dmg_mul = .90
    elif pat == 'harp':
        n += 1
        spread = .10
        add_side = (G.run.shot_alt % 2 == 0)
        G.run.shot_alt += 1
    elif pat == 'sun':
        radial = 2
        spread = .12
        dmg_mul = .95
    elif pat == 'queen':
        n += 1
        spread = .16
        dmg_mul = .82
        radius_mul = .85
    base *= dmg_mul
    bspd *= speed_mul
    br *= radius_mul
    pierce += extra_pierce
    homing = st['homing'] + homing_boost

    def add_shot(x0, y0, angle, damage, radius, life2, pierce2, homing2, extra=None):
        G.pb.append({'x': x0, 'y': y0,
                     'vx': math.sin(angle) * 980 * bspd,
                     'vy': -math.cos(angle) * 980 * bspd,
                     'r': radius, 'dmg': damage,
                     'pierce': pierce2, 'hits': [], 'crit': False,
                     'homing': homing2, 'freeze': st['freeze'],
                     'burn': st['burn'], 'mirror': int(st['mirror']),
                     'rico': int(st['ricochet']), 'life': life2, **(extra or {})})

    for i in range(n):
        if lateral:
            lat = (i - (n - 1) / 2) * lateral
            a = aim
            ox, oy = px + rx * lat * 28, py + ry * lat * 28
        else:
            off = (i - (n - 1) / 2) * spread
            a = aim + off
            ox, oy = px + rx * off * 26, py + ry * off * 26
        is_crit = random.random() < crit
        dmg = base * (critm if is_crit else 1.0)
        add_shot(ox, oy, a, dmg, br, life, pierce, homing,
                 {'crit': is_crit, 'kind': 'blade'} if pat == 'blade' else {'crit': is_crit})

    if random.random() < st['double']:
        for i in range(n):
            off = (i - (n - 1) / 2) * .16
            a = aim + off
            add_shot(px + rx * off * 30, py + ry * off * 30, a, base * .85,
                     br * .85, 1.7, pierce, homing)

    # 侧刺 / 双刃 / 回响 / 环爆：让每一类船的弹幕形状不同
    if add_side:
        if pat == 'blade':
            for sgn in (-1, 1):
                a = aim + sgn * .55
                add_shot(p.x + rx * sgn * 17, p.y + ry * sgn * 17, a,
                         base * .74, br * .8, 1.15, pierce, homing)
        else:
            for sgn in (-1, 1):
                a = aim + sgn * math.pi / 2
                add_shot(p.x + rx * sgn * 18, p.y + ry * sgn * 18, a,
                         base * .56, br * .72, .95, max(0, pierce - 1), homing)
    if add_rear:
        add_shot(p.x - sx * 16, p.y - sy * 16, aim + math.pi,
                 base * (0.78 if pat == 'mirror' else 0.62), br * .78, 1.1,
                 max(0, pierce - 1), homing)
    if radial:
        for k in range(4):
            a = aim + k * math.pi / 2
            add_shot(px, py, a, base * .55, br * .72, 1.0, max(0, pierce - 1), homing)

    echo_chance = float(getattr(G.run, 'fire_echo', 0) or 0)
    if echo_chance and random.random() < echo_chance:
        for i in range(min(n, 3)):
            off = (i - (min(n, 3) - 1) / 2) * .18
            add_shot(px, py, aim + off + .12, base * .58, br * .8, 1.3,
                     pierce, homing)

    if st['boomer'] > 0 and p.boomer_t <= 0:
        p.boomer_t = max(1.5, 2.9 - .22 * (st['boomer'] - 1))
        G.pb.append({'x': px, 'y': py, 'vx': sx * 560, 'vy': sy * 560, 'r': 8,
                     'dmg': base * 1.35, 'pierce': 3, 'hits': [], 'crit': False,
                     'homing': 0, 'freeze': 0, 'burn': 0, 'mirror': 0, 'rico': 0,
                     'life': 2.3, 'boomer': True, 'bt': 0, 'child': True})
    if st['mine'] > 0 and p.mine_t <= 0:
        p.mine_t = max(2.2, 4.0 - .3 * (st['mine'] - 1))
        G.pb.append({'x': p.x - sx * 14, 'y': p.y - sy * 14,
                     'vx': -sx * 90, 'vy': -sy * 90, 'r': 7,
                     'dmg': base * 2.3, 'pierce': 0, 'hits': [], 'crit': False,
                     'homing': 0, 'freeze': 0, 'burn': 0, 'mirror': 0, 'rico': 0,
                     'life': 3.0, 'kind': 'pmine', 'child': True})
    AUD.play('shoot' if n == 1 else 'shoot2', .55)
    particle(px, py, 1, G.run.ship.get('col', 'amber'), 40, 15, .16)


def update_pb(dt):
    p = G.player
    for b in G.pb:
        if b.get('kind') == 'pmine':
            b['life'] -= dt
            boom = b['life'] <= 0
            for e in G.enemies:
                if not e.dead and dist2((b['x'], b['y']), (e.x, e.y)) < 105 ** 2:
                    boom = True
                    break
            bo = G.boss
            if bo and not bo.dying and dist2((b['x'], b['y']), (bo.x, bo.y + 6)) < (95 + bo.r) ** 2:
                boom = True
            if boom:
                rad = 118
                for e in G.enemies:
                    if not e.dead and dist2((e.x, e.y), (b['x'], b['y'])) < rad ** 2:
                        damage_enemy(e, b['dmg'], b['x'], b['y'], False)
                if bo and not bo.dying and dist2((b['x'], b['y']), (bo.x, bo.y + 6)) < (rad + bo.r) ** 2:
                    hit_boss(b['dmg'], b['x'], b['y'], False)
                ring(b['x'], b['y'], 10, rad, 'amber', .45, 3)
                particle(b['x'], b['y'], 12, 'amber', 160, 22, .4)
                G.shake = max(G.shake, 6)
                b['life'] = 0
            continue
        b['x'] += b['vx'] * dt
        b['y'] += b['vy'] * dt
        b['life'] -= dt
        if b.get('boomer'):
            b['bt'] = b.get('bt', 0) + dt
            if b['bt'] > .55:
                dx, dy = p.x - b['x'], p.y - b['y']
                dl = max(1, math.hypot(dx, dy))
                b['vx'] = lerp(b['vx'], dx / dl * 720, min(1, dt * 9))
                b['vy'] = lerp(b['vy'], dy / dl * 720, min(1, dt * 9))
        if b['homing'] > 0:
            tgt = None
            best = 1e9
            for e in G.enemies:
                if e.dead:
                    continue
                d = dist2((b['x'], b['y']), (e.x, e.y))
                if d < best:
                    best = d
                    tgt = e
            if tgt and best < 420 ** 2:
                dx, dy = tgt.x - b['x'], tgt.y - b['y']
                dl = max(1, math.hypot(dx, dy))
                turn = .07 * b['homing'] * dt * 60
                b['vx'] = lerp(b['vx'], dx / dl * 900, min(1, turn))
                b['vy'] = lerp(b['vy'], dy / dl * 900, min(1, turn))

    for b in G.pb:
        if b.get('kind') == 'pmine':
            continue
        if (b['life'] <= 0 or b['y'] < -50 or b['x'] < -50
                or b['x'] > G.ww + 50 or b['y'] > G.wh + 50):
            continue
        for e in G.enemies:
            if e.dead:
                continue
            if dist2((b['x'], b['y']), (e.x, e.y)) > (b['r'] + e.r) ** 2:
                continue
            if e.id in b['hits']:
                continue
            b['hits'].append(e.id)
            damage_enemy(e, b['dmg'], b['x'], b['y'], b['crit'])
            if b.get('burn') and not e.dead:
                e.burn = max(e.burn, 1.5 * b['burn'])
                e.burn_t = max(e.burn_t, 2.0)
            if b.get('mirror') and not b.get('child') and len(G.pb) < 220:
                aa = math.atan2(b['vy'], b['vx'])
                for sgn in (-1, 1):
                    na = aa + sgn * .55
                    G.pb.append({'x': b['x'], 'y': b['y'],
                                 'vx': math.cos(na) * 860, 'vy': math.sin(na) * 860,
                                 'r': 3, 'dmg': b['dmg'] * .55, 'pierce': 0,
                                 'hits': [e.id], 'crit': False, 'homing': 0, 'freeze': 0,
                                 'burn': 0, 'mirror': 0, 'rico': 0, 'life': .9,
                                 'child': True})
            if b['freeze']:
                e.slow = .9
            if b['rico'] > 0:
                b['rico'] -= 1
                b['hits'] = []
                b['vx'] *= -1
                b['vy'] *= -1
                b['y'] += b['vy'] * .02
            elif b['pierce'] > 0:
                b['pierce'] -= 1
            else:
                b['life'] = 0
            break

        bo = G.boss
        if b['life'] > 0 and bo and not bo.dying:
            if dist2((b['x'], b['y']), (bo.x, bo.y + 6)) <= (b['r'] + bo.r * .92) ** 2:
                if 'boss' not in b['hits']:
                    b['hits'].append('boss')
                    hit_boss(b['dmg'], b['x'], b['y'], b['crit'])
                    if b['pierce'] > 0:
                        b['pierce'] -= 1
                    else:
                        b['life'] = 0

    G.pb = [b for b in G.pb if b['life'] > 0]


def cast_skill():
    p = G.player
    sk = G.run.ship
    st = G.run.st
    sp = 1 + .25 * st['skillpow']
    p.skill_t = sk['cd'] * st['cd']
    AUD.play('skill', .8)
    sid = sk.get('skill_key', sk['id'])
    if sid == 'echo':
        G.eb.clear()
        for e in G.enemies:
            if not e.dead:
                damage_enemy(e, 9 * st['dmg'] * sp, e.x, e.y, False)
        if G.boss and not G.boss.dying:
            hit_boss(16 * st['dmg'] * sp, G.boss.x, G.boss.y, False)
        ring(p.x, p.y, 16, 900, 'white', .9, 3)
        ring(p.x, p.y, 10, 620, 'aqua', 1.1, 6)
        G.shake = max(G.shake, 14)
        G.flashv = .5
    elif sid == 'talon':
        p.dash_dir = ((p.vx / 900, p.vy / 900) if math.hypot(p.vx, p.vy) > 60
                      else (math.sin(p.aim), -math.cos(p.aim)))
        p.dash_t = .42
        p.dash_hits = set()
        p.inv = max(p.inv, .55)
        ring(p.x, p.y, 8, 90, 'amber', .4, 2)
    elif sid == 'anvil':
        p.shield = 3
        p.shield_t = 7.0
        ring(p.x, p.y, 12, 130, 'coral', .6, 3)
    elif sid == 'swarm':
        for i in range(2):
            spawn_drone(i)
        ring(p.x, p.y, 10, 120, 'violet', .6, 2)
    elif sid == 'prism':
        p.charge_t = p.charge_need
    elif sid == 'thorn':
        n = 16
        base = 2.4 * G.run.st['dmg'] * (1 + .25 * G.run.st['skillpow'])
        for k in range(n):
            a = k * math.pi * 2 / n + G.t * .3
            G.pb.append({'x': p.x + math.cos(a) * 14, 'y': p.y + math.sin(a) * 14,
                         'vx': math.cos(a) * 720, 'vy': math.sin(a) * 720, 'r': 5,
                         'dmg': base, 'pierce': 2, 'hits': [], 'crit': False,
                         'homing': 0, 'freeze': 0, 'burn': 0, 'mirror': 0, 'rico': 0,
                         'life': 1.2, 'child': True})
        ring(p.x, p.y, 8, 150, 'steel', .5, 3)
        G.shake = max(G.shake, 8)
    elif sid == 'halo':
        heal_player(2, quiet=True)
        rad = 330
        G.eb = [b for b in G.eb if dist2((b['x'], b['y']), (p.x, p.y)) > rad * rad]
        p.inv = max(p.inv, 1.5)
        ring(p.x, p.y, 12, rad, 'gold', .9, 4)
        ring(p.x, p.y, 8, 180, 'white', .6, 2)
        G.flashv = max(G.flashv, .28)
    elif sid == 'void':
        wx = p.x + math.sin(p.aim) * 300
        wy = p.y - math.cos(p.aim) * 300
        G.well = {'x': clamp(wx, 120, G.ww - 120), 'y': clamp(wy, 120, G.wh - 120),
                  't': 3.2, 'max': 3.2, 'r': 190, 'acc': 0, 'ang': 0}
    elif sid == 'pyre':
        n = 20
        base = 2.2 * st['dmg'] * sp
        for k in range(n):
            a = k * math.pi * 2 / n + G.t * .25
            G.pb.append({'x': p.x + math.cos(a) * 14, 'y': p.y + math.sin(a) * 14,
                         'vx': math.cos(a) * 540, 'vy': math.sin(a) * 540, 'r': 6,
                         'dmg': base, 'pierce': 1, 'hits': [], 'crit': False,
                         'homing': 0, 'freeze': 0, 'burn': 5, 'mirror': 0, 'rico': 0,
                         'life': 1.3, 'child': True})
        G.fires.append({'x': p.x, 'y': p.y, 'r': 130, 't': 2.4, 'max': 2.4})
        ring(p.x, p.y, 10, 190, 'amber', .55, 3)
    elif sid == 'frost':
        rad = 290
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                e.slow = max(e.slow, 3.2)
                e.fire_t = max(e.fire_t, 1.2)
                damage_enemy(e, 3.2 * st['dmg'] * sp, e.x, e.y, False)
        G.eb = [b for b in G.eb if dist2((b['x'], b['y']), (p.x, p.y)) > (rad * .85) ** 2]
        ring(p.x, p.y, 10, rad, 'steel', .75, 3)
        ring(p.x, p.y, 16, rad * .55, 'white', .45, 2)
    elif sid == 'rift':
        base = 4.8 * st['dmg'] * sp
        aim = p.aim
        nx, ny = math.sin(aim), -math.cos(aim)
        rx, ry = math.cos(aim), math.sin(aim)
        variant = sk['id']

        def rift_blade(ox, oy, a, dmg, rad, spd, pierce2, life2, extra=None):
            G.pb.append({'x': p.x + ox, 'y': p.y + oy,
                         'vx': math.sin(a) * spd, 'vy': -math.cos(a) * spd,
                         'r': rad, 'dmg': dmg, 'pierce': pierce2, 'hits': [],
                         'crit': False, 'homing': 0, 'freeze': 0, 'burn': 0,
                         'mirror': 0, 'rico': 0, 'life': life2, 'kind': 'blade',
                         **(extra or {})})

        if variant == 'lark':
            # 云雀：两柄细刃 + 短冲刺，强调“突袭”而不是复制普攻
            for k in (-1, 1):
                a = aim + k * .14
                rift_blade(nx * 12 + rx * k * 18, ny * 12 + ry * k * 18,
                           a, base * .88, 8, 1220, 4, 1.05)
            p.dash_dir = ((p.vx / 900, p.vy / 900) if math.hypot(p.vx, p.vy) > 60
                          else (math.sin(aim), -math.cos(aim)))
            p.dash_t = .24
            p.dash_hits = set()
            p.inv = max(p.inv, .32)
            ring(p.x, p.y, 8, 110, sk.get('col', 'green'), .35, 2)
        elif variant == 'glaive':
            # 环刃：两柄回旋刃，飞出去再折回，和直线三连区别开
            for k in (-1, 1):
                a = aim + k * .55
                rift_blade(nx * 14 + rx * k * 16, ny * 14 + ry * k * 16,
                           a, base * 1.08, 11, 900, 5, 2.0,
                           {'boomer': True, 'bt': 0})
            ring(p.x, p.y, 10, 165, sk.get('col', 'green'), .5, 3)
        elif variant == 'breakwater':
            # 断潮：三道宽体重月刃，慢一点、宽一点，压出潮墙
            for k in (-1, 0, 1):
                a = aim + k * .22
                rift_blade(nx * 10 + rx * k * 20, ny * 10 + ry * k * 20,
                           a, base * 1.12, 15, 840, 6, 1.55)
            ring(p.x, p.y, 12, 175, sk.get('col', 'green'), .55, 4)
            G.shake = max(G.shake, 9)
        else:
            # 裂空：三道大型月刃，扇面比普攻更宽，刃体更大
            for k in (-1, 0, 1):
                a = aim + k * .16
                rift_blade(nx * 10 + rx * k * 17, ny * 10 + ry * k * 17,
                           a, base * 1.10, 13, 1040, 6, 1.3)
            ring(p.x, p.y, 8, 150, sk.get('col', 'green'), .5, 3)
        G.shake = max(G.shake, 7)
    elif sid == 'bastion':
        p.shield = min(3, p.shield + 3)
        p.shield_t = max(p.shield_t, 9.0)
        rad = 280
        G.eb = [b for b in G.eb if dist2((b['x'], b['y']), (p.x, p.y)) > rad ** 2]
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                damage_enemy(e, 5.2 * st['dmg'] * sp, e.x, e.y, False)
        ring(p.x, p.y, 12, rad, 'steel', .65, 4)
        ring(p.x, p.y, 8, rad * .5, 'amber', .4, 2)
    elif sid == 'tide':
        rad = 360
        for e in G.enemies:
            if e.dead:
                continue
            dx, dy = e.x - p.x, e.y - p.y
            d = max(1, math.hypot(dx, dy))
            if d < rad:
                e.x = clamp(e.x + dx / d * 130, 24, G.ww - 24)
                e.y = clamp(e.y + dy / d * 100, 30, G.wh - 30)
                e.slow = max(e.slow, 2.8)
                damage_enemy(e, 4.0 * st['dmg'] * sp, e.x, e.y, False)
        for k in range(3):
            ring(p.x, p.y, 16 + k * 26, rad - k * 26, 'aqua', .6 + k * .12, 3)
        G.shake = max(G.shake, 4)
    elif sid == 'star':
        for i in range(24):
            a = i / 24 * math.pi * 2 + random.uniform(-.08, .08)
            G.pb.append({'x': p.x, 'y': p.y - 14,
                         'vx': math.cos(a) * 330, 'vy': math.sin(a) * 330, 'r': 5,
                         'dmg': 2.2 * st['dmg'] * sp, 'pierce': 0, 'hits': [], 'crit': False,
                         'homing': 3, 'freeze': 0, 'burn': 0, 'mirror': 0, 'rico': 0,
                         'life': 1.7, 'child': True})
        ring(p.x, p.y, 12, 170, 'gold', .55, 3)
        ring(p.x, p.y, 160, 30, 'amber', .3, 2)
    elif sid == 'nova':
        rad = 620
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                e.slow = max(e.slow, 1.8)
                damage_enemy(e, 22.0 * st['dmg'] * sp, e.x, e.y, False)
        G.eb = [b for b in G.eb if dist2((b['x'], b['y']), (p.x, p.y)) > 520 ** 2]
        for k in range(4):
            ring(p.x, p.y, 18 + k * 40, rad - k * 90, 'coral', .75 + k * .1, 3)
        ring(p.x, p.y, 10, 220, 'white', .45, 3)
        G.flashv = max(G.flashv, .65)
        G.shake = max(G.shake, 15)
    elif sid == 'lumen':
        rad = 300
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                e.slow = max(e.slow, 3.0)
                damage_enemy(e, 4.5 * st['dmg'] * sp, e.x, e.y, False)
        G.fires.append({'x': p.x, 'y': p.y, 'r': 300, 't': 5.5, 'max': 5.5})
        ring(p.x, p.y, 14, rad, 'gold', .7, 3)
        ring(p.x, p.y, 8, 160, 'amber', .5, 2)
    elif sid == 'corona':
        rad = 330
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                e.burn_t = max(e.burn_t, 2.0)
                damage_enemy(e, 7.5 * st['dmg'] * sp, e.x, e.y, False)
        for dx, dy in ((0, 0), (-180, 0), (180, 0)):
            G.fires.append({'x': p.x + dx, 'y': p.y + dy, 'r': 150, 't': 4.0, 'max': 4.0})
        for k in range(3):
            ring(p.x, p.y, 10 + k * 24, rad - k * 40, 'amber', .55 + k * .1, 3)
    elif sid == 'refract':
        for i in range(12):
            a = i / 12 * math.pi * 2 + random.uniform(-.06, .06)
            G.pb.append({'x': p.x, 'y': p.y - 14,
                         'vx': math.cos(a) * 500, 'vy': math.sin(a) * 500, 'r': 5,
                         'dmg': 2.2 * st['dmg'] * sp, 'pierce': 0, 'hits': [], 'crit': False,
                         'homing': 0, 'freeze': 0, 'burn': 0, 'mirror': 0, 'rico': 4,
                         'life': 1.6, 'child': True})
        ring(p.x, p.y, 12, 190, 'aqua', .55, 3)
        ring(p.x, p.y, 170, 40, 'white', .25, 2)
    elif sid == 'vortex':
        tx = clamp(p.x + math.sin(p.aim) * 300, 120, G.ww - 120)
        ty = clamp(p.y - math.cos(p.aim) * 300, 120, G.wh - 120)
        if G.boss and not G.boss.dying:
            tx, ty = G.boss.x, G.boss.y + 50
        else:
            best = 1e18
            for e in G.enemies:
                if e.dead:
                    continue
                d = dist2((e.x, e.y), (p.x, p.y))
                if d < best:
                    best = d
                    tx, ty = e.x, e.y
        G.well = {'x': tx, 'y': ty, 't': 3.6, 'max': 3.6, 'r': 220,
                  'acc': 0, 'ang': 0}
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (tx, ty)) < 220 ** 2:
                damage_enemy(e, 5.0 * st['dmg'] * sp, e.x, e.y, False)
        ring(tx, ty, 12, 260, 'violet', .6, 3)
    elif sid == 'forge':
        for k in range(2):
            spawn_drone(len(G.drones), True)
        G.fires.append({'x': p.x, 'y': p.y, 'r': 155, 't': 5.0, 'max': 5.0})
        ring(p.x, p.y, 10, 210, 'amber', .55, 3)
    elif sid == 'storm':
        targets = sorted([e for e in G.enemies if not e.dead],
                         key=lambda e: dist2((e.x, e.y), (p.x, p.y)))[:8]
        last = (p.x, p.y)
        for e in targets:
            add_beam(e.x, e.y, 'aqua', .3)
            damage_enemy(e, 4.2 * st['dmg'] * sp, e.x, e.y, False)
            ring(e.x, e.y, 6, 46, 'aqua', .25, 1)
            last = (e.x, e.y)
        if G.boss and not G.boss.dying:
            add_beam(G.boss.x, G.boss.y, 'aqua', .35)
            hit_boss(10 * st['dmg'] * sp, G.boss.x, G.boss.y, False)
        G.shake = max(G.shake, 7)
    elif sid == 'decoy':
        for k in range(3):
            spawn_drone(len(G.drones))
        p.shield = min(3, p.shield + 1)
        p.shield_t = max(p.shield_t, 10)
        ring(p.x, p.y, 8, 150, 'violet', .5, 2)
    elif sid == 'titan':
        p.inv = max(p.inv, 3.0)
        rad = 210
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                damage_enemy(e, 9.0 * st['dmg'] * sp, e.x, e.y, False)
        ring(p.x, p.y, 12, rad, 'steel', .7, 4)
        G.shake = max(G.shake, 18)
    elif sid == 'oracle':
        G.slow_t = max(G.slow_t, 3.6)
        for e in G.enemies:
            if not e.dead:
                e.flash = max(e.flash, .3)
                if dist2((e.x, e.y), (p.x, p.y)) < 900 ** 2:
                    damage_enemy(e, 2.2 * st['dmg'] * sp, e.x, e.y, False)
        if G.boss and not G.boss.dying:
            hit_boss(6 * st['dmg'] * sp, G.boss.x, G.boss.y, False)
        ring(p.x, p.y, 14, 760, 'white', .8, 3)
    if G.run.st['nova'] > 0 and sid != 'prism':
        rad = 130 + 45 * st['nova']
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                damage_enemy(e, 5.5 * st['dmg'] * st['nova'] * sp, e.x, e.y, False)
        ring(p.x, p.y, 14, rad, 'green', .55, 3)


def cast_beam():
    p = G.player
    st = G.run.st
    dmg = 26 * st['dmg'] * (1 + .25 * st['skillpow'])
    aim = p.aim
    dx, dy = math.sin(aim), -math.cos(aim)
    nx, ny = math.cos(aim), math.sin(aim)
    ox, oy = p.x + dx * 16, p.y + dy * 16
    for e in G.enemies:
        if e.dead:
            continue
        ex, ey = e.x - ox, e.y - oy
        t = ex * dx + ey * dy
        perp = abs(ex * nx + ey * ny)
        if 0 < t < 940 and perp < 34 + e.r:
            damage_enemy(e, dmg, e.x, e.y, False)
    if G.boss and not G.boss.dying:
        ex, ey = G.boss.x - ox, G.boss.y + 6 - oy
        t = ex * dx + ey * dy
        perp = abs(ex * nx + ey * ny)
        if 0 < t < 980 and perp < 34 + G.boss.r:
            hit_boss(dmg * .8, G.boss.x, G.boss.y, False)
    add_beam(ox, oy, 'green', .32, aim)
    G.shake = max(G.shake, 10)
    AUD.play('big', .5)
    if st['nova'] > 0:
        cx, cy = p.x + dx * 300, p.y + dy * 300
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (cx, cy)) < 260 ** 2:
                damage_enemy(e, 6 * st['dmg'] * st['nova'], e.x, e.y, False)
        ring(cx, cy, 10, 280, 'green', .6, 3)


# ================================================================
#  无人机
# ================================================================
def spawn_drone(i, perma=False):
    G.drones.append({'a': i * math.pi * 2 / 3, 'life': 1e9 if perma else 12.0,
                     'fire': .5, 'x': G.player.x, 'y': G.player.y, 'perma': perma})


def update_drones(dt):
    p = G.player
    if not p:
        return
    for d in G.drones:
        d['life'] -= dt
        d['a'] += dt * 2.1
        R = 48
        d['x'] = p.x + math.cos(d['a']) * R
        d['y'] = p.y + math.sin(d['a']) * R * .55
        d['fire'] -= dt
        if d['fire'] <= 0 and G.run:
            d['fire'] = .22 / G.run.st['rate']
            tgt = None
            bestd = 1e9
            for e in G.enemies:
                if not e.dead and e.y < p.y:
                    dd = dist2((d['x'], d['y']), (e.x, e.y))
                    if dd < bestd:
                        bestd = dd
                        tgt = e
            ang = -math.pi / 2
            if tgt:
                ang = math.atan2(tgt.y - d['y'], tgt.x - d['x'])
            G.pb.append({'x': d['x'], 'y': d['y'], 'vx': math.cos(ang) * 760,
                         'vy': math.sin(ang) * 760, 'r': 3, 'dmg': .5 * G.run.st['dmg'],
                         'pierce': 0, 'hits': [], 'crit': False, 'homing': 0,
                         'freeze': 0, 'rico': 0, 'life': 1.6, 'drone': True})
            particle(d['x'], d['y'], 1, 'violet', 30, 12, .2)
    G.drones = [d for d in G.drones if d['life'] > 0]

# -*- coding: utf-8 -*-
# ================================================================
#  敌机
# ================================================================
EKIND = {
    'drifter': dict(hp=3.2, r=16, score=60, col='aqua'),
    'lantern': dict(hp=6.8, r=21, score=110, col='green'),
    'hunter': dict(hp=4.4, r=14, score=80, col='coral'),
    'turret': dict(hp=11, r=24, score=150, col='violet'),
    'spark': dict(hp=1.4, r=9, score=30, col='amber'),
    'marc': dict(hp=15, r=21, score=150, col='coral'),
    'splitter': dict(hp=5.5, r=18, score=95, col='coral'),
    'orbiter': dict(hp=5.0, r=13, score=105, col='amber'),
    'charger': dict(hp=7.2, r=16, score=130, col='violet'),
    'weaver': dict(hp=6.0, r=19, score=115, col='green'),
    'bulwark': dict(hp=14, r=22, score=175, col='steel', cr=.9),
    'spinner': dict(hp=6.0, r=17, score=125, col='violet', cr=1.55),
    'bomber': dict(hp=3.6, r=14, score=100, col='coral', cr=.95),
    'sniper': dict(hp=5.0, r=14, score=145, col='aqua', cr=.7),
    'dart': dict(hp=2.6, r=12, score=70, col='amber', cr=1.0),
    'spawner': dict(hp=16, r=26, score=220, col='violet', cr=1.2),
    'laser': dict(hp=7.0, r=15, score=140, col='coral', cr=.8),
    'orb': dict(hp=4.2, r=13, score=90, col='white', cr=.85),
    'sweeper': dict(hp=10, r=18, score=190, col='coral', cr=.8),
    'warden': dict(hp=13, r=20, score=180, col='steel', cr=.9),
    'siphoner': dict(hp=9, r=17, score=170, col='violet', cr=.85),
    'spear': dict(hp=8, r=16, score=165, col='green', cr=.85),
    'miner': dict(hp=10, r=18, score=190, col='amber', cr=.8),
    'titan': dict(hp=42, r=34, score=520, col='steel', cr=.9),
    'drake': dict(hp=12, r=20, score=220, col='coral', cr=.9),
    'mortar': dict(hp=14, r=24, score=240, col='steel', cr=.85),
    'shade': dict(hp=9, r=16, score=210, col='violet', cr=.85),
    'wisp': dict(hp=6.4, r=12, score=150, col='white', cr=.62),
    'juggernaut': dict(hp=32, r=30, score=480, col='coral', cr=.9),
    'webber': dict(hp=12, r=18, score=230, col='green', cr=.8),
    'prism': dict(hp=10, r=16, score=215, col='aqua', cr=.95),
    'hive': dict(hp=18, r=24, score=280, col='amber', cr=.8),
    'lancer': dict(hp=9, r=15, score=205, col='coral', cr=1.3),
    'cryo': dict(hp=12, r=18, score=220, col='aqua', cr=.8),
    'torch': dict(hp=14, r=20, score=240, col='amber', cr=.85),
    'voidling': dict(hp=7, r=14, score=185, col='violet', cr=.9),
}

# 悬停高度（相对镜头顶部，世界坐标里按出场时的镜头算一次）
HOVER = {'turret': 110, 'marc': 100, 'weaver': 124, 'bulwark': 300,
         'spinner': 268, 'sniper': 112, 'laser': 120, 'spawner': 190,
         'sweeper': 120, 'warden': 135, 'siphoner': 125,
         'spear': 112, 'miner': 138, 'titan': 92,
         'drake': 116, 'mortar': 132, 'shade': 118,
         'wisp': 120, 'juggernaut': 86, 'webber': 118,
         'prism': 116, 'hive': 118, 'lancer': 104, 'cryo': 120, 'torch': 112, 'voidling': 116}


class Enemy:
    def __init__(self, kind, x, y, layer, wave, scale_hp=True, elite=False):
        d = EKIND[kind]
        self.id = G.next_id
        G.next_id += 1
        self.kind = kind
        self.x = x
        self.y = y
        self.bx = x
        self.t = 0
        self.ph = rnd(6.28)
        self.r = d['r']
        sc = 1.0 if not scale_hp else (1 + (layer - 1) * .46 + (wave - 1) * .1)
        sc *= (G.run.mut.get('ehp', 1.0) if G.run else 1.0)
        sc *= DIFFS[G.diff]['ehp'] * mode_of().get('ehp', 1.0) * threat_of(layer)
        self.maxhp = d['hp'] * sc
        self.hp = self.maxhp
        self.score = d['score']
        self.fire_t = rnd(3.4, 1.5)
        self.flash = 0
        self.dead = False
        self.slow = 0
        self.state = 0
        self.ang = 0
        self.elite = elite
        self.burn = 0
        self.burn_t = 0
        self.burn_acc = 0
        self.ct = 0
        self.spawn_t = .4
        self.spd_k = (1 + (layer - 1) * .07) * threat_of(layer)
        self.ay = G.camy + HOVER.get(kind, 110)
        self.beam_t = 0
        self.beam_life = 0
        if elite:
            self.maxhp *= 2.6
            self.hp = self.maxhp
            self.r *= 1.22
            self.score = int(self.score * 2.4)
            self.spawn_t = .5


def eb_shot(x, y, ang, spd, r, col, kind='orb'):
    if len(G.eb) > 460:
        return
    if G.boss and len(G.eb) > 300:
        return
    spd *= DIFFS[G.diff]['espd'] * G.run.lmod['espd']
    if G.run and G.run.mut.get('espd'):
        spd *= G.run.mut['espd']
    if getattr(G, 'boss', None) and not G.boss.dying:
        # BOSS 战内所有敌弹随层数线性加速
        spd *= G.boss.spd_scale
    G.eb.append({'x': x, 'y': y, 'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd,
                 'r': r, 'col': col, 't': 0, 'life': 6.5, 'kind': kind})


def update_enemies(dt):
    p = G.player
    slow = .45 if G.slow_t > 0 else 1.0
    for e in G.enemies:
        if e.dead:
            continue
        e.t += dt
        if e.spawn_t > 0:
            e.spawn_t -= dt
            continue
        if e.burn_t > 0:
            e.burn_t -= dt
            e.burn_acc += dt
            if e.burn_acc >= .3:
                e.burn_acc -= .3
                e.hp -= e.burn * .3
                if e.hp <= 0:
                    kill_enemy(e)
                    continue
                if random.random() < .4:
                    particle(e.x + rnd(10, -10), e.y + rnd(10, -10), 1, 'amber', 60, 12, .3)
        if e.flash > 0:
            e.flash -= dt
        if e.slow > 0:
            e.slow -= dt
        k = slow * (.55 if e.slow > 0 else 1.0) * e.spd_k
        if e.kind == 'drifter':
            e.y += 68 * dt * k
            e.x = e.bx + math.sin(e.t * 1.5 + e.ph) * 42
            e.fire_t -= dt
            if e.fire_t <= 0 and G.camy + 40 < e.y < G.camy + H * .82:
                e.fire_t = 2.5 / max(1, e.spd_k)
                ang = math.atan2(p.y - e.y, p.x - e.x)
                eb_shot(e.x, e.y + 12, ang, 232, 6, 'coral')
        elif e.kind == 'lantern':
            e.y += 40 * dt * k
            e.x = e.bx + math.sin(e.t * .8 + e.ph) * 30
            e.fire_t -= dt
            if e.fire_t <= 0 and e.y > 30:
                e.fire_t = 3.1
                ang = math.atan2(p.y - e.y, p.x - e.x)
                for j in (-1, 0, 1):
                    eb_shot(e.x, e.y, ang + j * .26, 188, 7, 'green')
        elif e.kind == 'hunter':
            if e.state == 0:
                e.y += 58 * dt * k
                e.x = e.bx + math.sin(e.t * 1.2 + e.ph) * 20
                if e.t > .82:
                    e.state = 1
                    e.ang = math.atan2(p.y - e.y, p.x - e.x)
            else:
                want = math.atan2(p.y - e.y, p.x - e.x)
                d = want - e.ang
                while d > math.pi:
                    d -= math.pi * 2
                while d < -math.pi:
                    d += math.pi * 2
                e.ang += clamp(d, -2.4 * dt, 2.4 * dt)
                v = 296 * k
                e.x += math.cos(e.ang) * v * dt
                e.y += math.sin(e.ang) * v * dt
        elif e.kind == 'turret':
            e.y = lerp(e.y, e.ay, dt * 2.2)
            e.x = e.bx + math.sin(e.t * .55 + e.ph) * 56
            e.ang += dt * 1.8
            e.fire_t -= dt
            if e.t > 1.1 and e.fire_t <= 0:
                e.fire_t = .18
                e.state += 1
                for j in (0, 1):
                    a = e.ang + j * math.pi
                    eb_shot(e.x + math.cos(a) * 16, e.y + math.sin(a) * 16, a, 208, 6, 'violet')
                if e.state % 30 == 0:
                    e.fire_t = 2.0
        elif e.kind == 'spark':
            a = math.atan2(p.y - e.y, p.x - e.x)
            e.x += math.cos(a) * 132 * dt * k
            e.y += math.sin(a) * 132 * dt * k
        elif e.kind == 'marc':
            e.y = lerp(e.y, e.ay, dt * 1.7)
            e.x = e.bx + math.sin(e.t * .5 + e.ph) * 44
            e.fire_t -= dt
            if e.fire_t <= 0 and e.t > 1.3:
                e.fire_t = 1.5
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in range(-2, 3):
                    eb_shot(e.x, e.y + 14, a + j * .17, 198, 7, 'coral')
        elif e.kind == 'splitter':
            e.y += 56 * dt * k
            e.x = e.bx + math.sin(e.t * 1.15 + e.ph) * 38
            e.fire_t -= dt
            if e.fire_t <= 0 and e.t > .9 and G.camy + 40 < e.y < G.camy + H * .78:
                e.fire_t = 2.9
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in (-1, 0, 1):
                    eb_shot(e.x, e.y + 10, a + j * .3, 196, 6, 'coral')
        elif e.kind == 'orbiter':
            a = e.t * 1.55 + e.ph
            rad = 158 + math.sin(e.t * .7) * 32
            e.x = p.x + math.cos(a) * rad
            e.y = p.y + math.sin(a) * rad * .72
            e.fire_t -= dt
            if e.fire_t <= 0:
                e.fire_t = 1.9 / e.spd_k
                aa = math.atan2(p.y - e.y, p.x - e.x)
                eb_shot(e.x, e.y, aa, 258, 5, 'amber')
        elif e.kind == 'charger':
            if e.state == 0:
                e.y += 48 * dt * k
                e.x = e.bx + math.sin(e.t * 1.7 + e.ph) * 28
                if e.t > 1.6:
                    e.state = 1
                    e.ct = .7
                    e.ang = math.atan2(p.y - e.y, p.x - e.x)
                    ring(e.x, e.y, 4, 52, 'violet', .45, 2)
            elif e.state == 1:
                e.ct -= dt
                if e.ct <= 0:
                    e.state = 2
                    e.ct = .8
                    AUD.play('shoot2', .4)
            else:
                e.x += math.cos(e.ang) * 560 * dt * k
                e.y += math.sin(e.ang) * 560 * dt * k
                e.ct -= dt
                if e.ct <= 0:
                    e.state = 0
                    e.t = 0
                    e.fire_t = 1.2
        elif e.kind == 'weaver':
            e.y = lerp(e.y, e.ay, dt * 1.5)
            e.x = e.bx + math.sin(e.t * .66 + e.ph) * 76
            e.fire_t -= dt
            if e.fire_t <= 0 and e.t > 1.1:
                e.fire_t = 2.7
                a = math.atan2(p.y - e.y, p.x - e.x)
                eb_shot(e.x, e.y, a, 128, 13, 'green', kind='web')
        elif e.kind == 'bulwark':
            if e.y < e.ay:
                e.y += 34 * dt * k
            e.x = e.bx + math.sin(e.t * .55 + e.ph) * 52
            if e.state == 0 and e.hp <= e.maxhp * .6:
                e.state = 1
                ring(e.x, e.y, 10, e.r * 3.2, 'coral', .55, 3)
                particle(e.x, e.y, 12, 'steel', 180, 24, .5)
                AUD.play('hit', .6)
            e.fire_t -= dt
            if e.fire_t <= 0 and e.t > 1.2:
                e.fire_t = 2.5 if e.state else 3.0
                a = math.atan2(p.y - e.y, p.x - e.x)
                rng = 2 if e.state else 1
                for j in range(-rng, rng + 1):
                    eb_shot(e.x, e.y + 12, a + j * .21, 205, 7, 'steel')
        elif e.kind == 'spinner':
            if e.y < e.ay:
                e.y += 66 * dt * k
            e.x = e.bx + math.sin(e.t * 1.5 + e.ph) * 66
            e.ang += dt * 5.2
            if e.t > 1.2 and random.random() < .22:
                particle(e.x + math.cos(e.ang) * 34, e.y + math.sin(e.ang) * 34, 1, 'violet', 40, 12, .25)
        elif e.kind == 'bomber':
            a = math.atan2(p.y - e.y, p.x - e.x)
            spd = 96 + min(150, e.t * 46)
            e.x += math.cos(a) * spd * dt * k
            e.y += math.sin(a) * spd * dt * k
            if dist2((e.x, e.y), (p.x, p.y)) < 84 ** 2 or e.t > 4.6:
                for j in range(14):
                    aa = j * math.pi * 2 / 14 + e.t
                    eb_shot(e.x, e.y, aa, 230, 7, 'coral')
                ring(e.x, e.y, 8, 170, 'coral', .5, 3)
                particle(e.x, e.y, 16, 'amber', 220, 26, .55)
                G.shake = max(G.shake, 9)
                AUD.play('big', .7)
                kill_enemy(e)
                continue
        elif e.kind == 'sniper':
            e.y = lerp(e.y, e.ay, dt * 2.2)
            e.x = e.bx + math.sin(e.t * .5 + e.ph) * 40
            if e.state == 0:
                e.fire_t -= dt
                if e.fire_t <= 0 and e.y > G.camy + 40:
                    e.state = 1
                    e.ct = .95
                    e.ang = math.atan2(p.y - e.y, p.x - e.x)
            else:
                e.ct -= dt
                if e.ct <= 0:
                    eb_shot(e.x, e.y + 6, e.ang, 560, 6, 'aqua')
                    e.state = 0
                    e.fire_t = 2.4 / e.spd_k
                    AUD.play('shoot2', .5)
        elif e.kind == 'dart':
            # 疾矢：悬停 → 锁定 → 高速俯冲
            if e.state == 0:
                e.y += 46 * dt * k
                e.x = e.bx + math.sin(e.t * 1.9 + e.ph) * 24
                if e.t > .75:
                    e.state = 1
                    e.ct = .4
                    e.ang = math.atan2(p.y - e.y, p.x - e.x)
                    ring(e.x, e.y, 3, 38, 'amber', .35, 2)
            elif e.state == 1:
                e.ct -= dt
                e.ang = math.atan2(p.y - e.y, p.x - e.x)
                if e.ct <= 0:
                    e.state = 2
                    e.ct = 1.4
                    AUD.play('shoot2', .4)
            else:
                e.x += math.cos(e.ang) * 520 * dt * k
                e.y += math.sin(e.ang) * 520 * dt * k
                e.ct -= dt
                if e.ct <= 0:
                    e.state = 0
                    e.t = 0
                    e.ct = 0
                    e.fire_t = 1.0
        elif e.kind == 'spawner':
            # 孵巢：慢速下沉，持续孵出火花并打环形弹
            if e.y < e.ay:
                e.y += 30 * dt * k
            e.x = e.bx + math.sin(e.t * .6 + e.ph) * 50
            e.fire_t -= dt
            if e.fire_t <= 0 and e.t > 1.4:
                e.fire_t = 3.0
                if len(G.enemies) < 20:
                    for j in range(2):
                        G.enemies.append(Enemy('spark', e.x + rnd(26, -26), e.y + rnd(18, 2),
                                               G.run.layer, G.run.wave, scale_hp=False))
                n = 10 + e.t // 6
                for j in range(int(min(18, n))):
                    a = j * math.pi * 2 / max(1, int(min(18, n))) + e.t
                    eb_shot(e.x, e.y, a, 150, 6, 'violet')
                ring(e.x, e.y, 8, 90, 'violet', .4, 2)
        elif e.kind == 'laser':
            # 灼光：蓄能 → 垂直光柱，站错位置就要挨打
            e.y = lerp(e.y, e.ay, dt * 2.0)
            e.x = e.bx + math.sin(e.t * .4 + e.ph) * 30
            if e.state == 0:
                e.fire_t -= dt
                if e.fire_t <= 0:
                    e.state = 1
                    e.ct = 1.1
            elif e.state == 1:
                e.ct -= dt
                if e.ct <= 0:
                    e.state = 2
                    e.beam_life = .6
                    G.shake = max(G.shake, 5)
                    AUD.play('shoot2', .8)
            else:
                e.beam_life -= dt
                if p and abs(p.x - e.x) < 16 and p.y > e.y:
                    hurt_player(1)
                if e.beam_life <= 0:
                    e.state = 0
                    e.fire_t = 2.6 / e.spd_k
        elif e.kind == 'orb':
            # 游魂：缓慢贴身，死亡时裂成两粒火花
            a = math.atan2(p.y - e.y, p.x - e.x)
            spd = 96 + min(90, e.t * 18)
            e.x += math.cos(a) * spd * dt * k
            e.y += math.sin(a) * spd * dt * k
        elif e.kind == 'sweeper':
            # 扫光：悬停后左右扫射一条长光束，站错线就挨打
            e.y = lerp(e.y, e.ay, dt * 2.0)
            e.x = e.bx + math.sin(e.t * .45 + e.ph) * 38
            e.ct -= dt
            if e.ct <= 0:
                e.state = 1 - e.state
                e.ct = 2.0 if e.state else 1.25
            if e.state == 1:
                e.ang = math.pi * .5 + math.sin(e.t * .9 + e.ph) * .78
                bx = e.x + math.cos(e.ang) * 520
                by = e.y + math.sin(e.ang) * 520
                if p and seg_dist2(p.x, p.y, e.x, e.y, bx, by) < 13 ** 2:
                    hurt_player(1)
        elif e.kind == 'warden':
            # 守门：给附近敌机减伤，逼你先拆它
            if e.y < e.ay:
                e.y += 34 * dt * k
            e.x = e.bx + math.sin(e.t * .55 + e.ph) * 48
            e.fire_t -= dt
            if e.fire_t <= 0 and e.t > 1.2:
                e.fire_t = 3.2
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in (-1, 0, 1):
                    eb_shot(e.x, e.y + 8, a + j * .23, 188, 7, 'steel')
        elif e.kind == 'siphoner':
            # 汲取：用光束拖慢技能冷却，靠近才有用
            e.y = lerp(e.y, e.ay, dt * 1.8)
            e.x = e.bx + math.sin(e.t * .7 + e.ph) * 44
            e.fire_t -= dt
            if p and dist2((e.x, e.y), (p.x, p.y)) < 380 ** 2:
                cap = G.run.ship['cd'] * G.run.st['cd']
                p.skill_t = min(cap, p.skill_t + dt * .9)
                if e.fire_t <= 0:
                    e.fire_t = 2.7
                    a = math.atan2(p.y - e.y, p.x - e.x)
                    eb_shot(e.x, e.y, a, 172, 6, 'violet')
        elif e.kind == 'spear':
            # 标枪：先亮出瞄准线，再射出一根高速长矛
            e.y = lerp(e.y, e.ay, dt * 2.2)
            e.x = e.bx + math.sin(e.t * .65 + e.ph) * 52
            e.fire_t -= dt
            if e.state == 0:
                if e.fire_t <= 0 and p:
                    e.state = 1
                    e.ct = .55
                    e.ang = math.atan2(p.y - e.y, p.x - e.x)
            else:
                e.ct -= dt
                if e.ct <= 0:
                    if p:
                        eb_shot(e.x, e.y, e.ang, 335, 7, 'green', 'lance')
                    e.state = 0
                    e.fire_t = 1.7
        elif e.kind == 'miner':
            # 雷巢：在玩家附近丢下静止的感应雷
            e.y = lerp(e.y, e.ay, dt * 1.7)
            e.x = e.bx + math.sin(e.t * .55 + e.ph) * 46
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 2.4
                G.eb.append({'x': p.x + rnd(54, -54), 'y': p.y + rnd(44, -44),
                             'vx': 0, 'vy': 0, 'r': 9, 'col': 'amber',
                             't': 0, 'life': 6.5, 'kind': 'mine'})
        elif e.kind == 'titan':
            # 巨像：缓慢压上，周期性向四周喷出重弹
            e.y = lerp(e.y, e.ay, dt * 1.15)
            e.x = e.bx + math.sin(e.t * .3 + e.ph) * 74
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 2.6
                e.ang += .35
                for j in range(10):
                    eb_shot(e.x, e.y, e.ang + j * math.pi * 2 / 10, 155, 8, 'steel')
        elif e.kind == 'drake':
            # 龙骑：横向巡游，三连扇形齐射
            e.y = lerp(e.y, e.ay, dt * 1.7)
            e.x = e.bx + math.sin(e.t * .42 + e.ph) * 140
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 2.1
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in (-.22, 0, .22):
                    eb_shot(e.x, e.y + 8, a + j, 238, 6, 'coral')
        elif e.kind == 'mortar':
            # 迫击：抛出不规则慢速重弹
            e.y = lerp(e.y, e.ay, dt * 1.55)
            e.x = e.bx + math.sin(e.t * .35 + e.ph) * 38
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 2.8
                a = math.atan2(p.y - e.y, p.x - e.x)
                e.ang = a
                eb_shot(e.x, e.y, a, 92, 12, 'steel', 'heavy')
        elif e.kind == 'shade':
            # 幽影：短距闪现，贴着玩家散射
            e.ct -= dt
            if e.ct <= 0 and p:
                e.ct = 3.4
                a = rnd(6.28)
                e.x = clamp(p.x + math.cos(a) * rnd(300, 190), 30, G.ww - 30)
                e.y = clamp(p.y + math.sin(a) * rnd(230, 140), 40, G.wh - 40)
                particle(e.x, e.y, 8, 'violet', 120, 14, .4)
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 1.8
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in (-.34, 0, .34):
                    eb_shot(e.x, e.y, a + j, 215, 6, 'violet')
        elif e.kind == 'wisp':
            # 光蛾：高速穿梭，贴近后双发点射
            e.y = lerp(e.y, e.ay, dt * 2.2)
            e.x = e.bx + math.sin(e.t * 1.5 + e.ph) * 105
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 1.45
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in (-.12, .12):
                    eb_shot(e.x, e.y, a + j, 252, 5, 'white')
        elif e.kind == 'webber':
            # 织网：悬停抛网，命中会拖慢玩家
            e.y = lerp(e.y, e.ay, dt * 1.6)
            e.x = e.bx + math.sin(e.t * .5 + e.ph) * 58
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 2.25
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in (-.18, .18):
                    eb_shot(e.x, e.y, a + j, 128, 13, 'green', kind='web')
        elif e.kind == 'juggernaut':
            # 破城：缓慢压上，五连重炮覆盖
            e.y = lerp(e.y, e.ay, dt * 1.05)
            e.x = e.bx + math.sin(e.t * .24 + e.ph) * 68
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 3.0
                e.ang += .22
                for j in range(5):
                    eb_shot(e.x, e.y, e.ang - .55 + j * .275, 182, 9, 'coral', 'heavy')
        elif e.kind == 'prism':
            # 棱镜：悬停并折射三束高速光矛
            e.y = lerp(e.y, e.ay, dt * 1.6)
            e.x = e.bx + math.sin(e.t * .7 + e.ph) * 62
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 2.2
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in (-.2, 0, .2):
                    eb_shot(e.x, e.y, a + j, 305, 5, 'aqua', 'lance')
        elif e.kind == 'hive':
            # 蜂巢：不断孵出小蜂
            e.y = lerp(e.y, e.ay, dt * 1.4)
            e.x = e.bx + math.sin(e.t * .36 + e.ph) * 44
            e.ct -= dt
            if e.ct <= 0 and len(G.enemies) < 14:
                e.ct = 3.1
                for j in range(2):
                    G.enemies.append(Enemy('spark', e.x + rnd(40, -40), e.y + 20,
                                           G.run.layer, G.run.wave, scale_hp=False))
                particle(e.x, e.y, 6, 'amber', 80, 12, .35)
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 2.8
                a = math.atan2(p.y - e.y, p.x - e.x)
                eb_shot(e.x, e.y, a, 180, 9, 'amber', 'heavy')
        elif e.kind == 'lancer':
            # 骑枪：锁定后高速冲锋
            if e.state == 0:
                e.y = lerp(e.y, e.ay, dt * 1.8)
                e.x = e.bx + math.sin(e.t * .75 + e.ph) * 72
                e.fire_t -= dt
                if e.fire_t <= 0 and p:
                    e.fire_t = 2.6
                    e.state = 1
                    e.ct = .5
                    e.ang = math.atan2(p.y - e.y, p.x - e.x)
                    ring(e.x, e.y, 8, 80, 'coral', .3, 2)
            else:
                e.ct -= dt
                e.x += math.cos(e.ang) * 460 * dt
                e.y += math.sin(e.ang) * 460 * dt
                if random.random() < .5:
                    particle(e.x, e.y, 2, 'coral', 120, 12, .25)
                if e.ct <= 0:
                    e.state = 0
                    e.fire_t = 2.6
        elif e.kind == 'cryo':
            # 冰晶：抛射冻结碎片
            e.y = lerp(e.y, e.ay, dt * 1.5)
            e.x = e.bx + math.sin(e.t * .42 + e.ph) * 50
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 2.0
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in (-.16, .16):
                    eb_shot(e.x, e.y, a + j, 170, 10, 'aqua', 'web')
        elif e.kind == 'torch':
            # 炬火：近距离喷出扇形火舌
            e.y = lerp(e.y, e.ay, dt * 1.5)
            e.x = e.bx + math.sin(e.t * .55 + e.ph) * 54
            e.fire_t -= dt
            if e.fire_t <= 0 and p:
                e.fire_t = 1.7
                a = math.atan2(p.y - e.y, p.x - e.x)
                for j in range(5):
                    eb_shot(e.x, e.y, a + (j - 2) * .11, 150, 7, 'amber')
                G.fires.append({'x': e.x, 'y': e.y + 40, 'r': 54, 't': 1.2,
                                'max': 1.2, 'col': 'amber'})
        elif e.kind == 'voidling':
            # 虚空幼体：闪烁到近处后放射
            e.ct -= dt
            if e.ct <= 0 and p:
                e.ct = 3.0
                a = rnd(6.28)
                e.x = clamp(p.x + math.cos(a) * 150, 30, G.ww - 30)
                e.y = clamp(p.y + math.sin(a) * 130, 40, G.wh - 40)
                for j in range(10):
                    eb_shot(e.x, e.y, j * math.pi / 5, 150, 7, 'violet')
                particle(e.x, e.y, 8, 'violet', 100, 14, .35)

        if e.y > G.wh + 130 or e.y < -420 or e.x < -170 or e.x > G.ww + 170:
            e.dead = True

        if p and G.scene == 'play' and dist2((e.x, e.y), (p.x, p.y)) < \
                (e.r * EKIND[e.kind].get('cr', .78) + 7) ** 2:
            kill_enemy(e, silent=True)
            if p.inv <= 0:
                hurt_player(1)

    # 冲刺撞击
    if p and p.dash_t > 0:
        for e in G.enemies:
            if e.dead or e.id in p.dash_hits:
                continue
            if dist2((e.x, e.y), (p.x, p.y)) < (e.r + 24) ** 2:
                p.dash_hits.add(e.id)
                damage_enemy(e, 14 * G.run.st['dmg'], e.x, e.y, False)
                G.shake = max(G.shake, 6)

    G.enemies = [e for e in G.enemies if not e.dead]


def damage_enemy(e, dmg, x, y, crit=False):
    if e.dead or getattr(e, 'boom_lock', False):
        return
    st = G.run.st if G.run else None
    if st and st['first'] > 0 and e.hp >= e.maxhp * .98:
        dmg *= 1 + .35 * st['first']
    if st and st['chill'] > 0 and e.slow > 0:
        dmg *= 1 + .25 * st['chill']
    if st and G.player:
        pd = dist2((e.x, e.y), (G.player.x, G.player.y))
        if st['close'] > 0 and pd < 280 ** 2:
            dmg *= 1 + .3 * st['close']
        if st['far'] > 0 and pd > 520 ** 2:
            dmg *= 1 + .25 * st['far']
    if st and st['finisher'] > 0 and e.hp < e.maxhp * .25:
        dmg *= 1 + .4 * st['finisher']
    if st and e.kind != 'warden':
        for w in G.enemies:
            if w.kind == 'warden' and not w.dead and dist2((w.x, w.y), (e.x, e.y)) < 210 ** 2:
                dmg *= .66
                break
    if st and st['exec'] > 0 and e.hp < e.maxhp * .35:
        dmg *= 1 + .35 * st['exec']
    if e.kind == 'bulwark' and e.state == 0:
        dmg *= .62
    e.hp -= dmg
    e.flash = .1
    particle(x, y, 3 if not crit else 7, 'white', 130, 14, .24)
    if crit:
        particle(x, y, 3, 'gold', 180, 22, .35)
        AUD.play('hit', .5)
    else:
        AUD.play('hit', .32)
    if e.hp <= 0:
        e.boom_lock = True
        if st and st['overk'] > 0:
            over = max(0, -e.hp)
            if over > 0:
                rad = 100 + 24 * st['overk']
                boom = min(18, over * .6) * st['overk']
                for o in G.enemies:
                    if o is e or o.dead:
                        continue
                    if dist2((o.x, o.y), (e.x, e.y)) < rad ** 2:
                        damage_enemy(o, boom, o.x, o.y, False)
                ring(e.x, e.y, 8, rad, 'amber', .36, 2)
        kill_enemy(e, crit=crit)


def kill_enemy(e, silent=False, crit=False):
    if e.dead and not silent:
        return
    e.dead = True
    if not G.run:
        return
    G.run.kills += 1
    d = EKIND[e.kind]
    G.combo += 1
    G.combo_t = 2.6
    G.combo_best = max(G.combo_best, G.combo)
    if G.combo >= 50:
        grant_ach('combo50')
    if G.combo in (5, 10, 15, 20, 30):
        toast('连击 ×%d' % G.combo, 'gold')
        AUD.play('card', .55)
    mult = 1 + min(12, G.combo) * .06
    G.run.score += int(d['score'] * (1 + (G.run.layer - 1) * .25) * mult
                       * (1 + .15 * G.run.st['greed'])
                       * (1 + .35 * G.run.st['gambler'])
                       * G.run.mut.get('score', 1.0)
                       * G.run.lmod['score']
                       * DIFFS[G.diff]['score'] * G.run.score_mult)
    col = d['col']
    particle(e.x, e.y, 16 if e.elite else 14, col, 210, 34 if e.elite else 30, .62)
    ring(e.x, e.y, 6, e.r * 3.2, col, .42, 2)
    if e.elite:
        ring(e.x, e.y, 10, e.r * 5.2, 'gold', .7, 4)
        G.shake = max(G.shake, 10)
    if silent:
        return
    AUD.play('kill', .55)

    st = G.run.st
    if crit and st['critboom'] > 0:
        rad = 130 + 22 * st['critboom']
        for o in G.enemies:
            if o is e or o.dead:
                continue
            if dist2((o.x, o.y), (e.x, e.y)) < rad ** 2:
                damage_enemy(o, 9 * st['dmg'] * st['critboom'], o.x, o.y, False)
        ring(e.x, e.y, 8, rad, 'gold', .42, 3)
    if st['shieldkill'] > 0 and G.run.kills % max(4, 9 - 2 * int(st['shieldkill'])) == 0:
        p = G.player
        if p:
            p.shield = min(3, p.shield + 1)
            p.shield_t = max(p.shield_t, 18)
            ring(p.x, p.y, 6, 64, 'aqua', .32, 2)
    if st['soul'] > 0 and G.run.kills % 30 == 0:
        G.run.max_hp += 1
        if G.player:
            G.player.max_hp = G.run.max_hp
            G.player.hp = min(G.run.max_hp, G.player.hp + 1)
        toast('灵魂配额 · 艇体上限 +1', 'gold')
    if G.run.kills >= 500:
        grant_ach('kills500')
    if G.run.kills >= 1000:
        grant_ach('kills1000')
    if G.run.kills >= 1500:
        grant_ach('kills1500')
    if G.run.kills >= 2500:
        grant_ach('kills2500')
    if G.run.kills >= 5000:
        grant_ach('kills5000')
    if st['shock'] > 0:
        rad = 88 + 16 * st['shock']
        for o in G.enemies:
            if o is e or o.dead:
                continue
            if dist2((o.x, o.y), (e.x, e.y)) < rad ** 2:
                damage_enemy(o, 3.2 * st['dmg'] * st['shock'], o.x, o.y, False)
        ring(e.x, e.y, 8, rad, 'amber', .34, 2)
    if st['slow'] > 0:
        G.slow_t = .5 + .15 * (st['slow'] - 1)
    if st['leech'] > 0 and random.random() < .20 * min(2, st['leech']):
        heal_player(1, quiet=True)
    if st['vamp'] > 0 and G.run.kills % max(2, 5 - st['vamp']) == 0:
        heal_player(1, quiet=True)

    if e.kind == 'lantern' and not silent:
        for i in (-1, 1):
            s = Enemy('spark', e.x + i * 14, e.y + 4, G.run.layer, G.run.wave, scale_hp=False)
            s.x += i * 20
            G.enemies.append(s)
    if e.kind == 'splitter' and not silent:
        for i in (-1, 1):
            s = Enemy('spark', e.x + i * 16, e.y + rnd(10, -6), G.run.layer, G.run.wave, scale_hp=False)
            s.r *= 1.7
            s.maxhp *= 2.4
            s.hp = s.maxhp
            G.enemies.append(s)
    if e.kind == 'orb' and not silent:
        for i in (-1, 1):
            G.enemies.append(Enemy('spark', e.x + i * 15, e.y + rnd(8, -8),
                                   G.run.layer, G.run.wave, scale_hp=False))

    # 连锁放电
    if st['chain'] > 0 and not getattr(e, 'chained', False):
        tg = []
        for o in G.enemies:
            if o is e or o.dead:
                continue
            dd = dist2((o.x, o.y), (e.x, e.y))
            if dd < 250 ** 2:
                tg.append((dd, o))
        tg.sort(key=lambda z: z[0])
        for dd, o in tg[:3]:
            o.chained = True
            damage_enemy(o, 2.4 * st['dmg'] * st['chain'], o.x, o.y, False)
            for k in range(7):
                t = k / 7.0
                particle(e.x + (o.x - e.x) * t + rnd(7, -7),
                         e.y + (o.y - e.y) * t + rnd(7, -7), 1, 'violet', 40, 10, .22)

    # 余烬尾迹：击杀处留一团灼烧
    if st['afterburn'] > 0 and not silent:
        G.fires.append({'x': e.x, 'y': e.y, 'r': 64 + 22 * st['afterburn'],
                        't': 2.0 + .4 * st['afterburn'], 'max': 2.0 + .4 * st['afterburn']})

    # 掉落
    drop_chance = (.16 * (1 + .3 * st['greed']) * (1 - .2 * st['gambler'])
                   * G.run.lmod['drop']
                   * (G.run.mut.get('drop', 1.0) if G.run else 1.0))
    if e.elite:
        drop_chance = 1.4
    got = 0
    while got < 2 and random.random() < drop_chance:
        kind = random.choices(['heal', 'shield', 'od'], weights=[50, 30, 20])[0]
        G.drops.append({'x': e.x + rnd(14, -14), 'y': e.y, 'kind': kind, 't': 0,
                        'vy': 46, 'vx': rnd(20, -20)})
        got += 1


def hurt_player(n):
    p = G.player
    if not p or p.inv > 0 or G.scene != 'play':
        return
    st = G.run.st if G.run else None
    if st and st['phase'] > 0 and random.random() < .12 * st['phase']:
        p.inv = max(p.inv, .5)
        ring(p.x, p.y, 8, 56, 'violet', .36, 2)
        AUD.play('card', .3)
        return
    if p.shield > 0:
        p.shield -= 1
        p.inv = .55
        ring(p.x, p.y, 12, 84, 'aqua', .42, 2)
        particle(p.x, p.y, 12, 'aqua', 170, 20, .45)
        G.shake = max(G.shake, 6)
        AUD.play('hit', .7)
        if p.shield == 0:
            AUD.say('shield')
        if st and st['shieldburst'] > 0:
            rad = 110 + 24 * st['shieldburst']
            for e in G.enemies:
                if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                    damage_enemy(e, 6 * st['dmg'] * st['shieldburst'], e.x, e.y, False)
            ring(p.x, p.y, 8, rad, 'aqua', .42, 2)
        return
    p.hp -= n
    if st and st['fragile'] > 0:
        p.hp -= int(st['fragile'])
    if random.random() < DIFFS[G.diff]['dmg2']:
        p.hp -= 1
        toast('重创！', 'coral')
    p.inv = 1.5
    p.flash = 1.0
    G.shake = max(G.shake, 18)
    G.flashv = .35
    particle(p.x, p.y, 22, 'coral', 230, 32, .6)
    ring(p.x, p.y, 10, 130, 'coral', .5, 3)
    AUD.play('hurt', .8)
    if st and st['thorns'] > 0:
        rad = 120 + 30 * st['thorns']
        for e in G.enemies:
            if not e.dead and dist2((e.x, e.y), (p.x, p.y)) < rad ** 2:
                damage_enemy(e, 3.2 * st['dmg'] * st['thorns'], e.x, e.y, False)
        for k in range(14):
            a = k * math.pi / 7
            particle(p.x + math.cos(a) * 26, p.y + math.sin(a) * 26, 1, 'steel', 190, 16, .4,
                     direction=a, spread=.5)
        ring(p.x, p.y, 8, rad, 'steel', .4, 2)
    if st and st['retaliate'] > 0:
        n = 10 + 4 * int(st['retaliate'])
        base = 1.8 * st['dmg'] * st['retaliate']
        for k in range(n):
            a = k * math.pi * 2 / n + G.t * .2
            G.pb.append({'x': p.x + math.cos(a) * 16, 'y': p.y + math.sin(a) * 16,
                         'vx': math.cos(a) * 620, 'vy': math.sin(a) * 620, 'r': 4,
                         'dmg': base, 'pierce': 0, 'hits': [], 'crit': False,
                         'homing': 0, 'freeze': 0, 'burn': 0, 'mirror': 0, 'rico': 0,
                         'life': 1.1, 'child': True})
        ring(p.x, p.y, 8, 96, 'amber', .35, 2)
    if p.hp <= 0:
        p.hp = 0
        kill_player()


def heal_player(n, quiet=False):
    p = G.player
    if not p:
        return
    if p.hp >= G.run.max_hp:
        if not quiet:
            G.run.score += 20
        return
    p.hp = min(G.run.max_hp, p.hp + n)
    if not quiet:
        toast('艇体修复 +%d' % n, 'green')
        AUD.play('pick', .8)


# ================================================================
#  敌弹
# ================================================================
def update_eb(dt):
    p = G.player
    slow = .45 if G.slow_t > 0 else 1.0
    for b in G.eb:
        b['x'] += b['vx'] * dt * slow
        b['y'] += b['vy'] * dt * slow
        b['t'] += dt
        b['life'] -= dt
        if (b['life'] <= 0 or b['x'] < G.camx - 160 or b['x'] > G.camx + W + 160
                or b['y'] < G.camy - 210 or b['y'] > G.camy + H + 170):
            b['life'] = 0
            continue
        if p and p.inv <= 0 and dist2((b['x'], b['y']), (p.x, p.y)) < (b['r'] * .8 + 6) ** 2:
            b['life'] = 0
            if b.get('kind') == 'web':
                p.web_t = 1.9
                ring(p.x, p.y, 7, 48, 'green', .4, 2)
                AUD.play('card', .3)
            else:
                hurt_player(1)
    G.eb = [b for b in G.eb if b['life'] > 0]


# ================================================================
#  BOSS
# ================================================================
BOSSCFG = [
    dict(name='守夜者', en='WARDEN OF THE DARK', hp=105, r=62, col='amber'),
    dict(name='钟摆', en='THE PENDULUM', hp=140, r=56, col='violet'),
    dict(name='深渊之口', en='MAW OF THE ABYSS', hp=185, r=76, col='coral'),
    dict(name='回响之眼', en='EYE OF ECHOES', hp=230, r=58, col='green'),
    dict(name='终末回声', en='THE LAST ECHO', hp=275, r=84, col='white'),
    dict(name='归墟者', en='THE HOLLOW TIDE', hp=330, r=80, col='aqua'),
    dict(name='蚀骨者', en='RUSTBONE', hp=385, r=72, col='green'),
    dict(name='零号守卫', en='UNIT ZERO', hp=445, r=66, col='steel'),
    dict(name='回廊之核', en='CORRIDOR CORE', hp=530, r=92, col='gold'),
    dict(name='赤潮主', en='CRIMSON SOVEREIGN', hp=610, r=86, col='coral', pattern=2),
    dict(name='星骸', en='STAR WRAITH', hp=700, r=74, col='steel', pattern=7),
    dict(name='白洞', en='WHITE HOLE', hp=800, r=96, col='white', pattern=8),
    dict(name='霓虹主', en='NEON SOVEREIGN', hp=900, r=80, col='violet', pattern=1),
    dict(name='灰烬王', en='ASHEN KING', hp=1000, r=90, col='amber', pattern=4),
    dict(name='终焉', en='THE END', hp=1150, r=100, col='white', pattern=8),
    dict(name='虚空花母', en='VOID MATRON', hp=1250, r=95, col='green', pattern=6),
    dict(name='时骸', en='TIME WRAITH', hp=1350, r=88, col='steel', pattern=7),
    dict(name='深渊之底', en='ABYSS FLOOR', hp=1500, r=110, col='coral', pattern=8),
    dict(name='星墓主', en='LORD OF STAR GRAVE', hp=1650, r=95, col='steel', pattern=7),
    dict(name='熔核巨像', en='MOLTEN COLOSSUS', hp=1800, r=105, col='amber', pattern=6),
    dict(name='回廊尽头', en='CORRIDOR END', hp=2000, r=115, col='white', pattern=8),
    dict(name='静默观测者', en='SILENT WATCHER', hp=2300, r=100, col='aqua', pattern=3),
    dict(name='铸世者', en='WORLD FORGER', hp=2600, r=110, col='gold', pattern=5),
    dict(name='门后的东西', en='THE THING BEYOND', hp=3000, r=125, col='white', pattern=8),
    dict(name='盐圣', en='SALT HIEROPHANT', hp=3350, r=112, col='steel', pattern=5),
    dict(name='齿轮圣像', en='GEAR IDOL', hp=3700, r=118, col='amber', pattern=3),
    dict(name='虚数鲸', en='IMAGINARY WHALE', hp=4100, r=128, col='violet', pattern=7),
    dict(name='终末之眼', en='THE FINAL EYE', hp=4550, r=132, col='white', pattern=8),
]

def boss_pool(layer):
    # 前九层只用原九位 BOSS；十至十二层加入第一批终局 BOSS；
    # 十三至十五层第二批；十六至十八层第三批；十九至二十一层第四批；二十二层后全部开放
    if layer < 10:
        return BOSSCFG[:9]
    if layer < 13:
        return BOSSCFG[:12]
    if layer < 16:
        return BOSSCFG[:15]
    if layer < 19:
        return BOSSCFG[:18]
    if layer < 22:
        return BOSSCFG[:21]
    if layer < 25:
        return BOSSCFG[:24]
    return BOSSCFG


BOSS_SIG_NAMES = [
    '巡夜探照', '钟摆横扫', '深渊吞吸', '回声定位', '迟到回声', '归墟漩涡',
    '蚀骨酸雨', '零号协议', '核心过载', '赤潮拍岸', '星骸坠雨', '白洞引力',
    '霓虹矩阵', '灰烬风暴', '终焉钟声', '花母绽放', '时骸回拨', '深渊触手',
    '星墓坍缩', '熔核喷发', '尽头合拢', '静默凝视', '铸世锤击', '门扉全开',
    '盐柱审判', '齿轮碾压', '虚数抹除', '终末凝视',
]

BOSS_SIG2_NAMES = [
    '熄灯搜查', '双摆夹击', '巨口回流', '回声牢笼', '残响复写', '沉没',
    '骨刺之墙', '协议封锁', '核心坍缩', '血浪回卷', '星屑轨道', '事件视界',
    '霓虹囚笼', '王座余烬', '审判日', '孢子云', '时间倒带', '触手收网',
    '墓碑阵列', '地脉喷涌', '闭门', '零声场', '重锻', '门扉倒影',
    '霜蚀圣咏', '反向传动', '潮汐悖论', '视界闭合',
]


class Boss:
    def __init__(self, layer):
        off = G.run.boss_off if G.run else 0
        pool = boss_pool(layer)
        self.kind = (layer - 1 + off) % len(pool)
        cfg = pool[self.kind]
        self.cfg = cfg
        self.pattern = cfg.get('pattern', self.kind)
        self.x = G.camx + W / 2
        self.y = G.camy - 150
        self.r = cfg['r']
        self.maxhp = (cfg['hp'] * (1 + (layer - 1) * .30) * DIFFS[G.diff]['ehp']
                      * mode_of().get('boss_hp', 1.0) * threat_of(layer)
                      * (G.run.mut.get('boss_hp', 1.0) if G.run else 1.0))
        self.hp = self.maxhp
        self.t = 0
        self.phase = 1
        self.enter = True
        self.fire_t = 1.2
        self.pattern_t = 0
        self.dying = False
        self.die_t = 0
        self.flash = 0
        self.rot = 0
        self.sig = self.kind
        self.sig_name = BOSS_SIG_NAMES[self.kind]
        self.sig_t = 3.2
        self.sig_seen = False
        self.sig2_name = BOSS_SIG2_NAMES[self.kind]
        self.sig2_t = 6.5
        self.sig2_seen = False
        self.atkspd = (mode_of().get('bossrate', 1.0) * (1 + (layer - 1) * .012)
                       * (G.run.mut.get('bossrate', 1.0) if G.run else 1.0))
        self.spd_scale = 1 + (layer - 1) * .010
        self.rage_t = 18.0


def spawn_boss():
    G.cam_lock = arena_of_player()
    G.boss = Boss(G.run.layer)
    G.eb = []
    p = G.player
    if p:
        p.shield = min(3, p.shield + 1)
        p.shield_t = max(p.shield_t, 30)
    AUD.play('boss', .85)
    G.shake = max(G.shake, 12)
    bname = BOSSCFG[G.boss.kind]['en'] if META.get('lang') else BOSSCFG[G.boss.kind]['name']
    toast(L(bname + ' 出现 · 护盾 +1', bname + ' APPEARS · SHIELD +1'), 'coral')


def boss_signature(b):
    """每位 BOSS 的专属绝技：按身份而不是通用弹幕模板区分"""
    p = G.player
    if not p:
        return
    ph = b.phase
    fast = ph == 3
    aim = math.atan2(p.y - b.y, p.x - b.x)
    sig = b.sig
    if sig == 0:
        # 守夜者 · 巡夜探照：四盏探照灯轮流扫射
        for k in range(4):
            a = b.rot * 2.1 + k * math.pi / 2
            for j in range(3):
                eb_shot(b.x, b.y, a + (j - 1) * .13, 255 if fast else 220, 6, 'amber')
        ring(b.x, b.y, 12, 230, 'amber', .5, 2)
    elif sig == 1:
        # 钟摆 · 钟摆横扫：整片场地两排横向弹墙
        for row in range(2):
            for k in range(16):
                eb_shot(G.camx - 30, b.y + 24 + row * 30, 0, 205 if fast else 168, 6,
                        'violet' if row == 0 else 'white')
        ring(b.x, b.y, 10, 340, 'violet', .45, 2)
    elif sig == 2:
        # 深渊之口 · 深渊吞吸：把玩家往巨口里拖，再吐出环弹
        p.x = clamp(lerp(p.x, b.x, .20), G.camx + 34, G.camx + W - 34)
        p.y = clamp(lerp(p.y, b.y + 80, .13), G.camy + 70, G.camy + H - 36)
        for k in range(22 + ph * 4):
            eb_shot(b.x, b.y, k * math.pi * 2 / (22 + ph * 4) + b.rot, 180, 7, 'coral')
        ring(b.x, b.y, 20, 390, 'coral', .5, 3)
    elif sig == 3:
        # 回响之眼 · 回声定位：先标记玩家，再以眼为中心收束
        ring(p.x, p.y, 20, 120, 'green', .5, 3)
        for k in range(9 + ph * 2):
            eb_shot(b.x, b.y, aim + (k - (8 + ph * 2) / 2) * .055,
                    300 if fast else 252, 5, 'green')
        particle(p.x, p.y, 8, 'green', 90, 20, .45)
    elif sig == 4:
        # 终末回声 · 迟到回声：从玩家两侧复制一轮延迟齐射
        for side in (-1, 1):
            for k in range(6):
                eb_shot(p.x + side * 210, p.y - 120 - k * 18,
                        math.pi / 2 + side * .18, 150 if fast else 120, 6, 'white')
        ring(p.x, p.y, 8, 160, 'white', .5, 2)
    elif sig == 5:
        # 归墟者 · 归墟漩涡：在玩家脚下开一个吸积漩涡
        G.well = {'x': p.x, 'y': p.y, 't': 3.2, 'max': 3.2, 'r': 180,
                  'acc': 0, 'ang': 0}
        for k in range(18 + ph * 4):
            a = k * math.pi * 2 / (18 + ph * 4) + b.rot * 1.4
            eb_shot(b.x, b.y, a, 155, 8, 'aqua')
    elif sig == 6:
        # 蚀骨者 · 蚀骨酸雨：在场地里留下腐蚀坑
        for k in range(3 + ph):
            G.fires.append({'x': p.x + rnd(190, -190), 'y': p.y + rnd(150, -150),
                            'r': 76, 't': 3.4, 'max': 3.4, 'col': 'green'})
        for k in range(12):
            eb_shot(G.camx + rnd(W, 0), G.camy - 20, math.pi / 2, 145, 6, 'green')
        ring(p.x, p.y, 10, 230, 'green', .55, 2)
    elif sig == 7:
        # 零号守卫 · 零号协议：八向锁链弹道
        for k in range(8):
            a = b.rot * 1.3 + k * math.pi / 4
            for j in range(6):
                eb_shot(b.x, b.y, a, 135 + j * 30, 4, 'steel' if j % 2 else 'white')
        ring(b.x, b.y, 12, 260, 'steel', .45, 1)
    elif sig == 8:
        # 回廊之核 · 核心过载：三层反向环同时收缩
        for ri, spd in ((0, 255), (1, 190), (2, 135)):
            n = 18 + ph * 4
            for k in range(n):
                a = k * math.pi * 2 / n + b.rot * (1 if ri % 2 == 0 else -1) * 1.5
                eb_shot(b.x, b.y, a, spd, 7, 'gold' if ri == 2 else ('aqua' if ri == 0 else 'violet'))
        G.shake = max(G.shake, 8)
    elif sig == 9:
        # 赤潮主 · 赤潮拍岸：左右两侧同时推来潮墙
        for side, xx in ((-1, G.camx - 40), (1, G.camx + W + 40)):
            for k in range(10):
                eb_shot(xx, b.y - 160 + k * 34, 0 if side < 0 else math.pi,
                        190 if fast else 155, 7, 'coral')
        ring(b.x, b.y, 10, 420, 'coral', .7, 3)
    elif sig == 10:
        # 星骸 · 星骸坠雨：陨星从镜头上方砸向玩家
        for k in range(12 + ph * 3):
            eb_shot(p.x + rnd(330, -330), G.camy - 40, math.pi / 2 + rnd(.12, -.12),
                    170 if fast else 135, 7, 'white' if k % 3 else 'steel')
        ring(p.x, p.y, 10, 260, 'steel', .45, 2)
    elif sig == 11:
        # 白洞 · 白洞引力：强拉玩家并向外喷发
        p.x = clamp(lerp(p.x, b.x, .30), G.camx + 34, G.camx + W - 34)
        p.y = clamp(lerp(p.y, b.y + 120, .22), G.camy + 70, G.camy + H - 36)
        for k in range(26 + ph * 6):
            eb_shot(b.x, b.y, k * math.pi * 2 / (26 + ph * 6), 210, 6, 'white')
        ring(b.x, b.y, 18, 500, 'white', .7, 4)
    elif sig == 12:
        # 霓虹主 · 霓虹矩阵：横竖激光弹幕织网
        for k in range(10):
            eb_shot(G.camx + 40 + k * (W - 80) / 9, b.y, math.pi / 2, 205, 5, 'violet')
        for k in range(7):
            eb_shot(b.x, G.camy + 60 + k * (H - 120) / 6, 0, 205, 5, 'aqua')
        ring(b.x, b.y, 10, 300, 'violet', .45, 2)
    elif sig == 13:
        # 灰烬王 · 灰烬风暴：灰烬火雨覆盖玩家周围
        for k in range(5 + ph):
            G.fires.append({'x': p.x + rnd(220, -220), 'y': p.y + rnd(180, -180),
                            'r': 92, 't': 3.0, 'max': 3.0, 'col': 'amber'})
        for k in range(16):
            eb_shot(p.x + rnd(280, -280), G.camy - 30, math.pi / 2, 155, 6, 'amber')
        ring(p.x, p.y, 12, 280, 'amber', .5, 2)
    elif sig == 14:
        # 终焉 · 终焉钟声：慢速巨弹与全场震响
        for k in range(12):
            eb_shot(b.x, b.y, k * math.pi / 6 + b.rot, 120, 10, 'white' if k % 2 else 'violet')
        for k in range(6):
            eb_shot(b.x, b.y, aim + (k - 2.5) * .16, 360, 5, 'coral')
        G.flashv = max(G.flashv, .22)
        G.shake = max(G.shake, 12)
    elif sig == 15:
        # 虚空花母 · 花母绽放：种子向四周炸开并留下孢子地
        for k in range(16 + ph * 4):
            a = k * math.pi * 2 / (16 + ph * 4)
            eb_shot(b.x, b.y, a, 130, 9, 'green')
        for k in range(4):
            G.fires.append({'x': b.x + rnd(260, -260), 'y': b.y + rnd(180, -120),
                            'r': 70, 't': 3.2, 'max': 3.2, 'col': 'green'})
        ring(b.x, b.y, 14, 320, 'green', .6, 3)
    elif sig == 16:
        # 时骸 · 时骸回拨：把玩家拖进慢速区
        p.web_t = max(p.web_t, 1.8)
        for k in range(10 + ph * 2):
            eb_shot(b.x, b.y, k * math.pi * 2 / (10 + ph * 2) + b.rot, 175, 7, 'steel')
        ring(p.x, p.y, 16, 240, 'steel', .6, 2)
        ring(b.x, b.y, 12, 360, 'aqua', .55, 2)
    elif sig == 17:
        # 深渊之底 · 深渊触手：六根触手从底部升起
        for k in range(6):
            xx = b.x - 260 + k * 104
            for j in range(4):
                eb_shot(xx, G.camy + H + 20, -math.pi / 2, 150 + j * 35, 6, 'coral')
        ring(b.x, b.y, 16, 360, 'coral', .55, 3)
    elif sig == 18:
        # 星墓主 · 星墓坍缩：引力井 + 星屑环
        G.well = {'x': p.x, 'y': p.y, 't': 2.8, 'max': 2.8, 'r': 170,
                  'acc': 0, 'ang': 0}
        for k in range(24 + ph * 5):
            eb_shot(b.x, b.y, k * math.pi * 2 / (24 + ph * 5) + b.rot, 190, 6, 'steel')
        ring(b.x, b.y, 12, 360, 'white', .5, 2)
    elif sig == 19:
        # 熔核巨像 · 熔核喷发：三根岩浆柱从地面冲起
        for dx in (-150, 0, 150):
            G.fires.append({'x': clamp(p.x + dx, G.camx + 40, G.camx + W - 40),
                            'y': p.y + 20, 'r': 80, 't': 3.0, 'max': 3.0, 'col': 'amber'})
        for k in range(14):
            eb_shot(p.x + rnd(230, -230), G.camy + H + 20, -math.pi / 2,
                    160 if fast else 130, 7, 'amber')
        G.shake = max(G.shake, 10)
    elif sig == 20:
        # 回廊尽头 · 尽头合拢：两侧弹墙向中间挤压
        for side, xx in ((-1, G.camx - 20), (1, G.camx + W + 20)):
            for k in range(9):
                eb_shot(xx, b.y - 120 + k * 32, 0 if side < 0 else math.pi,
                        210 if fast else 170, 6, 'white')
        ring(b.x, b.y, 10, 460, 'gold', .8, 4)
    elif sig == 21:
        # 静默观测者 · 静默凝视：锁定一道贯穿场地的观测光束
        add_beam(p.x, p.y, 'aqua', .55)
        for k in range(18):
            eb_shot(b.x, b.y, aim + (k - 8.5) * .028, 260 if fast else 210, 5, 'aqua')
        ring(p.x, p.y, 10, 90, 'aqua', .35, 2)
    elif sig == 22:
        # 铸世者 · 铸世锤击：三圈冲击波向外锻打
        for ri, spd in ((0, 260), (1, 200), (2, 145)):
            n = 20 + ph * 4
            for k in range(n):
                eb_shot(b.x, b.y, k * math.pi * 2 / n + b.rot * .5, spd, 8,
                        'gold' if ri == 2 else 'amber')
        G.shake = max(G.shake, 16)
        ring(b.x, b.y, 12, 380, 'gold', .6, 3)
    elif sig == 23:
        # 门后的东西 · 门扉全开：全场射线与虚空幼体
        for k in range(30 + ph * 6):
            eb_shot(b.x, b.y, k * math.pi * 2 / (30 + ph * 6) + b.rot, 145, 6,
                    'white' if k % 4 == 0 else 'violet')
        for k in range(2 + ph):
            G.enemies.append(Enemy('voidling' if 'voidling' in EKIND else 'spark',
                                   b.x + rnd(160, -160), b.y + rnd(60, 0),
                                   G.run.layer, G.run.wave, scale_hp=False))
        G.flashv = max(G.flashv, .28)
    else:
        for k in range(20):
            eb_shot(b.x, b.y, k * math.pi / 10 + b.rot, 190, 7, 'white')


def boss_signature2(b):
    """第二绝技：第 2 阶段解锁，每个 BOSS 与名字对应的第二种杀招"""
    p = G.player
    if not p:
        return
    ph = b.phase
    fast = ph == 3
    sig = b.kind
    aim = math.atan2(p.y - b.y, p.x - b.x)
    cx0, cy0 = G.camx, G.camy
    R = b.r

    if sig == 0:
        # 守夜者 · 熄灯搜查：先扫出两道探照，再短点射
        for s in (-1, 1):
            a = b.rot * 1.8 * s
            for k in range(9):
                eb_shot(b.x, b.y, a + k * .045, 250 if fast else 210, 5, 'amber')
        for k in range(6):
            eb_shot(b.x, b.y, aim + (k - 2.5) * .06, 330, 5, 'white')
        ring(b.x, b.y, 14, 380, 'amber', .5, 2)
    elif sig == 1:
        # 钟摆 · 双摆夹击：左右两条摆动的竖向弹幕
        for side in (-1, 1):
            for k in range(8):
                yy = cy0 + 80 + k * (H - 160) / 7 + math.sin(b.t * 2.1 + side * 1.6) * 30
                xx = cx0 - 20 if side < 0 else cx0 + W + 20
                eb_shot(xx, yy, 0 if side < 0 else math.pi, 190 if fast else 155, 6, 'violet')
        for k in range(7):
            eb_shot(b.x, b.y, aim + (k - 3) * .08, 280, 5, 'white')
    elif sig == 2:
        # 深渊之口 · 巨口回流：外圈弹丸向巨口收束
        for k in range(30):
            a = k * math.pi * 2 / 30 + b.rot * .8
            sx = clamp(b.x + math.cos(a) * 430, cx0 - 20, cx0 + W + 20)
            sy = clamp(b.y + math.sin(a) * 300, cy0 - 20, cy0 + H + 20)
            eb_shot(sx, sy, math.atan2(b.y - sy, b.x - sx), 165 if fast else 135, 6, 'coral')
        G.well = {'x': p.x, 'y': p.y, 'r': 150, 't': 2.4, 'max': 2.4, 'ang': 0, 'pull': 85}
    elif sig == 3:
        # 回响之眼 · 回声牢笼：四角锚点同时向玩家收束
        for k in range(4):
            a = k * math.pi / 2 + b.rot * .3
            sx, sy = p.x + math.cos(a) * 340, p.y + math.sin(a) * 250
            for j in range(4):
                eb_shot(sx, sy, math.atan2(p.y - sy, p.x - sx) + (j - 1.5) * .06,
                        220 if fast else 185, 5, 'green')
        for k in range(10):
            eb_shot(b.x, b.y, aim + (k - 4.5) * .07, 245, 5, 'aqua')
    elif sig == 4:
        # 终末回声 · 残响复写：从玩家四周复制同一组弹道
        for dx, dy in ((-260, 0), (260, 0), (0, -230), (0, 230)):
            sx, sy = p.x + dx, p.y + dy
            for k in range(4):
                eb_shot(sx, sy, math.atan2(p.y - sy, p.x - sx) + (k - 1.5) * .07,
                        205 if fast else 175, 6, 'violet')
        for k in range(14):
            eb_shot(b.x, b.y, k * math.pi / 7 + b.rot, 175, 6, 'white')
    elif sig == 5:
        # 归墟者 · 沉没：漩涡拖拽 + 慢速大环
        G.well = {'x': p.x, 'y': p.y, 'r': 170, 't': 2.7, 'max': 2.7, 'ang': 0, 'pull': 105}
        for k in range(24):
            eb_shot(b.x, b.y, k * math.pi / 12 + b.rot, 145 if fast else 120, 10, 'aqua')
        for k in range(8):
            eb_shot(b.x, b.y, aim + (k - 3.5) * .09, 260, 6, 'steel')
    elif sig == 6:
        # 蚀骨者 · 骨刺之墙：上下两排骨墙只留一道横缝
        gap = cx0 + W * (.5 + .38 * math.sin(b.t * 1.35))
        for row in (0, 1):
            for k in range(16):
                xx = cx0 + 40 + k * (W - 80) / 15
                if abs(xx - gap) < 95:
                    continue
                yy = cy0 - 20 if row == 0 else cy0 + H + 20
                eb_shot(xx, yy, math.pi / 2 if row == 0 else -math.pi / 2,
                        170 if fast else 145, 6, 'green')
        for k in range(6):
            eb_shot(b.x, b.y, aim + (k - 2.5) * .11, 280, 6, 'amber')
    elif sig == 7:
        # 零号守卫 · 协议封锁：四臂旋转，附带三发重型协议弹
        for k in range(4):
            a = b.rot * 1.9 + k * math.pi / 2
            for j in range(5):
                eb_shot(b.x + math.cos(a) * R * .65, b.y + math.sin(a) * R * .65,
                        a, 165 + j * 40, 5, 'steel')
        for k in range(3):
            eb_shot(b.x, b.y, aim + (k - 1) * .12, 360, 9, 'white')
    elif sig == 8:
        # 回廊之核 · 核心坍缩：外圈层层向内塌缩
        for k in range(30):
            a = k * math.pi * 2 / 30 - b.rot
            sx, sy = p.x + math.cos(a) * 360, p.y + math.sin(a) * 280
            eb_shot(sx, sy, math.atan2(p.y - sy, p.x - sx), 175 if fast else 145, 7, 'gold')
        for k in range(18):
            eb_shot(b.x, b.y, k * math.pi / 9 + b.rot * 1.4, 125, 9, 'aqua')
    elif sig == 9:
        # 赤潮主 · 血浪回卷：三重血潮上下翻卷
        for wave_i in range(3):
            yy = cy0 + H + 30 - wave_i * 120
            for k in range(12):
                xx = cx0 + 60 + k * (W - 120) / 11
                eb_shot(xx, yy, -math.pi / 2 + math.sin(b.t + k) * .04,
                        205 if fast else 175, 7, 'coral')
        for k in range(9):
            eb_shot(b.x, b.y, aim + (k - 4) * .07, 250, 6, 'amber')
    elif sig == 10:
        # 星骸 · 星屑轨道：四道旋臂星屑
        for arm in range(4):
            for k in range(7):
                a = b.rot * 2.7 + arm * math.pi / 2 + k * .11
                eb_shot(b.x, b.y, a, 150 + k * 12, 5, 'white' if k % 2 else 'steel')
        for k in range(6):
            eb_shot(cx0 + rnd(W, 60), cy0 - 20, math.atan2(p.y - cy0, p.x - (cx0 + W / 2)),
                    180, 7, 'violet')
    elif sig == 11:
        # 白洞 · 事件视界：三圈反向视界，中心强引力
        for ri, spd in ((0, 300), (1, 220), (2, 155)):
            n = 24 + ri * 5
            for k in range(n):
                a = k * math.pi * 2 / n + b.rot * (1 if ri % 2 == 0 else -1)
                eb_shot(b.x, b.y, a, spd, 6, 'white' if ri == 0 else 'aqua')
        G.well = {'x': b.x, 'y': b.y, 'r': 230, 't': 2.2, 'max': 2.2, 'ang': 0, 'pull': 70}
    elif sig == 12:
        # 霓虹主 · 霓虹囚笼：上下左右交错的霓虹网格
        for k in range(12):
            xx = cx0 + 40 + k * (W - 80) / 11
            eb_shot(xx, cy0 - 20, math.pi / 2, 190, 5, 'violet')
            yy = cy0 + 50 + k * (H - 100) / 11
            eb_shot(cx0 + W + 20, yy, math.pi, 190, 5, 'aqua')
        for k in range(10):
            eb_shot(b.x, b.y, aim + (k - 4.5) * .06, 275, 5, 'white')
    elif sig == 13:
        # 灰烬王 · 王座余烬：王座周围连续燃起五片火域
        for k in range(5):
            a = k * math.pi * 2 / 5 + b.rot
            G.fires.append({'x': b.x + math.cos(a) * 210, 'y': b.y + math.sin(a) * 150,
                            'r': 105, 't': 2.5, 'max': 2.5, 'col': 'amber'})
        for k in range(20):
            eb_shot(b.x, b.y, k * math.pi / 10 + b.rot, 160 if fast else 135, 7, 'coral')
        G.shake = max(G.shake, 12)
    elif sig == 14:
        # 终焉 · 审判日：六发巨型审判弹 + 天顶落雷
        for k in range(6):
            eb_shot(b.x, b.y + 40, aim + (k - 2.5) * .055, 385, 10, 'gold')
        for k in range(12):
            eb_shot(p.x + rnd(280, -280), cy0 - 20, math.pi / 2, 220, 8, 'white')
        G.flashv = max(G.flashv, .35)
    elif sig == 15:
        # 虚空花母 · 孢子云：漫天花粉与孢囊
        for k in range(26):
            a = rnd(math.pi * 2)
            eb_shot(b.x, b.y, a, 110 + rnd(70), rnd(12, 7), 'green')
        for k in range(3):
            G.enemies.append(Enemy('voidling' if 'voidling' in EKIND else 'spark',
                                   b.x + rnd(180, -180), b.y + rnd(60, 0),
                                   G.run.layer, G.run.wave, scale_hp=False))
    elif sig == 16:
        # 时骸 · 时间倒带：玩家短暂变慢，四向迟滞弹回收
        p.slow_t = max(getattr(p, 'slow_t', 0), 1.2)
        for k in range(4):
            a = k * math.pi / 2 + b.rot
            sx, sy = p.x + math.cos(a) * 300, p.y + math.sin(a) * 230
            eb_shot(sx, sy, math.atan2(p.y - sy, p.x - sx), 235, 7, 'steel')
        for k in range(18):
            eb_shot(p.x + rnd(240, -240), p.y + rnd(180, -180), rnd(math.pi * 2), 90, 5, 'aqua')
    elif sig == 17:
        # 深渊之底 · 触手收网：四边触手同时向内收
        for side in range(4):
            for k in range(6):
                if side == 0:
                    sx, sy, ang = cx0 - 20, cy0 + 80 + k * 140, 0
                elif side == 1:
                    sx, sy, ang = cx0 + W + 20, cy0 + 80 + k * 140, math.pi
                elif side == 2:
                    sx, sy, ang = cx0 + 100 + k * 170, cy0 - 20, math.pi / 2
                else:
                    sx, sy, ang = cx0 + 100 + k * 170, cy0 + H + 20, -math.pi / 2
                eb_shot(sx, sy, ang, 180 if fast else 150, 7, 'green')
        for k in range(10):
            eb_shot(b.x, b.y, aim + (k - 4.5) * .08, 265, 5, 'coral')
    elif sig == 18:
        # 星墓主 · 墓碑阵列：三排墓碑从上方压下
        for row in range(3):
            for k in range(10):
                sx = cx0 + 80 + k * (W - 160) / 9 + row * 28
                sy = cy0 - 20 - row * 55
                eb_shot(sx, sy, math.pi / 2 + math.sin(b.t + k) * .05,
                        175 if fast else 145, 8, 'steel' if row == 1 else 'violet')
        G.well = {'x': p.x, 'y': p.y, 'r': 190, 't': 2.0, 'max': 2.0, 'ang': 0, 'pull': 80}
    elif sig == 19:
        # 熔核巨像 · 地脉喷涌：五道地脉火柱 + 岩浆反喷
        for dx in (-300, -150, 0, 150, 300):
            G.fires.append({'x': clamp(p.x + dx, cx0 + 40, cx0 + W - 40), 'y': p.y + 20,
                            'r': 95, 't': 2.8, 'max': 2.8, 'col': 'amber'})
        for k in range(18):
            eb_shot(p.x + rnd(260, -260), cy0 + H + 20, -math.pi / 2,
                    190 if fast else 160, 7, 'amber')
        G.shake = max(G.shake, 15)
    elif sig == 20:
        # 回廊尽头 · 闭门：四面门板向中心合拢
        for side in range(4):
            for k in range(9):
                if side < 2:
                    sx, sy = (cx0 - 20 if side == 0 else cx0 + W + 20), cy0 + 60 + k * 100
                    ang = 0 if side == 0 else math.pi
                else:
                    sx, sy = cx0 + 80 + k * (W - 160) / 8, (cy0 - 20 if side == 2 else cy0 + H + 20)
                    ang = math.pi / 2 if side == 2 else -math.pi / 2
                eb_shot(sx, sy, ang, 200 if fast else 165, 7, 'gold')
        for k in range(8):
            eb_shot(b.x, b.y, aim + (k - 3.5) * .09, 300, 5, 'white')
    elif sig == 21:
        # 静默观测者 · 零声场：压制技能冷却，同时放出无声弹幕
        p.skill_t = max(p.skill_t, 3.5)
        for k in range(20):
            a = k * math.pi / 10 + b.rot
            eb_shot(b.x, b.y, a, 170 if fast else 145, 5, 'aqua')
        for k in range(8):
            eb_shot(b.x, b.y, aim + (k - 3.5) * .04, 340, 4, 'white')
    elif sig == 22:
        # 铸世者 · 重锻：三圈锻锤冲击波与铁砧火域
        for ri, spd in ((0, 310), (1, 235), (2, 165)):
            n = 22 + ri * 5
            for k in range(n):
                eb_shot(b.x, b.y, k * math.pi * 2 / n + b.rot * .7, spd, 8,
                        'gold' if ri == 0 else 'amber')
        G.fires.append({'x': b.x, 'y': b.y, 'r': 190, 't': 2.4, 'max': 2.4, 'col': 'amber'})
        G.shake = max(G.shake, 18)
    elif sig == 23:
        # 门后的东西 · 门扉倒影：四角门影各射出一组倒影弹
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            sx = cx0 + W / 2 + dx * W / 2
            sy = cy0 + H / 2 + dy * H / 2
            for k in range(4):
                eb_shot(sx, sy, math.atan2(p.y - sy, p.x - sx) + (k - 1.5) * .05,
                        245, 6, 'violet' if k % 2 else 'white')
        for k in range(3):
            G.enemies.append(Enemy('voidling' if 'voidling' in EKIND else 'spark',
                                   b.x + rnd(180, -180), b.y + rnd(60, 0),
                                   G.run.layer, G.run.wave, scale_hp=False))
        G.flashv = max(G.flashv, .22)
    else:
        for k in range(20):
            eb_shot(b.x, b.y, k * math.pi / 10 + b.rot, 190, 7, 'white')
    if ph == 3:
        # 第三阶段追加一圈专属色弹，第二绝技本身也随阶段增强
        for k in range(14):
            eb_shot(b.x, b.y, k * math.pi / 7 + b.rot * 1.3, 225, 6, b.cfg['col'])


def hit_boss(dmg, x, y, crit=False):
    b = G.boss
    if not b or b.dying:
        return
    st = G.run.st if G.run else None
    if st and st['bossbane'] > 0:
        dmg *= 1 + .25 * st['bossbane']
    b.hp -= dmg
    b.flash = .08
    G.run.score += 3
    particle(x, y, 3 if not crit else 6, b.cfg['col'], 140, 18, .3)
    if b.hp <= 0:
        b.hp = 0
        boss_die()


def boss_die():
    b = G.boss
    b.dying = True
    b.die_t = 0
    G.shake = 24
    G.flashv = .7
    G.eb = []
    G.run.score += int(1200 * (1 + (G.run.layer - 1) * .3) * G.run.score_mult)
    AUD.play('big', 1.0)


def update_well(dt):
    w = G.well
    if not w:
        return
    w['t'] -= dt
    if w['t'] <= 0:
        ring(w['x'], w['y'], 20, w['r'] * 1.7, 'violet', .55, 4)
        G.well = None
        return
    w['ang'] += dt * 3.4
    k = w['t'] / w['max']
    rr = w['r'] * (.55 + .45 * k)
    lim = rr * 1.9
    for e in G.enemies:
        if e.dead:
            continue
        dx, dy = w['x'] - e.x, w['y'] - e.y
        d = math.hypot(dx, dy) + .01
        if d < lim:
            pull = 1 - d / lim
            e.x += dx / d * 230 * pull * dt
            e.y += dy / d * 230 * pull * dt
            if d < rr * .6:
                e.hp -= 3.4 * G.run.st['dmg'] * dt
                e.flash = max(e.flash, .05)
                if random.random() < .05:
                    particle(e.x, e.y, 1, 'violet', 60, 12, .3)
    for e in list(G.enemies):
        if not e.dead and e.hp <= 0:
            kill_enemy(e)


def update_boss(dt):
    b = G.boss
    if not b:
        return
    p = G.player
    b.t += dt
    b.rot += dt * .55
    if b.flash > 0:
        b.flash -= dt

    if b.dying:
        b.die_t += dt
        b.y += 10 * dt
        if random.random() < .55:
            a = rnd(6.28)
            d = rnd(b.r * 1.2)
            particle(b.x + math.cos(a) * d, b.y + math.sin(a) * d, 5, b.cfg['col'], 240, 30, .6)
        if b.die_t > .5 and random.random() < .4:
            AUD.play('kill', .6)
        if b.die_t > 1.8:
            ring(b.x, b.y, 20, 1100, 'white', 1.2, 5)
            G.shake = 26
            G.boss = None
            G.cam_lock = None
            finish_boss()
        return

    if b.enter:
        b.y = lerp(b.y, G.camy + 154, dt * 2.3)
        if b.y > G.camy + 148:
            b.enter = False
        return

    b.x = G.camx + W / 2 + math.sin(b.t * .44) * min(W * .2, 230)
    b.y = G.camy + 154 + math.sin(b.t * .9) * 15

    np = 1 if b.hp > b.maxhp * .66 else (2 if b.hp > b.maxhp * .33 else 3)
    if np != b.phase:
        b.phase = np
        b.sig_seen = False
        b.sig2_seen = False
        if np == 2:
            b.sig2_t = min(b.sig2_t, 3.0)
        if np == 3:
            b.rage_t = 10.0
        G.shake = max(G.shake, 14)
        ring(b.x, b.y, 20, 700, b.cfg['col'], .8, 3)
        AUD.play('skill', .8)
        toast('BOSS 进入第 %d 阶段' % np, 'amber')

    b.sig_t -= dt
    if b.sig_t <= 0:
        b.sig_t = max(2.9, 9.0 - b.phase * 1.35) / b.atkspd
        boss_signature(b)
        if not b.sig_seen:
            b.sig_seen = True
            toast('绝技 · %s' % b.sig_name, 'gold')
            AUD.play('skill', .55)

    # 第二绝技在第 2 阶段解锁，第 3 阶段更频繁
    b.sig2_t -= dt
    if b.phase >= 2 and b.sig2_t <= 0:
        b.sig2_t = max(4.2, 8.6 - b.phase * 1.1) / b.atkspd
        boss_signature2(b)
        if not b.sig2_seen:
            b.sig2_seen = True
            toast('第二绝技 · %s' % b.sig2_name, 'coral')
            AUD.play('skill', .7)

    # 第三阶段：双绝技连携
    if b.phase == 3:
        b.rage_t -= dt
        if b.rage_t <= 0:
            b.rage_t = 18.0 / b.atkspd
            toast('狂怒 · 双绝技同奏', 'gold')
            boss_signature(b)
            boss_signature2(b)
            G.shake = max(G.shake, 12)

    b.fire_t -= dt
    if b.fire_t > 0:
        return
    fast = b.phase == 3
    aim = math.atan2(p.y - b.y, p.x - b.x)
    b.pattern_t += .12

    if b.pattern == 0:
        if b.pattern_t % 3 < 1.7:
            arms = 3 + (b.phase - 1)
            for k in range(arms):
                a = b.rot * 2.2 + k * math.pi * 2 / arms
                eb_shot(b.x + math.cos(a) * b.r * .55, b.y + math.sin(a) * b.r * .55,
                        a, 272 if fast else 236, 6, 'amber')
            b.fire_t = .09 if fast else .12
        else:
            n = 26 + b.phase * 6
            for k in range(n):
                a = k * math.pi * 2 / n + b.t * .3
                eb_shot(b.x, b.y, a, 196, 7, 'coral')
            b.fire_t = 1.1 if fast else 1.5
    elif b.pattern == 1:
        if b.pattern_t % 4 < 2.4:
            swing = math.sin(b.t * 2.2) * .9
            for k in (-1, 0, 1):
                eb_shot(b.x, b.y + 20, aim + swing * .5 + k * .16, 258, 6, 'violet')
            b.fire_t = .18 if fast else .26
        else:
            n = 20 + b.phase * 4
            for k in range(n):
                a = k * math.pi * 2 / n + b.rot
                eb_shot(b.x, b.y, a, 176, 8, 'coral')
            b.fire_t = 1.2 if fast else 1.7
    elif b.pattern == 2:
        if b.pattern_t % 5 < 3:
            n = 7 + b.phase * 2
            for k in range(n):
                a = aim + (k - (n - 1) / 2) * .11
                eb_shot(b.x, b.y + 26, a, 246, 7, 'coral')
            b.fire_t = .22 if fast else .34
        else:
            if len(G.enemies) < 9:
                for k in range(2 + b.phase):
                    G.enemies.append(Enemy('spark', b.x + rnd(60, -60), b.y + rnd(30, -10),
                                           G.run.layer, G.run.wave, scale_hp=False))
            b.fire_t = 1.4
    elif b.pattern == 3:
        if b.pattern_t % 6 < 4.2:
            for s in (-1, 1):
                a = b.rot * (2.6 if s > 0 else -2.2) + math.sin(b.t * .7) * .3
                eb_shot(b.x + s * b.r * .5, b.y, a, 208, 7, 'green')
                eb_shot(b.x + s * b.r * .5, b.y, a + .16, 208, 7, 'green')
            b.fire_t = .17 if fast else .21
        else:
            n = 5 + b.phase * 2
            for k in range(n):
                a = aim + (k - (n - 1) / 2) * .075
                eb_shot(b.x, b.y + 18, a, 322, 5, 'aqua')
            b.fire_t = .85 if fast else 1.1
    elif b.pattern == 4:
        if b.pattern_t % 7 < 2.2:
            n = 30 + b.phase * 8
            for k in range(n):
                a = k * math.pi * 2 / n + b.t * .2
                da = abs((a - aim + math.pi) % (math.pi * 2) - math.pi)
                if da < .58:
                    continue
                eb_shot(b.x, b.y, a, 172, 7, 'white' if k % 3 == 0 else 'violet')
            b.fire_t = 1.1 if fast else 1.55
        elif b.pattern_t % 7 < 4.6:
            for k in range(4):
                a = b.rot * 3.4 + k * math.pi / 2
                for j in range(3):
                    eb_shot(b.x + math.cos(a) * b.r * .7, b.y + math.sin(a) * b.r * .7,
                            a + j * .12, 252, 6, 'coral')
            b.fire_t = .11 if fast else .15
        else:
            if len(G.enemies) < 10:
                for k in range(2):
                    ek = 'charger' if k % 2 == 0 else 'weaver'
                    G.enemies.append(Enemy(ek, b.x + rnd(90, -90), b.y + rnd(30, -10),
                                           G.run.layer, G.run.wave, scale_hp=False))
            b.fire_t = 1.7
    elif b.pattern == 5:
        if b.pattern_t % 8 < 3.0:
            n = 16 + b.phase * 4
            for k in range(n):
                a = -b.rot * 2.8 + k * math.pi * 2 / n
                eb_shot(b.x, b.y, a, 232, 7, 'aqua')
            for k in range(n):
                a = b.rot * 2.8 + k * math.pi * 2 / n
                eb_shot(b.x, b.y, a, 160, 9, 'steel')
            b.fire_t = .55 if fast else .8
        elif b.pattern_t % 8 < 5.6:
            for k in range(3 + b.phase):
                a = aim + (k - (2 + b.phase) / 2) * .12
                eb_shot(b.x, b.y + 20, a, 300, 6, 'coral')
            b.fire_t = .2 if fast else .28
        else:
            n = 22 + b.phase * 6
            for k in range(n):
                a = k * math.pi * 2 / n + b.rot * 1.6
                eb_shot(b.x, b.y, a, 138, 10, 'aqua' if k % 2 else 'violet')
            if len(G.enemies) < 11:
                for k in range(2):
                    G.enemies.append(Enemy('sniper' if k else 'spinner',
                                           b.x + rnd(120, -120), b.y + rnd(40, -20),
                                           G.run.layer, G.run.wave, scale_hp=False))
            b.fire_t = 1.3
    elif b.pattern == 6:
        # 蚀骨者：双螺旋 + 扇形封路
        if b.pattern_t % 6 < 3.6:
            n = 12 + b.phase * 2
            for k in range(n):
                a = b.rot * 3.0 + k * math.pi * 2 / n
                eb_shot(b.x, b.y, a, 216, 6, 'green')
                eb_shot(b.x, b.y, -a * 1.0 + .2, 176, 8, 'amber')
            b.fire_t = .28 if fast else .38
        else:
            n = 6 + b.phase * 2
            for k in range(n):
                a = aim + (k - (n - 1) / 2) * .09
                eb_shot(b.x, b.y + 24, a, 288, 6, 'coral')
            b.fire_t = .4 if fast else .6
    elif b.pattern == 7:
        # 零号守卫：四向十字旋转 + 环形脉冲
        if b.pattern_t % 5 < 3.2:
            for k in range(4):
                a = b.rot * 2.2 + k * math.pi / 2
                for j in range(4):
                    eb_shot(b.x + math.cos(a) * b.r * .6, b.y + math.sin(a) * b.r * .6,
                            a, 190 + j * 46, 5, 'steel')
            b.fire_t = .12 if fast else .16
        else:
            n = 20 + b.phase * 6
            for k in range(n):
                a = k * math.pi * 2 / n + b.rot * .7
                eb_shot(b.x, b.y, a, 150, 9, 'white' if k % 4 == 0 else 'violet')
            if len(G.enemies) < 9:
                G.enemies.append(Enemy('spinner', b.x + rnd(100, -100), b.y + rnd(30, -10),
                                       G.run.layer, G.run.wave, scale_hp=False))
            b.fire_t = 1.1
    else:
        # 回廊之核：三层反向环 + 追踪长矛 + 召唤
        if b.pattern_t % 7 < 3.4:
            for layer_i, spd in ((0, 132), (1, 196), (2, 258)):
                n = 18 + b.phase * 3
                for k in range(n):
                    a = k * math.pi * 2 / n + b.rot * (1 if layer_i % 2 == 0 else -1) * 1.3
                    eb_shot(b.x, b.y, a, spd, 7 if layer_i < 2 else 5,
                            'gold' if layer_i == 2 else ('aqua' if layer_i else 'violet'))
            b.fire_t = .9 if fast else 1.3
        elif b.pattern_t % 7 < 5.2:
            for k in range(3 + b.phase):
                a = aim + (k - (2 + b.phase) / 2) * .1
                eb_shot(b.x, b.y + 20, a, 340, 6, 'coral')
            b.fire_t = .18 if fast else .26
        else:
            if len(G.enemies) < 11:
                for k in range(3):
                    ek = 'sniper' if k == 0 else ('weaver' if k == 1 else 'bulwark')
                    G.enemies.append(Enemy(ek, b.x + rnd(140, -140), b.y + rnd(40, -20),
                                           G.run.layer, G.run.wave, scale_hp=False))
            for k in range(10):
                a = k * math.pi / 5 + b.rot
                for j in range(3):
                    eb_shot(b.x + math.cos(a) * b.r, b.y + math.sin(a) * b.r,
                            a + j * .1, 210, 6, 'green')
            b.fire_t = 1.2
    # 统一放缓弹幕节奏；层数越高攻击节奏越快（线性）
    b.fire_t *= 1.35 / b.atkspd


# ================================================================
#  掉落
# ================================================================
DROP_INFO = {'heal': ('修复', 'green'), 'shield': ('护盾', 'aqua'), 'od': ('过载', 'amber')}


def update_drops(dt):
    p = G.player
    for d in G.drops:
        d['t'] += dt
        d['y'] += d['vy'] * dt
        d['x'] += math.sin(d['t'] * 2.2) * 30 * dt
        if p and dist2((d['x'], d['y']), (p.x, p.y)) < (G.run.st['pick']) ** 2:
            G.run.pickups += 1
            if G.run.st['pickheal'] > 0 and G.run.pickups % max(6, 12 - 3 * int(G.run.st['pickheal'])) == 0:
                heal_player(1, quiet=True)
                ring(p.x, p.y, 5, 46, 'green', .3, 2)
            if d['kind'] == 'heal':
                heal_player(1)
            elif d['kind'] == 'shield':
                p.shield = min(3, p.shield + 1)
                p.shield_t = max(p.shield_t, 20)
                toast('护盾 +1', 'aqua')
                AUD.play('pick', .8)
            else:
                p.od_t = 8.0
                toast('过载：伤害提升', 'amber')
                AUD.play('pick', .9)
            particle(d['x'], d['y'], 10, DROP_INFO[d['kind']][1], 120, 20, .5)
            if G.run.st['siphon'] > 0:
                p.skill_t -= 1.5 * G.run.st['siphon']
                ring(p.x, p.y, 6, 54, 'steel', .3, 2)
            d['dead'] = True
    G.drops = [d for d in G.drops if not d.get('dead') and d['y'] < G.camy + H + 40]

# -*- coding: utf-8 -*-
# ================================================================
#  运行流程 / 波次 / 卡片
# ================================================================
WAVES_PER_LAYER = 5
# 二十一层不是二十一片海：锈潮、菌沼、熔窟、镜城、冻原、机冢、数据雨、归墟、回廊之核、血潮、星骸、白洞、霓虹雨、灰烬海、终焉之门、虚空花园、时间残骸、深渊之底、星海墓场、熔核、回廊尽头
LAYER_THEME = [
    dict(name='锈潮', en='RUST TIDE', tint=(12, 24, 30), accent='amber',
         motif='rust', amb='bubble', top=(10, 26, 32), bot=(2, 7, 10), line=(78, 126, 132)),
    dict(name='菌沼', en='SPORE MARSH', tint=(8, 30, 22), accent='green',
         motif='fungus', amb='spore', top=(9, 28, 21), bot=(2, 9, 7), line=(62, 132, 92)),
    dict(name='熔窟', en='MAGMA HOLLOW', tint=(30, 16, 10), accent='coral',
         motif='magma', amb='ember', top=(34, 14, 11), bot=(8, 3, 4), line=(158, 74, 44)),
    dict(name='镜城', en='MIRROR CITY', tint=(20, 16, 36), accent='violet',
         motif='mirror', amb='shard', top=(22, 19, 40), bot=(5, 4, 12), line=(98, 86, 158)),
    dict(name='冻原', en='FROST WASTE', tint=(18, 28, 36), accent='steel',
         motif='snow', amb='snow', top=(20, 33, 41), bot=(5, 10, 14), line=(128, 168, 188)),
    dict(name='机冢', en='MACHINE GRAVE', tint=(26, 20, 12), accent='amber',
         motif='mech', amb='spark', top=(27, 22, 13), bot=(6, 5, 3), line=(148, 114, 62)),
    dict(name='数据雨', en='DATA RAIN', tint=(8, 22, 34), accent='aqua',
         motif='data', amb='rain', top=(7, 22, 36), bot=(2, 6, 12), line=(64, 146, 176)),
    dict(name='归墟', en='THE HOLLOW', tint=(20, 12, 26), accent='steel',
         motif='void', amb='dust', top=(19, 13, 27), bot=(4, 3, 8), line=(94, 84, 124)),
    dict(name='回廊之核', en='CORRIDOR CORE', tint=(26, 22, 10), accent='gold',
         motif='core', amb='wave', top=(28, 24, 13), bot=(6, 5, 3), line=(178, 146, 74)),
    dict(name='血潮', en='BLOOD TIDE', tint=(32, 10, 16), accent='coral',
         motif='rust', amb='bubble', top=(38, 9, 15), bot=(9, 2, 5), line=(178, 62, 82)),
    dict(name='星骸', en='STAR WRAITH', tint=(12, 18, 34), accent='steel',
         motif='mirror', amb='shard', top=(11, 22, 40), bot=(2, 5, 13), line=(92, 136, 194)),
    dict(name='白洞', en='WHITE HOLE', tint=(34, 31, 40), accent='white',
         motif='core', amb='dust', top=(39, 36, 45), bot=(10, 9, 17), line=(204, 198, 224)),
    dict(name='霓虹雨', en='NEON RAIN', tint=(28, 8, 30), accent='violet',
         motif='data', amb='rain', top=(36, 8, 36), bot=(9, 2, 11), line=(196, 62, 178)),
    dict(name='灰烬海', en='ASHEN SEA', tint=(28, 24, 20), accent='amber',
         motif='magma', amb='ember', top=(35, 29, 23), bot=(9, 7, 6), line=(174, 144, 104)),
    dict(name='终焉之门', en='FINAL GATE', tint=(32, 28, 14), accent='gold',
         motif='core', amb='wave', top=(41, 36, 20), bot=(10, 8, 4), line=(230, 198, 116)),
    dict(name='虚空花园', en='VOID GARDEN', tint=(20, 30, 22), accent='green',
         motif='fungus', amb='spore', top=(25, 38, 30), bot=(5, 10, 8), line=(104, 168, 118)),
    dict(name='时间残骸', en='TIME WRECK', tint=(24, 24, 28), accent='steel',
         motif='mech', amb='shard', top=(31, 29, 34), bot=(8, 7, 10), line=(148, 136, 168)),
    dict(name='深渊之底', en='ABYSS FLOOR', tint=(34, 12, 10), accent='coral',
         motif='void', amb='dust', top=(42, 16, 12), bot=(10, 4, 3), line=(208, 116, 76)),
    dict(name='星海墓场', en='STAR GRAVE', tint=(10, 14, 30), accent='steel',
         motif='mirror', amb='shard', top=(12, 18, 38), bot=(2, 4, 12), line=(104, 128, 196)),
    dict(name='熔核', en='MOLTEN CORE', tint=(36, 12, 4), accent='amber',
         motif='magma', amb='ember', top=(44, 14, 6), bot=(12, 4, 2), line=(238, 132, 52)),
    dict(name='回廊尽头', en='CORRIDOR END', tint=(26, 24, 18), accent='gold',
         motif='core', amb='dust', top=(38, 34, 24), bot=(9, 8, 5), line=(236, 206, 130)),
    dict(name='静默深空', en='SILENT VOID', tint=(8, 10, 26), accent='violet',
         motif='void', amb='dust', top=(9, 12, 32), bot=(2, 3, 10), line=(86, 92, 172)),
    dict(name='创世熔炉', en='GENESIS FORGE', tint=(38, 32, 14), accent='gold',
         motif='core', amb='spark', top=(46, 40, 20), bot=(12, 9, 4), line=(255, 222, 140)),
    dict(name='门后', en='BEYOND THE GATE', tint=(34, 30, 34), accent='white',
         motif='mirror', amb='shard', top=(44, 40, 48), bot=(12, 10, 16), line=(232, 220, 244)),
    dict(name='盐霜圣堂', en='SALT CATHEDRAL', tint=(28, 34, 38), accent='steel',
         motif='snow', amb='snow', top=(36, 44, 48), bot=(9, 14, 17), line=(176, 206, 212)),
    dict(name='齿轮海沟', en='GEAR TRENCH', tint=(30, 24, 16), accent='amber',
         motif='mech', amb='spark', top=(38, 30, 18), bot=(9, 7, 4), line=(208, 154, 82)),
    dict(name='虚数潮', en='IMAGINARY TIDE', tint=(24, 12, 34), accent='violet',
         motif='data', amb='rain', top=(31, 14, 43), bot=(7, 3, 13), line=(170, 92, 220)),
    dict(name='终末之眼', en='FINAL EYE', tint=(36, 31, 28), accent='white',
         motif='core', amb='wave', top=(48, 40, 34), bot=(13, 10, 8), line=(255, 236, 194)),
]

# 每一层一张专属氛围文案：开场卡、地标铭牌与图鉴共用
ZONE_TAGS = [
    ('铁锈的潮汐吞没了第一支舰队', 'The rust tide swallowed the first fleet.'),
    ('菌丝在黑暗里铺成呼吸的森林', 'Mycelium breathes into a forest in the dark.'),
    ('熔岩把旧日航道烧成金色裂缝', 'Lava veins the old lanes in gold.'),
    ('每一面镜子都记得另一个你', 'Every mirror remembers another you.'),
    ('冰层下封着没有名字的祷词', 'Nameless prayers are sealed beneath the ice.'),
    ('巨械的骨头仍在缓慢转动', 'The bones of titans still turn, slowly.'),
    ('数据化作雨，落在无人读取的碑上', 'Data falls as rain on unread stelae.'),
    ('归墟没有底，只有更轻的沉默', 'The Hollow has no floor, only lighter silence.'),
    ('回廊的心脏在一圈圈地苏醒', "The corridor's heart wakes ring by ring."),
    ('血潮把海染成会疼痛的红', 'The blood tide stains the sea a hurting red.'),
    ('星骸在黑暗里拼出死去的地图', 'Star wrecks assemble dead maps in the dark.'),
    ('白洞吐出的光，比黑夜更冷', 'Light spat from the white hole is colder than night.'),
    ('霓虹雨冲刷着不会睡去的城', 'Neon rain washes a city that never sleeps.'),
    ('灰烬的海面下，火焰仍有余温', 'Beneath the ashen sea, embers still hold warmth.'),
    ('终焉之门只对回声敞开', 'The final gate opens only to echoes.'),
    ('虚空花园里，花以记忆为土壤', 'In the void garden, flowers root in memory.'),
    ('时间的残骸卡在每一秒之间', 'Wreckage of time wedges between every second.'),
    ('深渊之底不是终点，是胃', 'The abyss floor is not an end. It is a stomach.'),
    ('星海墓场里，光年只是墓碑的间距', 'In the star grave, light-years are grave spacing.'),
    ('熔核仍在替整座回廊心跳', 'The molten core still beats for the corridor.'),
    ('回廊尽头，门后还有门', "At the corridor's end, one more door."),
    ('静默深空，连回声也被吞掉', 'Silent void swallows even echoes.'),
    ('创世熔炉把失败锻成下一次下潜', 'The genesis forge tempers failure into the next dive.'),
    ('门后不是彼岸，是另一层海', 'Beyond the gate is not shore, but another sea.'),
    ('盐霜圣堂的钟声已经冻住', 'The bells of the salt cathedral froze mid-toll.'),
    ('齿轮海沟咬合着整片大陆', 'The gear trench meshes an entire continent.'),
    ('虚数潮里，数字长出了鳍', 'In the imaginary tide, numbers grow fins.'),
    ('终末之眼睁开时，回廊学会了凝视', 'When the final eye opens, the corridor learns to stare.'),
]

LANDMARK_NAMES = [
    ('沉船圣骸', 'THE SUNKEN RELIC'), ('孢子母树', 'THE MOTHER BLOOM'),
    ('熔心王座', 'THE MAGMA THRONE'), ('倒影之门', 'THE MIRROR GATE'),
    ('霜葬教堂', 'THE FROST CATHEDRAL'), ('泰坦坟场', 'TITAN BONEYARD'),
    ('雨塔', 'THE RAIN SPIRE'), ('归墟之眼', 'THE HOLLOW EYE'),
    ('回廊核心', 'THE CORRIDOR CORE'), ('血潮心脏', 'THE BLOOD HEART'),
    ('星骸王座', 'THE WRAITH THRONE'), ('白洞祭坛', 'THE WHITE ALTAR'),
    ('霓虹钟楼', 'THE NEON BELFRY'), ('灰烬巨船', 'THE ASHEN ARK'),
    ('终焉门扉', 'THE FINAL DOOR'), ('虚空花冠', 'THE VOID CROWN'),
    ('时之残骸', 'THE TIME WRECK'), ('深渊之口', 'THE ABYSS MAW'),
    ('星墓', 'THE STAR TOMB'), ('熔核炉心', 'THE MOLTEN HEART'),
    ('回廊尽头之门', 'THE LAST GATE'), ('静默方尖碑', 'THE SILENT OBELISK'),
    ('创世熔炉', 'THE GENESIS FORGE'), ('门后圣所', 'THE SANCTUM BEYOND'),
    ('盐霜圣堂', 'THE SALT CATHEDRAL'), ('齿轮圣像', 'THE GEAR IDOL'),
    ('虚数之鲸', 'THE IMAGINARY WHALE'), ('终末之眼', 'THE FINAL EYE'),
]


def zone_tag(layer):
    return ZONE_TAGS[(max(1, int(layer)) - 1) % len(ZONE_TAGS)]


def landmark_name(layer):
    return LANDMARK_NAMES[(max(1, int(layer)) - 1) % len(LANDMARK_NAMES)]


_THEME_VARIANTS = {}
_THEME_SUFFIX = ['回响', '余烬', '逆潮', '深潜', '耳鸣']


def theme_of(layer):
    layer = max(1, int(layer))
    n = len(LAYER_THEME)
    if layer <= n:
        return LAYER_THEME[layer - 1]
    idx = (layer - 1) % n
    cyc = (layer - 1) // n
    key = (idx, cyc)
    v = _THEME_VARIANTS.get(key)
    if v:
        return v
    base = LAYER_THEME[idx]
    v = dict(base)
    v['name'] = base['name'] + '·' + _THEME_SUFFIX[(cyc - 1) % len(_THEME_SUFFIX)]
    v['en'] = base['en'] + ' //' + str(cyc + 1)
    v['accent'] = LAYER_THEME[(idx + cyc * 5) % n]['accent']
    shift = (cyc * 11) % 40
    v['tint'] = tuple(min(80, c + shift) for c in base['tint'])
    v['top'] = tuple(min(90, c + shift) for c in base['top'])
    v['bot'] = tuple(min(60, c + shift // 2) for c in base['bot'])
    v['line'] = tuple(min(255, c + shift) for c in base['line'])
    _THEME_VARIANTS[key] = v
    return v


def new_run(ship_id, slot=None, count_run=True, from_load=False, quiet=False):
    if slot is not None:
        G.save_slot = int(slot)
    if G.profile is None:
        if slot is not None:
            G.profile = slot_profile(slot) or new_slot_profile()
        else:
            G.profile = blank_profile()
    G.profile = normalize_profile(G.profile)
    ship = ship_by_id(ship_id)
    daily_seed = None
    if MODES[G.mode].get('daily'):
        daily_seed = int(time.strftime('%Y%m%d')) & 0xFFFFFF
        random.seed(daily_seed)
    G.ww, G.wh = world_of(1)
    G.run = Run(ship)
    if not from_load:
        apply_ship_identity(G.run)
    G.player = Player(ship, G.run)
    G.camx = clamp(G.player.x - W / 2, 0, G.ww - W)
    G.camy = clamp(G.player.y - H / 2, 0, G.wh - H)
    G.cam_lock = None
    G.fires = []
    build_ambient(1)
    G.enemies = []
    G.pb = []
    G.eb = []
    G.parts = []
    G.drops = []
    G.drones = []
    G.beams = []
    G.well = None
    G.boss = None
    G.queue = []
    G.cards = []
    G.shake = 0
    G.slow_t = 0
    G.time = 0
    G.win = False
    G.dead_t = 0
    G.scene = 'play'
    G.t = 0
    G.combo = 0
    G.combo_t = 0
    G.combo_best = 0
    G.banner2 = None
    G.wave_tag = ''
    if not quiet:
        if META.get('runs', 0) <= 1:
            toast('首次下潜：WASD 移动 · 鼠标瞄准 · 自动开火 · 空格技能 · ESC 暂停后可看说明', 'aqua')
        elif G.joy:
            toast('手柄已连接：右摇杆瞄准 · A / RT 技能 · Y 自动索敌', 'gold')
    # ---- 本局回廊事件 ----
    mut = dict(random.choice(MUTS))
    G.run.mut = mut
    G.run.boss_off = random.randint(0, len(BOSSCFG) - 1)
    if daily_seed is not None:
        G.run.seed = daily_seed
    else:
        G.run.seed = random.randint(0, 0xFFFFFF)
    ev0 = roll_layer_event(1)
    st = G.run.st
    if mut.get('dmg'):
        st['dmg'] *= mut['dmg']
    if mut.get('cd'):
        st['cd'] *= mut['cd']
    if mut.get('speed'):
        st['speed'] *= mut['speed']
    if mut.get('rate'):
        st['rate'] *= mut['rate']
    if mut.get('maxhp'):
        G.run.max_hp = max(2, G.run.max_hp + mut['maxhp'])
        G.run.hp = G.run.max_hp
        G.player.max_hp = G.run.max_hp
        G.player.hp = G.run.hp
    if mut.get('regen'):
        st['regen'] = max(1, st['regen'])
    for i in range(int(G.run.st['drone'])):
        spawn_drone(i, True)
    if mut.get('start_aug'):
        a = random.choice(AUGS)
        G.run.take(a)
        G.player.max_hp = G.run.max_hp
        G.player.hp = min(G.run.max_hp, G.player.hp + 1)
        if a[4] == 'drone':
            spawn_drone(len(G.drones), True)
        G.start_aug_name = a[1]
    # ---- 回声工坊：跨局永久升级，在新一局开始时结算 ----
    lv_hull = upg_level('hull')
    if lv_hull:
        G.run.max_hp += lv_hull
        G.run.hp = G.run.max_hp
    lv_gun = upg_level('gun')
    if lv_gun:
        st['dmg'] *= 1.07 ** lv_gun
    lv_mag = upg_level('magnet')
    if lv_mag:
        st['pick'] *= 1.18 ** lv_mag
    lv_cool = upg_level('cool')
    if lv_cool:
        st['cd'] *= .94 ** lv_cool
    lv_sal = upg_level('salvage')
    if lv_sal:
        G.run.mut['drop'] = G.run.mut.get('drop', 1.0) * (1.10 ** lv_sal)
    lv_sh = upg_level('shield')
    if lv_sh:
        G.player.shield = max(G.player.shield, min(3, lv_sh))
    if getattr(G.run, 'start_shield', 0):
        G.player.shield = max(G.player.shield, min(3, G.run.start_shield))
    for _ in range(getattr(G.run, 'start_drone', 0)):
        spawn_drone(len(G.drones), True)
    lv_cache = upg_level('cache')
    for _ in range(lv_cache):
        a = random.choice(AUGS)
        G.run.take(a)
        if a[4] == 'drone':
            spawn_drone(len(G.drones), True)
    lv_bane = upg_level('bane')
    if lv_bane:
        st['bossbane'] = st.get('bossbane', 0) + .08 * lv_bane
    # 永久艇体/增幅可能改写了上限，最后统一同步到玩家实体
    G.player.max_hp = G.run.max_hp
    G.player.hp = G.run.max_hp
    if count_run and not from_load:
        META['runs'] = META.get('runs', 0) + 1
        save_meta()
        if G.save_slot is not None and int(G.save_slot) >= 0 and isinstance(G.profile, dict):
            G.profile['runs'] = int(G.profile.get('runs', 0)) + 1
            G.profile['updated'] = _stamp()
            save_profile(int(G.save_slot), G.profile)
        grant_ach('first_dive')
        if MODES[G.mode].get('daily'):
            grant_ach('daily_first')
    start_wave()
    if not from_load:
        AUD.say('start', force=True)
        G.banner2 = {'s': '%s · 本层事件 · %s  %s' % (G.run.mode_name, ev0['name'], ev0['desc']),
                     'col': 'gold', 't': 0, 'life': 2.8}
    if not from_load:
        save_checkpoint(quiet=True)
    layout()


def save_checkpoint(quiet=False):
    """把当前局内进度写进槽文件。保存的是「本波开头」的检查点。"""
    if not G.run or not G.player:
        return False
    if G.save_slot is None or int(G.save_slot) < 0:
        return False
    if G.scene not in ('play', 'pause', 'cards', 'settings', 'codex', 'help', 'lab'):
        return False
    r = G.run
    p = G.player
    profile = normalize_profile(G.profile)
    profile['updated'] = _stamp()
    data = {
        'ver': VERSION,
        'empty': False,
        'ended': False,
        'run_active': True,
        'profile': profile,
        'ship': r.ship['id'],
        'ship_name': r.ship['name'],
        'mode': int(r.mode),
        'diff': int(G.diff),
        'cycle': int(r.cycle),
        'layer': int(r.layer),
        'wave': int(r.wave),
        'seed': int(r.seed),
        'boss_off': int(r.boss_off),
        'mut': r.mut,
        'lmod': r.lmod,
        'max_hp': int(r.max_hp),
        'hp': int(r.hp),
        'st': r.st,
        'augs': r.augs,
        'pacts': list(r.pacts),
        'score': int(r.score),
        'kills': int(r.kills),
        'time': float(r.time),
        'cards_taken': int(r.cards_taken),
        'pickups': int(r.pickups),
        'waves_cleared': int(r.waves_cleared),
        'shards_earned': int(r.shards_earned),
        'start_aug_name': G.start_aug_name,
        'combo_best': int(G.combo_best),
        'px': float(p.x),
        'py': float(p.y),
        'p_hp': int(p.hp),
        'p_max_hp': int(p.max_hp),
        'p_shield': int(p.shield),
        'p_skill_t': float(p.skill_t),
        'p_charge_t': float(p.charge_t),
        'updated': time.strftime('%Y-%m-%d %H:%M'),
    }
    try:
        path = slot_file(G.save_slot)
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        G.profile = profile
        if not quiet:
            toast(L('进度已保存 · 存档槽 %d' % (G.save_slot + 1),
                   'Progress saved · Slot %d' % (G.save_slot + 1)), 'aqua', 2.0)
            AUD.play('pick', .6)
        return True
    except Exception:
        if not quiet:
            toast(L('保存失败：无法写入存档', 'Save failed: could not write slot'), 'coral', 2.0)
        return False


def load_slot(slot):
    d = read_slot(slot)
    if not d:
        return False
    if d.get('ended') or not d.get('run_active'):
        return False
    try:
        G.mode = int(d.get('mode', 0))
        G.diff = int(d.get('diff', 0))
        G.mode = int(clamp(G.mode, 0, len(MODES) - 1))
        G.diff = int(clamp(G.diff, 0, len(DIFFS) - 1))
        G.save_slot = int(slot)
        G.profile = normalize_profile(d.get('profile'))
        new_run(d.get('ship', 'echo'), slot=slot, count_run=False, from_load=True, quiet=True)
        r = G.run
        p = G.player
        r.cycle = int(d.get('cycle', 0))
        r.layer = int(max(1, d.get('layer', 1)))
        r.wave = int(max(1, d.get('wave', 1)))
        r.seed = int(d.get('seed', 0))
        r.boss_off = int(d.get('boss_off', 0))
        r.mut = d.get('mut') if isinstance(d.get('mut'), dict) else r.mut
        r.lmod = d.get('lmod') if isinstance(d.get('lmod'), dict) else r.lmod
        r.max_hp = int(max(2, d.get('max_hp', r.max_hp)))
        r.hp = int(clamp(d.get('hp', r.max_hp), 1, r.max_hp))
        r.score = int(d.get('score', 0))
        r.kills = int(d.get('kills', 0))
        r.time = float(d.get('time', 0))
        r.cards_taken = int(d.get('cards_taken', 0))
        r.pickups = int(d.get('pickups', 0))
        r.waves_cleared = int(d.get('waves_cleared', 0))
        r.shards_earned = int(d.get('shards_earned', 0))
        r.st = default_stats()
        saved_st = d.get('st')
        if isinstance(saved_st, dict):
            for k, v in saved_st.items():
                if isinstance(v, (int, float)):
                    r.st[k] = v
        r.augs = {}
        saved_augs = d.get('augs')
        if isinstance(saved_augs, dict):
            for k, v in saved_augs.items():
                if isinstance(k, str) and isinstance(v, (int, float)):
                    r.augs[k] = int(v)
        r.pacts = []
        saved_pacts = d.get('pacts')
        if isinstance(saved_pacts, list):
            r.pacts = [str(x) for x in saved_pacts if isinstance(x, str)]
        G.start_aug_name = str(d.get('start_aug_name', ''))
        G.combo_best = int(d.get('combo_best', 0))
        G.ww, G.wh = world_of(r.layer)
        p.x = clamp(float(d.get('px', G.ww / 2)), 40, G.ww - 40)
        p.y = clamp(float(d.get('py', G.wh - 170)), 40, G.wh - 40)
        p.max_hp = r.max_hp
        p.hp = int(clamp(d.get('p_hp', r.hp), 1, r.max_hp))
        p.shield = int(max(0, d.get('p_shield', 0)))
        p.skill_t = float(max(0, d.get('p_skill_t', 0)))
        p.charge_t = float(max(0, d.get('p_charge_t', 0)))
        p.inv = 1.2
        G.camx = clamp(p.x - W / 2, 0, G.ww - W)
        G.camy = clamp(p.y - H / 2, 0, G.wh - H)
        build_ambient(r.layer)
        G.drones = []
        for i in range(int(max(0, r.st.get('drone', 0)))):
            spawn_drone(i, True)
        start_wave()
        G.banner2 = None
        G.cards = []
        G.scene = 'play'
        save_checkpoint(quiet=True)
        toast(L('已载入存档槽 %d' % (slot + 1), 'Loaded slot %d' % (slot + 1)), 'gold', 2.2)
        AUD.say('start')
        layout()
        return True
    except Exception as e:
        G.load_error = repr(e)
        return False


def clear_slot(slot):
    """结束一次下潜：清掉局内检查点，但保留这个存档的工坊、结晶和序章状态。"""
    if slot is None or int(slot) < 0:
        return
    d = read_slot(slot)
    if not d:
        return
    p = normalize_profile(d.get('profile'))
    save_profile(int(slot), p, clear_run=True)


def remove_slot(slot):
    """彻底删除一个存档，包括工坊与结晶。"""
    if slot is None or int(slot) < 0:
        return
    try:
        p = slot_file(slot)
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


def first_empty_slot():
    for i in range(SLOT_COUNT):
        if not read_slot(i):
            return i
    return -1


def start_wave():
    G.wave_t = 0
    G.wave_active = True
    G.queue = build_wave(G.run.layer, G.run.wave)
    G.enemies = []
    G.eb = []
    if G.run.wave == waves_for_layer():
        bcfg = boss_pool(G.run.layer)[((G.run.layer - 1) + G.run.boss_off) % len(boss_pool(G.run.layer))]
        bn = bcfg['en'] if META.get('lang') else bcfg['name']
        G.banner = {'s': L('第 %d 层 · %s 接近' % (G.run.layer, bn),
                           'STRATUM %d · %s APPROACHING' % (G.run.layer, bn)),
                    'col': 'coral', 't': 0, 'life': 2.6}
    else:
        tag = (' · ' + G.wave_tag) if G.wave_tag else ''
        cap = layers_for_run()
        total = ('%d' % cap) if cap else '∞'
        G.banner = {'s': '%d / %s 层 · %s · 第 %d 波%s' % (
            G.run.layer, total, theme_of(G.run.layer)['name'], G.run.wave, tag),
                    'col': theme_of(G.run.layer)['accent'], 't': 0, 'life': 2.0}
    if G.run.wave == 1 and G.layer_card_t > 0:
        G.banner = None
    AUD.play('card', .4)
    if G.run.wave == waves_for_layer():
        AUD.say('boss')


def build_wave(layer, wave):
    if wave == waves_for_layer():
        G.wave_tag = ''
        return [(1.3, 'boss', 0, 0)]
    kinds = ['drifter', 'drifter', 'hunter', 'lantern', 'turret', 'spark', 'marc', 'splitter']
    if layer >= 2:
        kinds += ['orbiter', 'charger', 'bulwark', 'bomber']
    if layer >= 3:
        kinds += ['weaver', 'spinner', 'dart']
    if layer >= 4:
        kinds += ['sniper']
    if layer >= 5:
        kinds += ['orb']
    if layer >= 6:
        kinds += ['laser']
    if layer >= 7:
        kinds += ['spawner']
    if layer >= 5:
        kinds += ['sweeper']
    if layer >= 6:
        kinds += ['warden']
    if layer >= 7:
        kinds += ['siphoner']
    if layer >= 8:
        kinds += ['spear']
    if layer >= 9:
        kinds += ['miner']
    if layer >= 10:
        kinds += ['titan']
    if layer >= 9:
        kinds += ['drake']
    if layer >= 10:
        kinds += ['mortar']
    if layer >= 11:
        kinds += ['shade']
    if layer >= 10:
        kinds += ['wisp']
    if layer >= 11:
        kinds += ['webber']
    if layer >= 12:
        kinds += ['juggernaut']
    if layer >= 12:
        kinds += ['lancer']
    if layer >= 13:
        kinds += ['prism']
    if layer >= 13:
        kinds += ['cryo']
    if layer >= 14:
        kinds += ['hive']
    if layer >= 15:
        kinds += ['torch']
    if layer >= 16:
        kinds += ['voidling']
    weight = {'drifter': 3.4, 'hunter': 2.2, 'lantern': 2.0, 'turret': 1.3, 'spark': 1.8,
              'marc': 1.0, 'splitter': 2.0, 'orbiter': 1.8, 'charger': 1.9, 'weaver': 1.4,
              'bulwark': 1.1, 'spinner': 1.2, 'bomber': 1.6, 'sniper': 1.0,
              'dart': 1.5, 'orb': 1.5, 'laser': 1.2, 'spawner': .9,
              'sweeper': 1.2, 'warden': 1.0, 'siphoner': .9,
              'spear': 1.0, 'miner': .9, 'titan': .5,
              'drake': .9, 'mortar': .8, 'shade': .8,
              'wisp': 1.1, 'juggernaut': .55, 'webber': .85,
              'prism': .8, 'hive': .6, 'lancer': .8, 'cryo': .85, 'torch': .8, 'voidling': .9}
    cost = {'drifter': 1.0, 'hunter': 1.4, 'lantern': 1.7, 'turret': 2.4, 'spark': .6,
            'marc': 3.0, 'splitter': 1.7, 'orbiter': 1.8, 'charger': 2.0, 'weaver': 1.9,
            'bulwark': 2.8, 'spinner': 2.1, 'bomber': 1.5, 'sniper': 1.8,
            'dart': 1.6, 'orb': 1.7, 'laser': 2.2, 'spawner': 3.2,
            'sweeper': 2.3, 'warden': 2.8, 'siphoner': 2.2,
            'spear': 2.2, 'miner': 2.4, 'titan': 4.6,
            'drake': 2.6, 'mortar': 2.7, 'shade': 2.5,
            'wisp': 2.0, 'juggernaut': 4.4, 'webber': 2.5,
            'prism': 2.4, 'hive': 3.2, 'lancer': 2.2, 'cryo': 2.5, 'torch': 2.6, 'voidling': 2.3}
    # 随机波次风格：只抽本层已经解锁的敌机风格
    avail_tags = [t for t in WAVE_TAGS if not t['w'] or any(k in kinds for k in t['w'])]
    tag = random.choice(avail_tags) if random.random() < .62 else WAVE_TAGS[0]
    G.wave_tag = tag['name']
    bias = tag['w']
    wt = [weight[k] * (bias.get(k, 1.0) if k in kinds else 1.0) for k in kinds]
    mut = G.run.mut if G.run else {}
    budget = ((5.5 + layer * 1.25 + wave * 1.8) * mut.get('budget', 1.0)
              * (G.run.lmod['budget'] if G.run else 1.0) * DIFFS[G.diff]['budget']
              * mode_of().get('budget', 1.0))
    elitep = (.05 + layer * .035) * mut.get('elite', 1.0)
    ev = []
    used = 0.0
    t = .55
    guard = 0
    while used < budget and t < 11.5 and guard < 60:
        guard += 1
        kind = random.choices(kinds, weights=wt, k=1)[0]
        group = rndint(5, 2) if kind in ('drifter', 'spark') else 1
        elite = (kind != 'spark') and random.random() < elitep
        for i in range(group):
            # 位置在出场时按镜头计算，保证总是从玩家附近压下来
            ev.append((t + i * .13, kind, None, None, bool(elite and i == 0)))
        used += cost[kind] * group
        t += rnd(1.65, .85)
    return ev


def update_wave(dt):
    if not G.wave_active:
        return
    G.wave_t += dt
    while G.queue and G.queue[0][0] <= G.wave_t:
        ev = G.queue.pop(0)
        kind, x, y = ev[1], ev[2], ev[3]
        elite = ev[4] if len(ev) > 4 else False
        if kind == 'boss':
            spawn_boss()
        else:
            x = ev[2] if ev[2] is not None else G.camx + rnd(W - 150, 75)
            if ev[3] is not None:
                y = ev[3]
            else:
                py = G.player.y if G.player else G.camy + H * .5
                y = clamp(py - rnd(H * .62, H * .44), G.camy - 90, G.camy + H * .34)
            G.enemies.append(Enemy(kind, x, y, G.run.layer, G.run.wave, elite=elite))


def wave_cleared():
    G.wave_active = False
    G.run.waves_cleared += 1
    G.banner = None
    open_cards('wave')


def finish_boss():
    G.wave_active = False
    G.run.waves_cleared += 1
    heal_player(2)
    open_cards('boss')


def open_cards(ctx, kind='aug'):
    G.card_kind = kind
    if kind == 'pact':
        G.cards = [pact_card(p) for p in roll_pacts()]
    else:
        G.cards = pack_choice(ctx)
    G.card_ctx = ctx
    G.scene = 'cards'
    G.shake = 0
    AUD.play('card', .9)
    layout()


def choose_card(i):
    if i < 0 or i >= len(G.cards):
        return
    a = G.cards[i]
    # ---- 契约卡：直接写入本局规则，然后继续换层 ----
    if G.card_kind == 'pact':
        p = a[5]
        apply_pact(p)
        toast('契约生效 · ' + a[1], 'gold')
        AUD.play('pick', 1.0)
        G.cards = []
        G.scene = 'play'
        advance_after_boss()
        return
    G.run.take(a)
    if G.run.cards_taken >= 15:
        grant_ach('collector')
    p = G.player
    p.max_hp = G.run.max_hp
    p.hp = min(p.hp, p.max_hp)
    if a[4] == 'drone':
        spawn_drone(len(G.drones), True)
    toast('获得增幅 · ' + a[1], RARITY_COL[a[3]])
    AUD.play('pick', 1.0)
    G.cards = []
    G.scene = 'play'
    ctx = G.card_ctx
    if ctx == 'boss':
        # 契约模式：先拿 BOSS 增幅，再签一份本层契约
        if MODES[G.run.mode].get('pact'):
            open_cards('boss', 'pact')
            return
        advance_after_boss()
    else:
        G.run.wave += 1
        start_wave()
        save_checkpoint(quiet=True)
    layout()


def advance_after_boss():
    """BOSS 增幅 / 契约处理完之后，统一执行换层。"""
    G.run.layer += 1
    cap = layers_for_run()
    if cap is not None and G.run.layer > cap:
        G.run.layer = cap
        win_run()
        return
    p = G.player
    # 换层：更大的新地图、新的环境与镜头
    if G.run.layer > LAYERS:
        cyc = (G.run.layer - 1) // LAYERS
        if cyc > G.run.cycle:
            G.run.cycle = cyc
            grant_ach('cycle1')
            toast('回廊轮回 %d · 主题开始复写' % cyc, 'violet')
    G.ww, G.wh = world_of(G.run.layer)
    p.x = G.ww / 2
    p.y = G.wh - 170
    p.inv = max(p.inv, 1.0)
    G.camx = clamp(p.x - W / 2, 0, G.ww - W)
    G.camy = clamp(p.y - H / 2, 0, G.wh - H)
    G.cam_lock = None
    G.drops = []
    G.fires = []
    build_ambient(G.run.layer)
    AUD.say('layer')
    ev = roll_layer_event(G.run.layer)
    if G.run.layer >= 3:
        grant_ach('deep3')
    if G.run.layer >= 6:
        grant_ach('deep6')
    if G.run.layer >= 9:
        grant_ach('deep9')
    if G.run.layer >= 12:
        grant_ach('deep12')
    if G.run.layer >= 15:
        grant_ach('deep15')
    if G.run.layer >= 18:
        grant_ach('deep18')
    if G.run.layer >= 21:
        grant_ach('deep21')
    if G.run.layer >= 24:
        grant_ach('deep24')
    if G.run.layer >= 28:
        grant_ach('deep28')
    mid = MODES[G.run.mode]['id']
    if mid == 'endless':
        for need in (10, 20, 30, 50, 100):
            if G.run.layer >= need:
                grant_ach('endless%d' % need)
    G.run.wave = 1
    heal_player(1, quiet=True)
    start_wave()
    G.banner2 = {'s': '本层事件 · %s  %s' % (ev['name'], ev['desc']),
                 'col': 'gold', 't': 0, 'life': 2.6}
    save_checkpoint(quiet=True)
    G.card_kind = 'aug'
    layout()


def kill_player():
    if G.scene != 'play':
        return
    p = G.player
    st = G.run.st if G.run else None
    if st and st['revive'] > 0:
        st['revive'] = 0
        p.hp = min(3, max(1, G.run.max_hp))
        p.inv = 3.2
        p.shield = max(p.shield, 1)
        G.eb = []
        ring(p.x, p.y, 14, 320, 'gold', 1.0, 5)
        ring(p.x, p.y, 8, 160, 'white', .7, 3)
        particle(p.x, p.y, 30, 'gold', 230, 30, .8)
        G.shake = 22
        G.flashv = .55
        toast('备用核心启动 · 你还没有死透', 'gold')
        AUD.play('skill', 1.0)
        AUD.say('revive')
        return
    G.scene = 'dead'
    G.dead_t = 0
    clear_slot(G.save_slot)
    particle(p.x, p.y, 34, 'coral', 250, 34, .9)
    particle(p.x, p.y, 16, 'amber', 190, 28, .7)
    ring(p.x, p.y, 10, 240, 'coral', .9, 3)
    G.shake = 26
    AUD.play('big', 1.0)
    AUD.say('death')
    update_meta_end()
    layout()


def win_run():
    G.scene = 'win'
    G.win = True
    G.boss = None
    clear_slot(G.save_slot)
    AUD.say('clear', force=True)
    particle(W / 2, H / 2, 40, 'aqua', 260, 36, 1.2)
    ring(W / 2, H / 2, 20, 900, 'white', 1.4, 4)
    grant_ach('clear')
    if G.diff == 2:
        grant_ach('nightmare')
    if G.run:
        mid = MODES[G.run.mode]['id']
        if mid == 'rush':
            grant_ach('rush_clear')
        elif mid == 'hunt':
            grant_ach('hunt_clear')
        elif mid == 'daily':
            grant_ach('daily_clear')
        elif mid == 'pact':
            grant_ach('pact_clear')
    update_meta_end()
    layout()


def record_key(mode=None, diff=None):
    mode = getattr(G, 'mode', 0) if mode is None else mode
    diff = getattr(G, 'diff', 0) if diff is None else diff
    if mode == 0:
        return str(diff)
    if MODES[mode].get('daily'):
        return 'daily-%s-d%d' % (time.strftime('%Y%m%d'), diff)
    return 'm%d-d%d' % (mode, diff)


def best_record(mode=None, diff=None):
    return META.get('best_by_diff', {}).get(record_key(mode, diff), {})


def update_meta_end():
    if not G.run:
        return
    META['best_layer'] = max(META.get('best_layer', 0), G.run.layer)
    META['best_score'] = max(META.get('best_score', 0), G.run.score)
    META['kills'] = META.get('kills', 0) + G.run.kills
    if META['kills'] >= 100:
        grant_ach('slayer')
    if all(ship_unlocked(s) for s in SHIPS):
        grant_ach('fleet')
        grant_ach('allhands')
    bd = META.setdefault('best_by_diff', {})
    k = record_key(G.run.mode, G.diff)
    r = bd.get(k, {})
    bd[k] = {'layer': max(r.get('layer', 0), G.run.layer),
             'score': max(r.get('score', 0), G.run.score)}
    # 回声结晶：按本局表现结算，只加到当前存档，不跨槽共享
    earned = max(1, int(G.run.score / 6000) + int(G.run.layer * 1.5)
                 + int(G.run.kills / 25))
    G.run.shards_earned = earned
    p = normalize_profile(G.profile)
    p['shards'] = int(p.get('shards', 0)) + earned
    p['shards_total'] = int(p.get('shards_total', 0)) + earned
    p['best_layer'] = max(int(p.get('best_layer', 0)), int(G.run.layer))
    p['best_score'] = max(int(p.get('best_score', 0)), int(G.run.score))
    p['updated'] = _stamp()
    G.profile = p
    if G.save_slot is not None and int(G.save_slot) >= 0:
        save_profile(int(G.save_slot), p)
    if p['shards'] >= 100:
        grant_ach('shards100')
    if p['shards'] >= 300:
        grant_ach('shards300')
    if p['shards'] >= 500:
        grant_ach('shards500')
    if p['shards'] >= 800:
        grant_ach('shards800')
    save_meta()


def update_fires(dt):
    if not G.run:
        return
    for f in G.fires:
        f['t'] -= dt
        r2 = f['r'] ** 2
        for e in G.enemies:
            if e.dead:
                continue
            if dist2((e.x, e.y), (f['x'], f['y'])) < r2:
                e.hp -= 3.2 * G.run.st['dmg'] * dt
                e.burn_t = max(e.burn_t, .5)
                e.flash = max(e.flash, .05)
                if e.hp <= 0:
                    kill_enemy(e)
        if random.random() < .25:
            a = rnd(6.28)
            d = rnd(f['r'])
            particle(f['x'] + math.cos(a) * d, f['y'] + math.sin(a) * d, 1, 'amber', 60, 12, .3)
    G.fires = [f for f in G.fires if f['t'] > 0]


def draw_fires(surf, ox, oy):
    for f in G.fires:
        k = f['t'] / f['max']
        x, y = f['x'] + ox, f['y'] + oy
        rr = int(f['r'] * (.55 + .45 * k))
        pygame.draw.circle(surf, mix(COL['bg0'], COL['amber'], .35 + .35 * k), (int(x), int(y)), rr, 2)
        glow_at(surf, COL['coral'], x, y, f['r'] * 1.4, 1)


def update_camera(dt):
    """镜头跟随玩家；BOSS 战锁在大竞技场里"""
    p = G.player
    if not p:
        return
    if G.cam_lock is not None:
        tx, ty = G.cam_lock
        G.camx, G.camy = tx, ty
        return
    tx = p.x - W / 2 + p.vx * .14
    ty = p.y - H / 2 + p.vy * .14
    # 靠近地标时镜头略微上抬，让巨构能进入画面
    if G.landmark:
        d = math.sqrt(dist2((p.x, p.y), (G.landmark['x'], G.landmark['y'])))
        if d < 920:
            ty -= 230 * (1 - d / 920)
    tx = clamp(tx, 0, max(0, G.ww - W))
    ty = clamp(ty, 0, max(0, G.wh - H))
    k = min(1, dt * 7.0)
    G.camx = lerp(G.camx, tx, k)
    G.camy = lerp(G.camy, ty, k)


def arena_of_player():
    """以玩家当前位置为中心，取一个屏幕大小的 BOSS 竞技场"""
    p = G.player
    ax = clamp(p.x - W / 2, 0, max(0, G.ww - W))
    ay = clamp(p.y - H * .62, 0, max(0, G.wh - H))
    return (ax, ay)


def update(dt):
    if dt <= 0:
        return
    G.t += dt
    if G.scene == 'intro':
        G.intro_t = min(len(intro_page_text(G.intro_page)), G.intro_t + dt * 34)
        update_parts(dt * .5)
    elif G.scene == 'play':
        G.run.time += dt
        if G.layer_card_t > 0:
            G.layer_card_t = max(0, G.layer_card_t - dt)
        update_player(dt)
        update_camera(dt)
        update_pb(dt)
        update_enemies(dt)
        update_eb(dt)
        update_well(dt)
        update_boss(dt)
        update_drops(dt)
        update_fires(dt)
        update_drones(dt)
        update_caches(dt)
        update_wave(dt)
        update_parts(dt)
        if G.slow_t > 0:
            G.slow_t -= dt
        if G.combo_t > 0:
            G.combo_t -= dt
            if G.combo_t <= 0:
                G.combo = 0
        if G.wave_active and not G.queue and not G.enemies and not G.boss and G.wave_t > 1.6:
            if G.run.wave != waves_for_layer():
                wave_cleared()
    else:
        update_parts(dt * .5)
        if G.scene == 'dead':
            G.dead_t += dt
    if G.shake > 0:
        G.shake = max(0, G.shake - dt * 55)
    if G.flashv > 0:
        G.flashv = max(0, G.flashv - dt * 2.4)
    if G.banner:
        G.banner['t'] += dt
        if G.banner['t'] > G.banner['life']:
            G.banner = None
    if G.banner2:
        G.banner2['t'] += dt
        if G.banner2['t'] > G.banner2.get('life', 1.9):
            G.banner2 = None


def update_parts(dt):
    for p in G.parts:
        p['life'] -= dt
        if p.get('ring'):
            f = 1 - p['life'] / p['max']
            p['r'] = p['r0'] + (p['r1'] - p['r0']) * ease(f)
        else:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            k = max(0, 1 - 2.4 * dt)
            p['vx'] *= k
            p['vy'] *= k
    G.parts = [p for p in G.parts if p['life'] > 0]
    for b in G.beams:
        b['life'] -= dt
    G.beams = [b for b in G.beams if b['life'] > 0]

# -*- coding: utf-8 -*-
# ================================================================
#  绘制
# ================================================================
SCREEN = None
BG = None
DIM = None
SNOW = []
SHIP_CACHE = {}
FLAME = None
_dt_last = 1 / 60


def mix(c1, c2, t):
    t = clamp(t, 0, 1)
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def quad_points(p0, p1, p2, n=12):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def build_bg():
    global BG
    BG = pygame.Surface((W, H))
    c0, c1, c2 = COL['bg0'], COL['bg1'], COL['bg2']
    for y in range(H):
        f = y / H
        if f < .45:
            c = mix(c0, c1, f / .45)
        else:
            c = mix(c1, c2, (f - .45) / .55)
        pygame.draw.line(BG, c, (0, y), (W, y))

    # 顶部微光
    dome = pygame.transform.smoothscale(_glow_base((58, 138, 158), 1), (1600, 820))
    BG.blit(dome, (W // 2 - 800, -470), special_flags=pygame.BLEND_ADD)

    # 远景星云
    _soft_blob(BG, (30, 92, 104), int(W * .78), int(H * .58), 760, 320, 20)
    _soft_blob(BG, (66, 44, 96), int(W * .30), int(H * .74), 620, 260, 14)
    _soft_blob(BG, (108, 76, 34), int(W * .52), int(H * .20), 520, 200, 10)

    # 暗角
    small = pygame.Surface((80, 48), pygame.SRCALPHA)
    cx, cy = 40, 24
    for y in range(48):
        for x in range(80):
            d = math.hypot((x - cx) / 40, (y - cy) / 24)
            a = int(clamp((d - .55) * 230, 0, 118))
            small.set_at((x, y), (0, 0, 0, a))
    BG.blit(pygame.transform.smoothscale(small, (W, H)), (0, 0))


def build_snow():
    SNOW.clear()
    for i in range(110):
        layer = i % 3
        SNOW.append({'x': rnd(W), 'y': rnd(H), 'r': .6 + layer * .5,
                     's': 6 + layer * 12, 'a': .06 + layer * .06, 'ph': rnd(6.28)})


def build_shaft():
    global SHAFT
    SHAFT = shaft_for('aqua')


_SHAFTS = {}


def shaft_for(accent):
    """按区域强调色缓存柔光柱"""
    s = _SHAFTS.get(accent)
    if s:
        return s
    col = COL.get(accent, COL['aqua'])
    s = pygame.Surface((150, H), pygame.SRCALPHA)
    for i in range(150):
        a = int(11 * math.sin(math.pi * i / 150) ** 2)
        if a > 0:
            pygame.draw.line(s, (col[0], col[1], col[2], a), (i, 0), (i, H))
    _SHAFTS[accent] = s
    return s


def build_flame():
    global FLAME
    s = pygame.Surface((30, 80), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    for i in range(60):
        f = i / 60
        a = int(230 * (1 - f) ** 1.7)
        w = int(12 * (1 - f * .75))
        pygame.draw.rect(s, (95, 240, 208, a), (15 - w // 2, i * 1.3, w, 3))
    FLAME = s


SHIP_HULLS = {
    'dart': [(0, -46), (5, -33), (11, -20), (13, -2), (10, 18), (6, 38),
             (2, 42), (-2, 42), (-6, 38), (-10, 18), (-13, -2), (-11, -20), (-5, -33)],
    'anvil': [(0, -38), (14, -34), (24, -24), (26, -2), (22, 22), (14, 34),
              (6, 40), (-6, 40), (-14, 34), (-22, 22), (-26, -2), (-24, -24), (-14, -34)],
    'hammer': [(0, -44), (16, -36), (22, -34), (22, -28), (12, -24), (10, -18),
               (12, -8), (22, 10), (24, 28), (16, 38), (0, 42), (-16, 38),
               (-24, 28), (-22, 10), (-12, -8), (-10, -18), (-12, -24),
               (-22, -28), (-22, -34), (-16, -36)],
    'wedge': [(0, -48), (12, -30), (20, -6), (18, 18), (10, 34), (0, 40),
              (-10, 34), (-18, 18), (-20, -6), (-12, -30)],
    'hex': [(0, -42), (16, -30), (21, -6), (16, 20), (8, 34), (0, 38),
            (-8, 34), (-16, 20), (-21, -6), (-16, -30)],
    'orb': [(0, -36), (14, -32), (24, -20), (28, -2), (24, 18), (14, 32),
            (0, 38), (-14, 32), (-24, 18), (-28, -2), (-24, -20), (-14, -32)],
    'boat': [(0, -34), (18, -28), (24, -12), (26, 10), (20, 28), (10, 38),
             (0, 42), (-10, 38), (-20, 28), (-26, 10), (-24, -12), (-18, -28)],
    'blade': [(0, -48), (6, -28), (10, -4), (6, 18), (14, 36), (4, 42),
              (-4, 42), (-14, 36), (-6, 18), (-10, -4), (-6, -28)],
    'claw': [(0, -40), (10, -30), (16, -10), (22, 6), (18, 22), (8, 34),
             (0, 38), (-8, 34), (-18, 22), (-22, 6), (-16, -10), (-10, -30)],
    'serpent': [(0, -44), (8, -32), (10, -18), (4, -6), (14, 6), (10, 20),
                (4, 30), (8, 40), (-4, 44), (-10, 32), (-6, 18), (-14, 8),
                (-8, -4), (-10, -20), (-8, -32)],
    'star': [(0, -44), (9, -20), (24, -24), (14, -4), (30, 0), (14, 6),
             (22, 24), (8, 12), (0, 34), (-8, 12), (-22, 24), (-14, 6),
             (-30, 0), (-14, -4), (-24, -24), (-9, -20)],
    'eye': [(0, -40), (16, -30), (26, -14), (26, 4), (18, 22), (8, 34),
            (0, 38), (-8, 34), (-18, 22), (-26, 4), (-26, -14), (-16, -30)],
    'crystal': [(0, -46), (8, -28), (16, -18), (14, -2), (22, 8), (12, 20),
                (8, 38), (0, 44), (-8, 38), (-12, 20), (-22, 8), (-14, -2),
                (-16, -18), (-8, -28)],
}

SHIP_WINGS = {
    'swept': [(8, -8), (32, 14), (28, 26), (8, 16)],
    'falcon': [(8, -16), (28, 0), (38, 26), (10, 18)],
    'manta': [(10, -2), (45, 10), (36, 28), (8, 18)],
    'blade': [(10, 4), (40, 20), (34, 30), (8, 24)],
    'thorn': [(8, 2), (36, 12), (32, 26), (8, 20)],
    'hex': [(10, -4), (22, 2), (26, 18), (12, 22)],
    'none': [],
}

SHIP_LOOKS = {
    'echo': ('dart', 'swept', 'echo'), 'talon': ('wedge', 'falcon', 'talon'),
    'anvil': ('hammer', 'none', 'anvil'), 'swarm': ('hex', 'hex', 'honeycomb'),
    'prism': ('crystal', 'blade', 'prism'), 'thorn': ('dart', 'thorn', 'thorn'),
    'halo': ('orb', 'ring', 'halo'), 'void': ('orb', 'ring', 'void'),
    'pyre': ('serpent', 'blade', 'dragon'), 'frost': ('crystal', 'thorn', 'frost'),
    'rift': ('blade', 'blade', 'split'), 'bastion': ('anvil', 'none', 'rock'),
    'tide': ('boat', 'manta', 'wave'), 'star': ('star', 'none', 'spark'),
    'nova': ('star', 'none', 'nova'), 'lumen': ('orb', 'ring', 'lumen'),
    'corona': ('star', 'ring', 'corona'), 'refract': ('crystal', 'blade', 'facet'),
    'vortex': ('orb', 'ring', 'spiral'), 'forge': ('boat', 'none', 'furnace'),
    'storm': ('wedge', 'blade', 'bolt'), 'decoy': ('hex', 'twin', 'mirror'),
    'titan': ('anvil', 'none', 'titan'), 'oracle': ('eye', 'ring', 'oracle'),
    'lark': ('wedge', 'falcon', 'bird'), 'manta': ('boat', 'manta', 'manta'),
    'kraken': ('claw', 'none', 'kraken'), 'solar': ('star', 'none', 'sun'),
    'starferry': ('boat', 'swept', 'raft'), 'eclipse': ('orb', 'blade', 'eclipse'),
    'bulwark': ('boat', 'twin', 'rock'), 'weaver': ('hex', 'ring', 'web'),
    'requiem': ('eye', 'ring', 'harp'), 'glaive': ('blade', 'ring', 'ringblade'),
    'seraph': ('eye', 'falcon', 'seraph'), 'abysseye': ('eye', 'none', 'abyss_eye'),
    'sepulcher': ('anvil', 'none', 'tomb'), 'hivemind': ('hex', 'hex', 'queen'),
    'dawn': ('orb', 'falcon', 'dawn'), 'breakwater': ('wedge', 'manta', 'breaker'),
}


def _ship_pts(cx, cy, pts):
    return [(cx + x, cy + y) for x, y in pts]


def _ship_scale_pts(cx, cy, pts, k):
    return [(cx + x * k, cy + y * k) for x, y in pts]


def _ship_poly(s, pts, fill, edge=None, width=1):
    pygame.draw.polygon(s, fill, pts)
    if edge:
        pygame.draw.polygon(s, edge, pts, width)


def _ship_hex(s, x, y, r, fill, edge):
    p = [(x + math.cos(a) * r, y + math.sin(a) * r)
         for a in (math.pi / 6 + i * math.pi / 3 for i in range(6))]
    pygame.draw.polygon(s, fill, p)
    pygame.draw.polygon(s, edge, p, 1)


def _ship_star4(s, x, y, r, col):
    p = []
    for i in range(8):
        a = -math.pi / 2 + i * math.pi / 4
        rr = r if i % 2 == 0 else r * .42
        p.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    pygame.draw.polygon(s, col, p)


def _ship_wing(s, cx, cy, kind, dark, c, light, hot):
    if kind == 'none':
        return
    if kind == 'ring':
        pygame.draw.ellipse(s, mix(c, COL['bg0'], .22), (cx - 38, cy - 19, 76, 52), 1)
        pygame.draw.ellipse(s, mix(c, light, .25), (cx - 31, cy - 13, 62, 38), 1)
        for i in range(8):
            a = i * math.pi / 4
            pygame.draw.circle(s, hot, (int(cx + math.cos(a) * 34), int(cy + math.sin(a) * 23)), 1)
        return
    if kind == 'twin':
        for sgn in (-1, 1):
            p = [(cx + sgn * 14, cy - 8), (cx + sgn * 22, cy - 2),
                 (cx + sgn * 24, cy + 22), (cx + sgn * 17, cy + 30),
                 (cx + sgn * 12, cy + 24)]
            _ship_poly(s, p, dark, c)
            pygame.draw.line(s, light, p[1], p[3], 1)
        return
    if kind == 'hex':
        for sgn in (-1, 1):
            _ship_hex(s, cx + sgn * 20, cy + 8, 10, dark, c)
            _ship_hex(s, cx + sgn * 24, cy + 22, 6, mix(dark, c, .2), mix(c, light, .3))
        return
    base = SHIP_WINGS.get(kind, [])
    if not base:
        return
    for sgn in (-1, 1):
        p = [(cx + sgn * x, cy + y) for x, y in base]
        _ship_poly(s, p, dark, c)
        # 翼内高光
        if len(p) >= 4:
            pygame.draw.aaline(s, light, p[0], p[2])
            pygame.draw.aaline(s, mix(c, light, .2), p[1], p[3])
        if kind == 'falcon':
            pygame.draw.aaline(s, hot, (cx + sgn * 12, cy - 10), (cx + sgn * 34, cy + 24))
        if kind == 'manta':
            pygame.draw.arc(s, mix(c, light, .25),
                            pygame.Rect(int(cx - 40), int(cy + 4), 80, 34), .2, 2.8, 1)


def _ship_motif(s, cx, cy, motif, c, mid, light, hot):
    if motif == 'echo':
        for rr in (13, 20, 27):
            pygame.draw.arc(s, mix(c, light, .35),
                            pygame.Rect(int(cx - rr), int(cy - 10 - rr), rr * 2, rr * 2),
                            -.45, 2.35, 1)
        pygame.draw.circle(s, hot, (int(cx), int(cy - 8)), 2)
        for sgn in (-1, 1):
            pygame.draw.circle(s, c, (int(cx + sgn * 17), int(cy + 8)), 2)
    elif motif == 'talon':
        for dx in (-11, 0, 11):
            p = [(cx + dx * .55, cy - 20), (cx + dx * 1.15, cy - 47), (cx + dx * 1.35, cy - 22)]
            pygame.draw.polygon(s, mix(c, light, .35), p, 0)
        for sgn in (-1, 1):
            pygame.draw.arc(s, hot, pygame.Rect(int(cx + sgn * 2 - 14), int(cy - 20), 28, 24),
                            .2 if sgn > 0 else 1.4, 2.9 if sgn > 0 else 4.1, 1)
    elif motif == 'anvil':
        pygame.draw.rect(s, mix(c, light, .45), (cx - 19, cy - 34, 38, 6))
        pygame.draw.rect(s, c, (cx - 19, cy - 34, 38, 6), 1)
        pygame.draw.line(s, light, (cx - 15, cy + 22), (cx + 15, cy + 22), 1)
        for dx in (-10, 0, 10):
            pygame.draw.line(s, mix(c, light, .2), (cx + dx, cy - 22), (cx + dx * 1.25, cy + 20), 1)
    elif motif == 'honeycomb':
        for dx, dy, r in ((-15, 8, 5), (0, 12, 5), (15, 8, 5), (-9, 24, 4), (9, 24, 4)):
            _ship_hex(s, cx + dx, cy + dy, r, mix(mid, c, .3), hot)
        pygame.draw.circle(s, hot, (int(cx), int(cy - 6)), 2)
    elif motif == 'prism':
        for sgn in (-1, 1):
            pygame.draw.polygon(s, (*mix(c, light, .35), 80),
                                [(cx, cy - 30), (cx + sgn * 12, cy - 6), (cx, cy + 16)])
            pygame.draw.line(s, hot, (cx, cy - 30), (cx + sgn * 15, cy + 8), 1)
        pygame.draw.line(s, light, (cx, cy - 26), (cx, cy + 20), 1)
    elif motif == 'thorn':
        for i in range(12):
            a = i * math.pi / 6
            x1, y1 = cx + math.cos(a) * 12, cy + math.sin(a) * 18
            x2, y2 = cx + math.cos(a) * 23, cy + math.sin(a) * 30
            pygame.draw.line(s, mix(c, light, .25), (x1, y1), (x2, y2), 1)
        pygame.draw.circle(s, hot, (int(cx), int(cy)), 2)
    elif motif == 'halo':
        pygame.draw.ellipse(s, mix(c, light, .45), (cx - 20, cy - 24, 40, 22), 1)
        pygame.draw.ellipse(s, mix(c, hot, .5), (cx - 14, cy - 19, 28, 13), 1)
        pygame.draw.circle(s, hot, (int(cx), int(cy - 14)), 2)
    elif motif == 'void':
        pygame.draw.circle(s, (5, 9, 16), (int(cx), int(cy - 1)), 9)
        pygame.draw.circle(s, mix(c, light, .35), (int(cx), int(cy - 1)), 13, 1)
        pygame.draw.arc(s, hot, pygame.Rect(int(cx - 19), int(cy - 14), 38, 26), .2, 2.9, 1)
        for dx, dy in ((-12, -16), (13, -12), (0, 14)):
            pygame.draw.circle(s, hot, (int(cx + dx), int(cy + dy)), 1)
    elif motif == 'dragon':
        for i in range(5):
            pygame.draw.circle(s, mix(c, light, .3), (int(cx), int(cy - 20 + i * 9)), 2)
            pygame.draw.line(s, light, (cx - 5, cy - 20 + i * 9), (cx + 5, cy - 20 + i * 9), 1)
        for sgn in (-1, 1):
            pygame.draw.arc(s, hot, pygame.Rect(int(cx - 10), int(cy + 22), 20, 22),
                            .4 if sgn > 0 else 1.2, 2.7 if sgn > 0 else 3.4, 1)
    elif motif == 'frost':
        for i in range(6):
            a = i * math.pi / 3
            x1, y1 = cx + math.cos(a) * 7, cy + math.sin(a) * 8
            x2, y2 = cx + math.cos(a) * 24, cy + math.sin(a) * 28
            pygame.draw.line(s, mix(c, light, .45), (x1, y1), (x2, y2), 1)
            pygame.draw.line(s, light, (x2, y2),
                             (x2 - math.cos(a + .5) * 5, y2 - math.sin(a + .5) * 5), 1)
            pygame.draw.line(s, light, (x2, y2),
                             (x2 - math.cos(a - .5) * 5, y2 - math.sin(a - .5) * 5), 1)
    elif motif == 'split':
        pygame.draw.polygon(s, (6, 12, 18), [(cx, cy - 43), (cx + 3, cy - 12),
                                              (cx + 2, cy + 20), (cx, cy + 40),
                                              (cx - 2, cy + 20), (cx - 3, cy - 12)])
        pygame.draw.line(s, hot, (cx - 2, cy - 38), (cx - 2, cy + 36), 1)
        pygame.draw.line(s, hot, (cx + 2, cy - 38), (cx + 2, cy + 36), 1)
    elif motif == 'rock':
        for pts in ([(cx - 17, cy - 24), (cx - 7, cy - 12), (cx - 12, cy + 4), (cx - 2, cy + 22)],
                    [(cx + 16, cy - 20), (cx + 8, cy - 6), (cx + 15, cy + 10), (cx + 6, cy + 28)]):
            pygame.draw.lines(s, mix(c, light, .25), False, pts, 1)
        pygame.draw.line(s, light, (cx - 20, cy + 18), (cx + 20, cy + 18), 1)
    elif motif == 'wave':
        for sgn in (-1, 1):
            for rr in (0, 6, 12):
                pygame.draw.arc(s, mix(c, light, .3),
                                pygame.Rect(int(cx + sgn * 8 - 34), int(cy + 10 + rr), 68, 30 - rr),
                                .3, 2.8, 1)
    elif motif == 'spark':
        for dx, dy, r in ((-12, -8, 5), (0, 2, 7), (14, 12, 4)):
            _ship_star4(s, cx + dx, cy + dy, r, hot)
    elif motif == 'nova':
        for i in range(12):
            a = i * math.pi / 6
            pygame.draw.line(s, mix(c, light, .35), (cx + math.cos(a) * 8, cy + math.sin(a) * 12),
                             (cx + math.cos(a) * 28, cy + math.sin(a) * 34), 1)
        pygame.draw.circle(s, hot, (int(cx), int(cy)), 3)
    elif motif == 'lumen':
        pygame.draw.ellipse(s, (*mix(c, hot, .55), 70), (cx - 8, cy - 22, 16, 36))
        pygame.draw.line(s, hot, (cx, cy - 25), (cx, cy + 24), 1)
        pygame.draw.circle(s, COL['white'], (int(cx), int(cy - 9)), 2)
    elif motif == 'corona':
        pygame.draw.ellipse(s, mix(c, light, .35), (cx - 27, cy - 30, 54, 58), 1)
        for i in range(14):
            a = i * math.pi / 7
            pygame.draw.line(s, mix(c, hot, .35), (cx + math.cos(a) * 22, cy + math.sin(a) * 25),
                             (cx + math.cos(a) * 31, cy + math.sin(a) * 36), 1)
        pygame.draw.circle(s, hot, (int(cx), int(cy - 2)), 3)
    elif motif == 'facet':
        for sgn in (-1, 1):
            for i in range(3):
                y = cy - 18 + i * 14
                pygame.draw.polygon(s, (*mix(c, light, .3 + i * .1), 55),
                                    [(cx, y), (cx + sgn * 15, y + 6), (cx + sgn * 8, y + 14)])
        pygame.draw.line(s, hot, (cx - 12, cy - 22), (cx + 12, cy + 24), 1)
    elif motif == 'spiral':
        p = []
        for i in range(28):
            a = i * .33
            rr = 3 + i * .9
            p.append((cx + math.cos(a) * rr, cy - 2 + math.sin(a) * rr * .75))
        pygame.draw.lines(s, mix(c, light, .35), False, p, 1)
        pygame.draw.circle(s, hot, (int(cx), int(cy - 2)), 2)
    elif motif == 'furnace':
        for sgn in (-1, 1):
            pygame.draw.rect(s, mix(mid, c, .35), (int(cx + sgn * 9 - 4), int(cy + 18), 8, 18))
            pygame.draw.rect(s, hot, (int(cx + sgn * 9 - 2), int(cy + 26), 4, 3))
            pygame.draw.line(s, light, (cx + sgn * 9, cy - 12), (cx + sgn * 9, cy + 16), 1)
        pygame.draw.circle(s, hot, (int(cx), int(cy + 4)), 2)
    elif motif == 'bolt':
        p = [(cx - 12, cy - 30), (cx - 2, cy - 18), (cx - 8, cy - 16),
             (cx + 6, cy - 2), (cx - 2, cy), (cx + 14, cy + 18)]
        pygame.draw.lines(s, hot, False, p, 1)
        pygame.draw.lines(s, mix(c, light, .2), False, p, 2)
    elif motif == 'mirror':
        for sgn in (-1, 1):
            pygame.draw.polygon(s, (*mix(c, light, .25), 70),
                                [(cx + sgn * 5, cy - 26), (cx + sgn * 17, cy - 6),
                                 (cx + sgn * 12, cy + 24), (cx + sgn * 3, cy + 8)])
        pygame.draw.line(s, hot, (cx, cy - 24), (cx, cy + 22), 1)
    elif motif == 'titan':
        for sgn in (-1, 1):
            pygame.draw.rect(s, mix(mid, c, .3), (int(cx + sgn * 21 - 6), int(cy - 8), 12, 18))
            pygame.draw.rect(s, c, (int(cx + sgn * 21 - 6), int(cy - 8), 12, 18), 1)
            pygame.draw.line(s, hot, (cx + sgn * 21, cy - 8), (cx + sgn * 21, cy - 26), 2)
        pygame.draw.line(s, light, (cx - 12, cy + 20), (cx + 12, cy + 20), 1)
    elif motif == 'oracle':
        pygame.draw.ellipse(s, mix(c, light, .3), (cx - 18, cy - 18, 36, 22), 1)
        pygame.draw.circle(s, mix(c, light, .55), (int(cx), int(cy - 7)), 6)
        pygame.draw.circle(s, COL['white'], (int(cx), int(cy - 7)), 2)
        pygame.draw.arc(s, hot, pygame.Rect(int(cx - 24), int(cy - 26), 48, 40), .2, 2.9, 1)
    elif motif == 'bird':
        for sgn in (-1, 1):
            for i in range(3):
                pygame.draw.arc(s, mix(c, light, .25),
                                pygame.Rect(int(cx + sgn * 6 - 12), int(cy - 4 + i * 8), 24, 16),
                                .3 if sgn > 0 else 1.4, 2.8 if sgn > 0 else 3.9, 1)
    elif motif == 'manta':
        for sgn in (-1, 1):
            for i in range(3):
                pygame.draw.line(s, mix(c, light, .2), (cx + sgn * (14 + i * 6), cy + 8),
                                 (cx + sgn * (12 + i * 6), cy + 20), 1)
    elif motif == 'kraken':
        for i in range(3):
            pygame.draw.arc(s, mix(c, light, .28),
                            pygame.Rect(int(cx - 20 + i * 5), int(cy + 10), 20, 30), .2, 2.7, 1)
            pygame.draw.arc(s, mix(c, hot, .2),
                            pygame.Rect(int(cx + 12 - i * 5), int(cy + 10), 20, 30), .4, 2.9, 1)
        pygame.draw.circle(s, hot, (int(cx), int(cy + 1)), 2)
    elif motif == 'sun':
        pygame.draw.circle(s, mix(c, hot, .35), (int(cx), int(cy - 1)), 8, 1)
        for i in range(12):
            a = i * math.pi / 6
            pygame.draw.line(s, mix(c, light, .3), (cx + math.cos(a) * 11, cy - 1 + math.sin(a) * 12),
                             (cx + math.cos(a) * 22, cy - 1 + math.sin(a) * 24), 1)
    elif motif == 'raft':
        pygame.draw.polygon(s, mix(c, light, .25), [(cx, cy - 30), (cx + 14, cy + 4), (cx - 14, cy + 4)])
        pygame.draw.line(s, hot, (cx, cy - 30), (cx, cy + 18), 1)
        pygame.draw.line(s, light, (cx - 12, cy + 20), (cx + 12, cy + 20), 1)
        for dx, dy in ((-18, -12), (18, -8), (0, 16)):
            _ship_star4(s, cx + dx, cy + dy, 3, hot)
    elif motif == 'eclipse':
        pygame.draw.circle(s, (4, 7, 12), (int(cx), int(cy - 4)), 10)
        pygame.draw.arc(s, mix(c, hot, .4), pygame.Rect(int(cx - 14), int(cy - 18), 28, 28), .3, 2.9, 1)
        pygame.draw.circle(s, mix(c, light, .2), (int(cx), int(cy - 4)), 15, 1)
    elif motif == 'web':
        for i in range(3):
            rr = 10 + i * 8
            pygame.draw.ellipse(s, mix(c, light, .3), (cx - rr, cy - rr * .7, rr * 2, rr * 1.4), 1)
        for i in range(6):
            a = i * math.pi / 3
            pygame.draw.line(s, mix(c, light, .2), (cx, cy), (cx + math.cos(a) * 28, cy + math.sin(a) * 20), 1)
        for dx, dy in ((-16, -10), (14, -6), (0, 16)):
            pygame.draw.circle(s, hot, (int(cx + dx), int(cy + dy)), 2)
    elif motif == 'harp':
        for i in range(4):
            pygame.draw.line(s, mix(c, light, .3), (cx - 10 + i * 7, cy - 18),
                             (cx - 10 + i * 7, cy + 22), 1)
        pygame.draw.arc(s, hot, pygame.Rect(int(cx - 14), int(cy - 24), 28, 10), 0, 3.14, 1)
        pygame.draw.arc(s, hot, pygame.Rect(int(cx - 14), int(cy + 16), 28, 10), 0, 3.14, 1)
    elif motif == 'ringblade':
        for sgn in (-1, 1):
            pygame.draw.circle(s, mix(c, light, .3), (int(cx + sgn * 22), int(cy + 10)), 9, 1)
            pygame.draw.arc(s, hot, pygame.Rect(int(cx + sgn * 22 - 9), int(cy + 1), 18, 18), .2, 2.9, 2)
        pygame.draw.line(s, hot, (cx - 10, cy + 4), (cx + 10, cy + 4), 1)
    elif motif == 'seraph':
        for sgn in (-1, 1):
            for i in range(3):
                pygame.draw.arc(s, mix(c, light, .35),
                                pygame.Rect(int(cx + sgn * 4 - 14), int(cy - 2 + i * 8), 28, 18),
                                .3 if sgn > 0 else 1.3, 2.8 if sgn > 0 else 3.7, 1)
        pygame.draw.ellipse(s, hot, (cx - 16, cy - 26, 32, 12), 1)
        pygame.draw.line(s, COL['white'], (cx, cy - 18), (cx, cy + 18), 1)
    elif motif == 'abyss_eye':
        pygame.draw.ellipse(s, mix(c, light, .25), (cx - 20, cy - 20, 40, 30), 1)
        pygame.draw.ellipse(s, (3, 7, 12), (cx - 12, cy - 14, 24, 18))
        pygame.draw.circle(s, mix(c, hot, .4), (int(cx), int(cy - 5)), 4)
        pygame.draw.line(s, COL['white'], (cx, cy - 14), (cx, cy + 4), 1)
    elif motif == 'tomb':
        pygame.draw.rect(s, mix(mid, c, .3), (cx - 10, cy - 34, 20, 48))
        pygame.draw.rect(s, c, (cx - 10, cy - 34, 20, 48), 1)
        pygame.draw.line(s, light, (cx - 14, cy - 20), (cx + 14, cy - 20), 1)
        pygame.draw.line(s, light, (cx - 14, cy + 8), (cx + 14, cy + 8), 1)
        pygame.draw.line(s, mix(c, light, .2), (cx - 5, cy - 10), (cx - 3, cy + 2), 1)
    elif motif == 'queen':
        for dx in (-10, 0, 10):
            pygame.draw.polygon(s, hot, [(cx + dx - 3, cy - 26), (cx + dx, cy - 38), (cx + dx + 3, cy - 26)])
        pygame.draw.ellipse(s, mix(c, light, .3), (cx - 9, cy - 10, 18, 28), 1)
        for dy in (0, 9, 18):
            _ship_hex(s, cx, cy + dy, 4, mix(mid, c, .3), hot)
    elif motif == 'dawn':
        pygame.draw.line(s, mix(c, light, .35), (cx - 24, cy + 2), (cx + 24, cy + 2), 1)
        for i in range(7):
            a = math.pi + i * math.pi / 6
            pygame.draw.line(s, hot, (cx, cy + 2), (cx + math.cos(a) * 25, cy + 2 + math.sin(a) * 28), 1)
        pygame.draw.circle(s, mix(c, hot, .4), (int(cx), int(cy + 2)), 5)
    elif motif == 'breaker':
        for sgn in (-1, 1):
            pygame.draw.polygon(s, mix(c, light, .28),
                                [(cx + sgn * 3, cy - 36), (cx + sgn * 14, cy - 14),
                                 (cx + sgn * 8, cy + 28)])
        pygame.draw.line(s, hot, (cx - 2, cy - 34), (cx + 2, cy + 28), 1)
        pygame.draw.line(s, light, (cx - 18, cy + 22), (cx + 18, cy + 22), 1)


def make_ship(col, sid='echo'):
    key = (sid, col)
    if key in SHIP_CACHE:
        return SHIP_CACHE[key]
    s = pygame.Surface((96, 112), pygame.SRCALPHA)
    cx, cy = 48, 58
    c = COL.get(col, COL['aqua'])
    dark = mix(COL['bg1'], c, .14)
    mid = mix((8, 22, 30), c, .30)
    light = mix(c, COL['white'], .42)
    hot = mix(c, COL['white'], .82)
    hull, wing, motif = SHIP_LOOKS.get(sid, ('dart', 'swept', 'echo'))
    aura = pygame.Surface((96, 112), pygame.SRCALPHA)
    pygame.draw.ellipse(aura, (*mix(c, (4, 10, 16), .45), 32), (8, 24, 80, 70))
    s.blit(aura, (0, 0))
    _ship_wing(s, cx, cy, wing, dark, c, light, hot)
    hp = _ship_pts(cx, cy, SHIP_HULLS.get(hull, SHIP_HULLS['dart']))
    _ship_poly(s, hp, mid, c, 1)
    ip = _ship_scale_pts(cx, cy, SHIP_HULLS.get(hull, SHIP_HULLS['dart']), .70)
    pygame.draw.polygon(s, mix(mid, light, .16), ip, 1)
    _ship_motif(s, cx, cy, motif, c, mid, light, hot)
    # 驾驶舱
    cp = [(cx, cy - 26), (cx + 5, cy - 14), (cx + 4, cy - 4),
          (cx - 4, cy - 4), (cx - 5, cy - 14)]
    pygame.draw.polygon(s, (224, 253, 249), cp)
    pygame.draw.polygon(s, mix(c, COL['white'], .55), cp, 1)
    pygame.draw.circle(s, COL['white'], (int(cx), int(cy - 14)), 2)
    # 引擎舱
    engines = 3 if hull in ('anvil', 'boat', 'hammer') else 2
    for i in range(engines):
        ex = cx + (i - (engines - 1) / 2) * 7
        pygame.draw.rect(s, (10, 26, 34), (int(ex - 3), int(cy + 28), 6, 9))
        pygame.draw.rect(s, c, (int(ex - 3), int(cy + 28), 6, 9), 1)
        pygame.draw.circle(s, mix(c, COL['white'], .65), (int(ex), int(cy + 37)), 2)
    # 舷灯与艏灯
    pygame.draw.rect(s, c, (cx - 12, cy + 2, 3, 5))
    pygame.draw.rect(s, c, (cx + 9, cy + 2, 3, 5))
    pygame.draw.circle(s, (255, 246, 218), (int(cx), int(cy - 44 if hull in ('dart', 'blade', 'wedge') else cy - 36)), 2)
    SHIP_CACHE[key] = s
    return s


def glow_ship(x, y):
    s = pygame.Surface((120, 120))
    s.fill((0, 0, 0))
    pygame.draw.circle(s, (26, 62, 66), (60, 60), 46)
    return s


# ---------------------------------------------------------------- 背景层
def draw_bg(surf, dt):
    global _dt_last
    surf.blit(BG, (0, 0))
    # 海雪
    for s in SNOW:
        s['y'] += s['s'] * dt * (1.6 if G.scene == 'play' else .6)
        s['x'] += math.sin(G.t * .35 + s['ph']) * 8 * dt
        if s['y'] > H + 6:
            s['y'] = -6
            s['x'] = rnd(W)
        if s['x'] < -10:
            s['x'] = W + 10
        elif s['x'] > W + 10:
            s['x'] = -10
        c = mix(COL['bg0'], COL['white'], s['a'] * 3.2)
        pygame.draw.circle(surf, c, (int(s['x']), int(s['y'])), int(max(1, s['r'])))


def draw_sonar(surf, x, y, t):
    R = 420
    a0 = t * .7
    for i in range(16):
        p = i / 16
        ang = a0 - p * .3
        c = mix(COL['bg0'], COL['aqua'], (.5 - p * .5) * .45)
        pygame.draw.line(surf, c, (x, y), (x + math.cos(ang) * R, y + math.sin(ang) * R), 1)
    for rr in (110, 220, 330):
        for k in range(36):
            ang = k * math.pi / 18
            c = mix(COL['bg0'], COL['aqua'], .3)
            pygame.draw.line(surf, c,
                             (x + math.cos(ang) * rr, y + math.sin(ang) * rr),
                             (x + math.cos(ang + .09) * rr, y + math.sin(ang + .09) * rr), 1)


# ---------------------------------------------------------------- 实体
_ROT_CACHE = {}


def rot_ship(img_key, img, deg, scale):
    k = (img_key, int(round(deg)) % 360, round(scale, 2))
    s = _ROT_CACHE.get(k)
    if s is None:
        if len(_ROT_CACHE) > 520:
            _ROT_CACHE.clear()
        s = pygame.transform.rotozoom(img, deg, scale)
        _ROT_CACHE[k] = s
    return s


def draw_ship_at(surf, x, y, roll, col='aqua', alpha_blink=True, shield=0, scale=1.2,
                 heading=0.0, sid='echo'):
    img = make_ship(col, sid)
    rot = rot_ship(('ship', sid, col), img, -math.degrees(roll + heading), scale)
    rect = rot.get_rect(center=(int(x), int(y)))
    # 尾焰：从船尾向后喷，随船头一起旋转
    if FLAME:
        f = 0.75 + random.random() * .5
        fwid = max(1, int(20 * scale * (0.9 + random.random() * .3)))
        fhei = max(1, int(30 * scale * f))
        fl = pygame.transform.smoothscale(FLAME, (fwid, fhei))
        ang = heading + roll
        if abs(ang) > .001:
            fl = pygame.transform.rotate(fl, -math.degrees(ang))
        bx, by = -math.sin(ang), math.cos(ang)
        rx, ry = x + bx * 30 * scale, y + by * 30 * scale
        fw, fh = fl.get_size()
        half = abs(bx) * fw * .5 + abs(by) * fh * .5
        fr = fl.get_rect(center=(int(rx + bx * half), int(ry + by * half)))
        surf.blit(fl, fr, special_flags=pygame.BLEND_ADD)
    surf.blit(rot, rect)
    if shield > 0:
        for i in range(shield):
            r = 26 + i * 4
            pygame.draw.circle(surf, mix(COL['bg0'], COL['aqua'], .55), (int(x), int(y)), r, 1)


def draw_ship_icon(surf, center, sid, col, height=36, glow=True):
    """名录/按钮用的小模型，保持船头朝上，不参与旋转缓存。"""
    img = make_ship(col, sid)
    w = max(1, int(round(img.get_width() * height / img.get_height())))
    scaled = pygame.transform.smoothscale(img, (w, height))
    if glow:
        glow_at(surf, COL.get(col, COL['aqua']), center[0], center[1] + 3,
                max(20, int(height * .82)), 1)
    surf.blit(scaled, scaled.get_rect(center=(int(center[0]), int(center[1]))))


def draw_player(surf, ox, oy):
    p = G.player
    if not p:
        return
    x, y = p.x + ox, p.y + oy
    aim = p.aim
    glow_at(surf, COL[G.run.ship.get('col', 'amber')], x + math.sin(aim) * 7,
            y - math.cos(aim) * 7, 44, 1)
    blink = 1.0
    if p.inv > 0 and int(p.inv * 18) % 2 == 0:
        blink = .45
    if blink >= 1:
        draw_ship_at(surf, x, y, p.roll, G.run.ship['col'], shield=p.shield, heading=aim,
                     sid=G.run.ship['id'])
    else:
        draw_ship_at(surf, x, y, p.roll, G.run.ship['col'], shield=p.shield, heading=aim,
                     sid=G.run.ship['id'])
    # 自动索敌时从船头伸出一小段金色准星（鼠标模式由鼠标准星指示）
    if abs(aim) > .02 and G.aim_mode == 'auto':
        nx, ny = math.sin(aim), -math.cos(aim)
        acol = 'gold'
        a0 = (int(x + nx * 46), int(y + ny * 46))
        a1 = (int(x + nx * 72), int(y + ny * 72))
        pygame.draw.line(surf, mix(COL['bg0'], COL[acol], .55), a0, a1, 1)
        pygame.draw.circle(surf, mix(COL['bg0'], COL[acol], .8), a1, 2)
    if p.charge_t > 0:
        f = 1 - p.charge_t / p.charge_need
        pygame.draw.circle(surf, mix(COL['bg0'], COL['green'], .55), (int(x), int(y)), int(14 + f * 18), 1)
    if p.od_t > 0:
        pygame.draw.circle(surf, mix(COL['bg0'], COL['amber'], .5), (int(x), int(y)), 34, 1)
    st = G.run.st
    if st['orbit'] > 0:
        n = 2 * int(st['orbit'])
        for i in range(n):
            a = p.orb_ang + i * math.pi * 2 / n
            ox2 = x + math.cos(a) * 58
            oy2 = y + math.sin(a) * 58 * .92
            glow_at(surf, COL['gold'], ox2, oy2, 26, 1)
            pygame.draw.circle(surf, COL['gold'], (int(ox2), int(oy2)), 4)
            pygame.draw.circle(surf, COL['white'], (int(ox2), int(oy2)), 1)
    if p.web_t > 0:
        pygame.draw.circle(surf, mix(COL['bg0'], COL['green'], .4), (int(x), int(y)), 22, 1)


def draw_player_blades(surf, ox, oy):
    p = G.player
    if not p or G.run.st['blade'] <= 0:
        return
    x, y = p.x + ox, p.y + oy
    n = max(1, int(G.run.st['blade']))
    for i in range(n):
        a = p.blade_ang + i * math.pi * 2 / n
        bx = x + math.cos(a) * 76
        by = y + math.sin(a) * 76
        glow_at(surf, COL['steel'], bx, by, 30, 1)
        da = a + math.pi / 2
        pygame.draw.line(surf, COL['steel'],
                         (bx - math.cos(da) * 13, by - math.sin(da) * 13),
                         (bx + math.cos(da) * 13, by + math.sin(da) * 13), 3)
        pygame.draw.line(surf, COL['white'],
                         (bx - math.cos(da) * 8, by - math.sin(da) * 8),
                         (bx + math.cos(da) * 8, by + math.sin(da) * 8), 1)


def draw_enemy(surf, e, ox, oy):
    x, y = e.x + ox, e.y + oy
    d = EKIND[e.kind]
    col = COL[d['col']]
    fl = e.flash > 0
    if e.spawn_t > .16:
        k = 1 - e.spawn_t / .4
        pygame.draw.circle(surf, mix(COL['bg0'], col, .5 + .35 * k), (int(x), int(y)),
                           int(e.r * (.45 + k * 1.15)), 1)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['white'], .55), (int(x), int(y)),
                           max(1, int(e.r * .3 * k)))
        return
    glow_at(surf, COL['white'] if fl else col, x, y, e.r * 2.4, 2)

    if e.kind == 'drifter':
        for k in range(4):
            a = math.pi * .5 + (k - 1.5) * .55 + math.sin(e.t * 2 + k) * .16
            p0 = (x + math.cos(a) * 6, y + math.sin(a) * 6)
            p1 = (x + math.cos(a) * e.r * .95 + math.sin(e.t * 3 + k) * 7, y + e.r * 1.5)
            p2 = (x + math.cos(a) * e.r * .6 + math.sin(e.t * 2 + k) * 12, y + e.r * 2.2)
            pygame.draw.lines(surf, mix(COL['bg0'], col, .45), False, quad_points(p0, p1, p2, 6), 1)
        pygame.draw.circle(surf, (12, 52, 58), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .35), (int(x), int(y)), int(e.r * .62), 1)
        pygame.draw.circle(surf, col, (int(x), int(y + 6)), 5)
        pygame.draw.circle(surf, COL['white'], (int(x), int(y + 5)), 2)
    elif e.kind == 'lantern':
        for k in range(4):
            a = k * math.pi / 2 + e.t * .5
            p1 = (x + math.cos(a) * e.r * 1.15, y + math.sin(a) * e.r * 1.15)
            p2 = (x + math.cos(a + .55) * e.r * .55, y + math.sin(a + .55) * e.r * .55)
            p3 = (x + math.cos(a - .55) * e.r * .55, y + math.sin(a - .55) * e.r * .55)
            pygame.draw.polygon(surf, mix(COL['bg0'], col, .55), [p1, p2, p3], 1)
        pygame.draw.circle(surf, (10, 40, 30), (int(x), int(y)), int(e.r * .72))
        b = .5 + math.sin(e.t * 5) * .22
        pygame.draw.circle(surf, mix(COL['bg0'], col, b), (int(x), int(y)), int(e.r * .42))
        pygame.draw.circle(surf, COL['white'], (int(x), int(y)), int(e.r * .18))
    elif e.kind == 'hunter':
        a = e.ang + math.pi / 2
        pts = []
        body = [(0, -e.r * 1.7), (e.r * .72, e.r * .5), (e.r * .28, e.r * 1.1),
                (-e.r * .28, e.r * 1.1), (-e.r * .72, e.r * .5)]
        for px, py in body:
            pts.append((x + px * math.cos(a) - py * math.sin(a),
                        y + px * math.sin(a) + py * math.cos(a)))
        pygame.draw.polygon(surf, (48, 18, 26), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)
        for s in (-1, 1):
            ex = x + (s * 4.5) * math.cos(a) - (-e.r * .35) * math.sin(a)
            ey = y + (s * 4.5) * math.sin(a) + (-e.r * .35) * math.cos(a)
            pygame.draw.circle(surf, col, (int(ex), int(ey)), 2)
    elif e.kind == 'turret':
        pts = []
        for k in range(6):
            ang = k * math.pi / 3 + math.sin(e.t * .4) * .1
            pts.append((x + math.cos(ang) * e.r, y + math.sin(ang) * e.r))
        pygame.draw.polygon(surf, (30, 22, 56), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)
        for k in (0, 1):
            ang = e.ang + k * math.pi
            pygame.draw.line(surf, col, (x, y),
                             (x + math.cos(ang) * e.r * 1.25, y + math.sin(ang) * e.r * 1.25), 2)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .6 + math.sin(e.t * 6) * .3), (int(x), int(y)), int(e.r * .32))
        pygame.draw.circle(surf, COL['white'], (int(x), int(y)), int(e.r * .12))
    elif e.kind == 'spark':
        a = e.t * 3
        pts = []
        for k in range(3):
            ang = a + k * math.pi * 2 / 3
            pts.append((x + math.cos(ang) * e.r, y + math.sin(ang) * e.r))
        pygame.draw.polygon(surf, (74, 44, 14), pts)
        pygame.draw.polygon(surf, col, pts, 1)
        pygame.draw.circle(surf, COL['white'], (int(x), int(y)), int(e.r * .35))
    elif e.kind == 'marc':
        pts = []
        for k in range(8):
            ang = k * math.pi / 4 + e.t * .25
            rr = e.r * (1.18 if k % 2 == 0 else .82)
            pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
        pygame.draw.polygon(surf, (50, 18, 28), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .7), (int(x), int(y)), int(e.r * .4))
        pygame.draw.circle(surf, COL['white'], (int(x), int(y)), int(e.r * .15))
    elif e.kind == 'splitter':
        for k in (-1, 1):
            cx = x + k * e.r * .46
            pygame.draw.circle(surf, (54, 22, 24), (int(cx), int(y)), int(e.r * .6))
            pygame.draw.circle(surf, COL['white'] if fl else col, (int(cx), int(y)), int(e.r * .6), 2)
            pygame.draw.circle(surf, mix(COL['bg0'], col, .5), (int(cx), int(y)), int(e.r * .24), 1)
        pygame.draw.line(surf, mix(COL['bg0'], col, .7), (x - 3, y - e.r * .55), (x + 3, y + e.r * .55), 1)
    elif e.kind == 'orbiter':
        for k in range(3):
            a = e.t * 2.6 + k * math.pi * 2 / 3
            pygame.draw.circle(surf, mix(COL['bg0'], col, .45),
                               (int(x + math.cos(a) * e.r * 1.35),
                                int(y + math.sin(a) * e.r * 1.35)), 2, 1)
        pygame.draw.circle(surf, (48, 38, 12), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .7), (int(x), int(y)), int(e.r * .42))
    elif e.kind == 'charger':
        a = e.ang if e.state == 2 else math.pi / 2
        tip = (x + math.cos(a) * e.r * 1.85, y + math.sin(a) * e.r * 1.85)
        l1 = (x + math.cos(a + 2.4) * e.r, y + math.sin(a + 2.4) * e.r)
        l2 = (x + math.cos(a - 2.4) * e.r, y + math.sin(a - 2.4) * e.r)
        pygame.draw.polygon(surf, (36, 18, 52), [tip, l1, l2])
        pygame.draw.polygon(surf, COL['white'] if fl else col, [tip, l1, l2], 2)
        if e.state == 1:
            pygame.draw.circle(surf, mix(COL['bg0'], COL['coral'], .8), (int(x), int(y)), int(e.r * 1.4), 1)
        pygame.draw.circle(surf, col, (int(x), int(y)), int(e.r * .3))
    elif e.kind == 'weaver':
        for k in range(6):
            a = k * math.pi / 3 + e.t * .35
            pygame.draw.line(surf, mix(COL['bg0'], col, .42),
                             (x + math.cos(a) * e.r * .5, y + math.sin(a) * e.r * .5),
                             (x + math.cos(a + .4) * e.r * 1.65, y + math.sin(a + .4) * e.r * 1.65), 1)
        pygame.draw.circle(surf, (12, 38, 28), (int(x), int(y)), int(e.r * .7))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r * .7), 2)
        pygame.draw.circle(surf, col, (int(x), int(y)), int(e.r * .26))
    elif e.kind == 'bulwark':
        pts = []
        for k in range(8):
            ang = k * math.pi / 4 + .39
            pts.append((x + math.cos(ang) * e.r, y + math.sin(ang) * e.r))
        pygame.draw.polygon(surf, mix(COL['bg1'], col, .30), pts)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .55), (int(x), int(y)), int(e.r * .52))
        pygame.draw.polygon(surf, COL['white'] if fl else mix(col, COL['white'], .35), pts, 3)
        for k in range(4):
            ang = k * math.pi / 2 + math.sin(e.t * .5) * .18
            pygame.draw.line(surf, mix(COL['white'], col, .4),
                             (x + math.cos(ang) * e.r * .42, y + math.sin(ang) * e.r * .42),
                             (x + math.cos(ang) * e.r * .96, y + math.sin(ang) * e.r * .96), 2)
        pygame.draw.circle(surf, mix(COL['bg1'], COL['ink'], .4), (int(x), int(y)), int(e.r * .26), 1)
        if e.state == 0:
            pygame.draw.circle(surf, mix(COL['bg0'], COL['steel'], .9), (int(x), int(y)),
                               int(e.r * .8), 1)
        else:
            bb = .45 + math.sin(e.t * 9) * .3
            pygame.draw.circle(surf, mix(COL['bg0'], COL['coral'], bb), (int(x), int(y)),
                               int(e.r * .82), 2)
    elif e.kind == 'spinner':
        for s in (0, 1):
            a = e.ang + s * math.pi
            tipx = x + math.cos(a) * e.r * 1.95
            tipy = y + math.sin(a) * e.r * 1.95
            p1 = (x + math.cos(a + .55) * e.r * .55, y + math.sin(a + .55) * e.r * .55)
            p2 = (x + math.cos(a - .55) * e.r * .55, y + math.sin(a - .55) * e.r * .55)
            pygame.draw.polygon(surf, mix(COL['bg1'], col, .55), [(tipx, tipy), p1, p2])
            pygame.draw.polygon(surf, mix(COL['white'], col, .3), [(tipx, tipy), p1, p2], 1)
        pygame.draw.circle(surf, mix(COL['bg1'], col, .28), (int(x), int(y)), int(e.r * .62))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r * .62), 2)
        pygame.draw.circle(surf, col, (int(x), int(y)), int(e.r * .2))
        pygame.draw.circle(surf, mix(COL['white'], col, .35), (int(x), int(y)), 2)
    elif e.kind == 'bomber':
        f = clamp(e.t / 4.6, 0, 1)
        bb = .3 + abs(math.sin(e.t * (5 + f * 16))) * .55
        pygame.draw.circle(surf, mix(COL['bg0'], col, bb), (int(x), int(y)), int(e.r * .85))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r * .85), 2)
        pygame.draw.arc(surf, mix(COL['bg0'], COL['gold'], .85),
                        (x - e.r, y - e.r, e.r * 2, e.r * 2), 1.57, 1.57 + 6.28 * (1 - f), 2)
        pygame.draw.circle(surf, COL['white'], (int(x), int(y)), 2)
    elif e.kind == 'sniper':
        pygame.draw.circle(surf, (10, 42, 46), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        pygame.draw.line(surf, mix(COL['bg0'], col, .8), (x - e.r, y), (x + e.r, y), 1)
        pygame.draw.line(surf, mix(COL['bg0'], col, .8), (x, y - e.r), (x, y + e.r), 1)
        if e.state == 1:
            k = 1 - max(0, e.ct) / .95
            ex = x + math.cos(e.ang) * 900
            ey = y + math.sin(e.ang) * 900
            pygame.draw.line(surf, mix(COL['bg0'], COL['coral'], .3 + k * .55),
                             (x, y), (ex, ey), 1 + int(k * 2))
    elif e.kind == 'dart':
        a = e.ang if e.state else (e.t * 2 + e.ph)
        pts = [(x + math.cos(a) * (e.r + 6), y + math.sin(a) * (e.r + 6)),
               (x + math.cos(a + 2.4) * e.r, y + math.sin(a + 2.4) * e.r),
               (x + math.cos(a - 2.4) * e.r, y + math.sin(a - 2.4) * e.r)]
        pygame.draw.polygon(surf, mix(COL['bg0'], col, .55 if fl else .25), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)
        if e.state == 1:
            pygame.draw.line(surf, mix(COL['bg0'], COL['coral'], .5),
                             (x, y), (x + math.cos(e.ang) * 220, y + math.sin(e.ang) * 220), 1)
    elif e.kind == 'spawner':
        pygame.draw.circle(surf, (14, 10, 34), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        for k in range(3):
            aa = e.t * 1.7 + k * 2.094
            pygame.draw.circle(surf, mix(COL['bg0'], col, .75),
                               (int(x + math.cos(aa) * e.r * .55),
                                int(y + math.sin(aa) * e.r * .55)), 4, 1)
        pp = .5 + .5 * math.sin(e.t * 4)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['gold'], .3 + pp * .5),
                           (int(x), int(y)), int(4 + pp * 5))
    elif e.kind == 'laser':
        pygame.draw.circle(surf, (26, 12, 12), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        if e.state == 1:
            k = 1 - max(0, e.ct) / 1.1
            pygame.draw.line(surf, mix(COL['bg0'], COL['coral'], .25 + k * .6),
                             (x, y), (x, H), 1 + int(k * 2))
        elif e.state == 2:
            k = max(0, e.beam_life) / .6
            pygame.draw.rect(surf, mix(COL['bg0'], COL['coral'], .55 + k * .4),
                             (x - 8, y, 16, H - y))
            pygame.draw.rect(surf, COL['white'], (x - 2, y, 4, H - y))
            glow_at(surf, COL['coral'], x, y + 80, 120, 2)
    elif e.kind == 'orb':
        pygame.draw.circle(surf, mix(COL['bg0'], col, .3), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .7), (int(x), int(y)), int(e.r * .45), 1)
    elif e.kind == 'sweeper':
        pygame.draw.circle(surf, (40, 14, 16), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        for k in range(4):
            a = e.t * 1.4 + k * math.pi / 2
            pygame.draw.line(surf, mix(COL['bg0'], col, .7),
                             (x + math.cos(a) * e.r * .45, y + math.sin(a) * e.r * .45),
                             (x + math.cos(a) * e.r * 1.3, y + math.sin(a) * e.r * 1.3), 2)
        if e.state == 1:
            bx = x + math.cos(e.ang) * 520
            by = y + math.sin(e.ang) * 520
            pygame.draw.line(surf, mix(COL['bg0'], COL['coral'], .55), (x, y), (bx, by), 3)
            pygame.draw.line(surf, COL['white'], (x, y), (bx, by), 1)
            glow_at(surf, COL['coral'], x + math.cos(e.ang) * 70,
                    y + math.sin(e.ang) * 70, 60, 2)
    elif e.kind == 'warden':
        pts = []
        for k in range(6):
            a = e.t * .22 + k * math.pi / 3
            pts.append((x + math.cos(a) * e.r, y + math.sin(a) * e.r))
        pygame.draw.polygon(surf, mix(COL['bg1'], col, .35), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .45), (int(x), int(y)),
                           int(e.r * 1.55), 1)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['aqua'], .35), (int(x), int(y)),
                           210, 1)
        pygame.draw.circle(surf, col, (int(x), int(y)), int(e.r * .28))
    elif e.kind == 'siphoner':
        pygame.draw.circle(surf, (20, 12, 36), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        for k in range(3):
            a = e.t * 1.8 + k * math.pi * 2 / 3
            pygame.draw.circle(surf, mix(COL['bg0'], col, .6),
                               (int(x + math.cos(a) * e.r * .62),
                                int(y + math.sin(a) * e.r * .62)), 4, 1)
        p = G.player
        if p and dist2((e.x, e.y), (p.x, p.y)) < 380 ** 2:
            px, py = p.x + ox, p.y + oy
            pygame.draw.line(surf, mix(COL['bg0'], col, .65), (x, y), (px, py), 2)
            pygame.draw.circle(surf, mix(COL['bg0'], COL['white'], .5), (int(px), int(py)), 2)
    elif e.kind == 'spear':
        pts = [(x + math.cos(e.t * .6 + k * math.pi * .5) * e.r,
                y + math.sin(e.t * .6 + k * math.pi * .5) * e.r) for k in range(4)]
        pygame.draw.polygon(surf, mix(COL['bg1'], col, .35), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)
        tipx, tipy = x + math.cos(e.ang) * e.r * 2.3, y + math.sin(e.ang) * e.r * 2.3
        pygame.draw.line(surf, col, (x, y), (tipx, tipy), 2)
        if e.state == 1:
            pygame.draw.line(surf, mix(COL['bg0'], COL['green'], .55), (x, y),
                             (x + math.cos(e.ang) * 620, y + math.sin(e.ang) * 620), 1)
    elif e.kind == 'miner':
        pygame.draw.circle(surf, (32, 24, 8), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        for k in range(4):
            a = e.t * 1.1 + k * math.pi * .5
            pygame.draw.circle(surf, mix(COL['bg0'], col, .8),
                               (int(x + math.cos(a) * e.r * .65),
                                int(y + math.sin(a) * e.r * .65)), 3, 1)
        pp = .5 + .5 * math.sin(e.t * 5)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['amber'], .3 + pp * .5),
                           (int(x), int(y)), int(3 + pp * 4))
    elif e.kind == 'titan':
        pts = []
        for k in range(6):
            a = e.t * .25 + k * math.pi / 3
            pts.append((x + math.cos(a) * e.r, y + math.sin(a) * e.r))
        pygame.draw.polygon(surf, (26, 24, 26), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 3)
        for k in range(3):
            a = e.t * 1.3 + k * math.pi * 2 / 3
            pygame.draw.circle(surf, mix(COL['bg0'], COL['amber'], .7),
                               (int(x + math.cos(a) * e.r * .55),
                                int(y + math.sin(a) * e.r * .55)), 5, 1)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .55), (int(x), int(y)), int(e.r * .3))
    elif e.kind == 'drake':
        pts = [(x, y - e.r * 1.2),
               (x + e.r * 1.5, y - e.r * .2),
               (x + e.r * .55, y + e.r * .9),
               (x, y + e.r * .35),
               (x - e.r * .55, y + e.r * .9),
               (x - e.r * 1.5, y - e.r * .2)]
        pygame.draw.polygon(surf, mix(COL['bg1'], col, .32), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .8), (int(x), int(y)), int(e.r * .35))
    elif e.kind == 'mortar':
        pygame.draw.circle(surf, (22, 24, 26), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        for k in range(3):
            a = e.t * .7 + k * math.pi * 2 / 3
            pygame.draw.circle(surf, mix(COL['bg0'], COL['steel'], .7),
                               (int(x + math.cos(a) * e.r * .55),
                                int(y + math.sin(a) * e.r * .55)), 4, 1)
        pygame.draw.line(surf, col, (x, y), (x + math.cos(e.ang) * e.r * 1.6,
                                              y + math.sin(e.ang) * e.r * 1.6), 4)
    elif e.kind == 'shade':
        k = .5 + .5 * math.sin(e.t * 8 + e.ph)
        pts = [(x, y - e.r), (x + e.r, y), (x, y + e.r), (x - e.r, y)]
        pygame.draw.polygon(surf, mix(COL['bg1'], col, .18 + k * .18), pts)
        pygame.draw.polygon(surf, mix(COL['bg0'], col, .5 + k * .4), pts, 1)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['white'], .3 + k * .3),
                           (int(x), int(y)), 3)
    elif e.kind == 'wisp':
        fl2 = .6 + .4 * math.sin(e.t * 7 + e.ph)
        for side in (-1, 1):
            pts = [(x, y),
                   (x + side * e.r * 1.55, y - e.r * .75),
                   (x + side * e.r * 1.1, y + e.r * .2)]
            pygame.draw.polygon(surf, mix(COL['bg1'], col, .22 + fl2 * .18), pts)
            pygame.draw.polygon(surf, mix(COL['bg0'], col, .6 + fl2 * .3), pts, 1)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .35 + fl2 * .3), (int(x), int(y)), int(e.r * .55))
        pygame.draw.circle(surf, COL['white'], (int(x), int(y)), 2)
        glow_at(surf, COL['white'], x, y, 26, .7)
    elif e.kind == 'webber':
        pygame.draw.circle(surf, (5, 22, 16), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        for k in range(6):
            a0 = e.t * .35 + k * math.pi / 3
            a1 = a0 + math.pi / 3
            pygame.draw.line(surf, mix(COL['bg0'], col, .55),
                             (x + math.cos(a0) * e.r * .35, y + math.sin(a0) * e.r * .35),
                             (x + math.cos(a0) * e.r * 1.35, y + math.sin(a0) * e.r * 1.35), 1)
            pygame.draw.line(surf, mix(COL['bg0'], col, .35),
                             (x + math.cos(a0) * e.r * 1.35, y + math.sin(a0) * e.r * 1.35),
                             (x + math.cos(a1) * e.r * 1.35, y + math.sin(a1) * e.r * 1.35), 1)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['green'], .8), (int(x), int(y)), int(e.r * .28))
    elif e.kind == 'juggernaut':
        pts = []
        for k in range(8):
            a = e.t * .18 + k * math.pi / 4
            rr = e.r * (1.0 if k % 2 == 0 else .82)
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
        pygame.draw.polygon(surf, (26, 10, 12), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 3)
        pygame.draw.circle(surf, mix(COL['bg0'], col, .35), (int(x), int(y)), int(e.r * .62), 2)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['amber'], .8), (int(x), int(y)), int(e.r * .24))
        for k in range(4):
            a = e.t * 1.1 + k * math.pi / 2
            pygame.draw.circle(surf, mix(COL['bg0'], col, .8),
                               (int(x + math.cos(a) * e.r * .72),
                                int(y + math.sin(a) * e.r * .72)), 4, 1)
    elif e.kind == 'prism':
        pts = []
        for k in range(3):
            a = e.t * .9 + k * math.pi * 2 / 3
            pts.append((x + math.cos(a) * e.r * 1.2, y + math.sin(a) * e.r * 1.2))
        pygame.draw.polygon(surf, mix(COL['bg1'], col, .28), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)
        for k in range(3):
            a = e.t * .9 + k * math.pi * 2 / 3
            pygame.draw.line(surf, mix(COL['bg0'], COL['aqua'], .7), (x, y),
                             (x + math.cos(a) * e.r * 1.5, y + math.sin(a) * e.r * 1.5), 1)
        pygame.draw.circle(surf, COL['white'], (int(x), int(y)), 2)
    elif e.kind == 'hive':
        pts = []
        for k in range(6):
            a = e.t * .25 + k * math.pi / 3
            pts.append((x + math.cos(a) * e.r, y + math.sin(a) * e.r))
        pygame.draw.polygon(surf, (32, 22, 7), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 3)
        for k in range(4):
            a = e.t * 1.0 + k * math.pi / 2
            pygame.draw.circle(surf, mix(COL['bg0'], col, .75),
                               (int(x + math.cos(a) * e.r * .5),
                                int(y + math.sin(a) * e.r * .5)), 5, 1)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['amber'], .9), (int(x), int(y)), 3)
    elif e.kind == 'lancer':
        pts = [(x + math.cos(e.ang) * e.r * 1.8, y + math.sin(e.ang) * e.r * 1.8),
               (x + math.cos(e.ang + 2.3) * e.r, y + math.sin(e.ang + 2.3) * e.r),
               (x + math.cos(e.ang - 2.3) * e.r, y + math.sin(e.ang - 2.3) * e.r)]
        pygame.draw.polygon(surf, mix(COL['bg1'], col, .3), pts)
        pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)
        pygame.draw.line(surf, mix(COL['bg0'], col, .8), (x, y),
                         (x - math.cos(e.ang) * e.r * 2.4, y - math.sin(e.ang) * e.r * 2.4), 2)
        if e.state == 1:
            pygame.draw.line(surf, mix(COL['bg0'], COL['white'], .3), (x, y),
                             (x + math.cos(e.ang) * 180, y + math.sin(e.ang) * 180), 1)
    elif e.kind == 'cryo':
        pygame.draw.circle(surf, (7, 24, 32), (int(x), int(y)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y)), int(e.r), 2)
        for k in range(6):
            a = e.t * .6 + k * math.pi / 3
            pygame.draw.line(surf, mix(COL['bg0'], col, .85), (x, y),
                             (x + math.cos(a) * e.r * 1.35, y + math.sin(a) * e.r * 1.35), 2)
            pygame.draw.line(surf, mix(COL['bg0'], COL['white'], .5),
                             (x + math.cos(a) * e.r * .65, y + math.sin(a) * e.r * .65),
                             (x + math.cos(a + .5) * e.r * .95, y + math.sin(a + .5) * e.r * .95), 1)
    elif e.kind == 'torch':
        pygame.draw.circle(surf, (30, 16, 8), (int(x), int(y + e.r * .5)), int(e.r))
        pygame.draw.circle(surf, COL['white'] if fl else col, (int(x), int(y + e.r * .5)), int(e.r), 2)
        for k in range(3):
            a = e.t * 3 + k * math.pi * 2 / 3
            hh = e.r * (.7 + .35 * math.sin(e.t * 9 + k))
            pygame.draw.line(surf, mix(COL['bg0'], COL['amber'], .8),
                             (x + math.cos(a) * e.r * .3, y + e.r * .2),
                             (x + math.cos(a) * e.r * .7, y - hh), 2)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['white'], .8), (int(x), int(y)), 3)
    elif e.kind == 'voidling':
        kk = .5 + .5 * math.sin(e.t * 6 + e.ph)
        pygame.draw.circle(surf, mix(COL['bg1'], col, .16 + kk * .12),
                           (int(x), int(y)), int(e.r * 1.15))
        pygame.draw.circle(surf, mix(COL['bg0'], col, .6 + kk * .3),
                           (int(x), int(y)), int(e.r), 2)
        for k in range(5):
            a = e.t * 1.7 + k * math.pi * 2 / 5
            pygame.draw.line(surf, mix(COL['bg0'], col, .55),
                             (x + math.cos(a) * e.r * .5, y + math.sin(a) * e.r * .5),
                             (x + math.cos(a) * e.r * 1.45, y + math.sin(a) * e.r * 1.45), 2)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['white'], .4 + kk * .4),
                           (int(x), int(y)), 3)

    if e.elite:
        rr = e.r * 1.55
        for k in range(8):
            a0 = e.t * 1.9 + k * math.pi / 4
            pygame.draw.line(surf, mix(COL['bg2'], COL['gold'], .85),
                             (x + math.cos(a0) * rr, y + math.sin(a0) * rr),
                             (x + math.cos(a0 + .32) * rr, y + math.sin(a0 + .32) * rr), 2)
    if e.burn_t > 0:
        bb = .45 + math.sin(e.t * 18) * .3
        pygame.draw.circle(surf, mix(COL['bg0'], COL['amber'], bb),
                           (int(x), int(y - e.r - 4)), 2)

    # 血条（受伤才显示）
    if e.hp < e.maxhp:
        w = e.r * 1.6
        pygame.draw.rect(surf, (20, 40, 46), (x - w / 2, y - e.r - 9, w, 3))
        pygame.draw.rect(surf, mix(COL['coral'], col, e.hp / e.maxhp),
                         (x - w / 2, y - e.r - 9, w * max(0, e.hp / e.maxhp), 3))


def draw_boss(surf, b, ox, oy):
    x, y = b.x + ox, b.y + oy
    col = COL[b.cfg['col']]
    fl = b.flash > 0
    if b.enter:
        k = clamp((b.y + 170) / 300.0, 0, 1)
        pygame.draw.line(surf, mix(COL['bg0'], col, .4), (x, 0), (x, max(0, y)), 7)
        pygame.draw.line(surf, mix(COL['bg0'], COL['white'], .3), (x, 0), (x, max(0, y)), 2)
        for i in range(3):
            pygame.draw.circle(surf, mix(COL['bg0'], col, .45 - i * .1),
                               (int(x), int(y)), int(b.r * (1.1 + k * 1.4 + i * .35)), 1)
    glow_at(surf, COL['white'] if fl else col, x, y, b.r * 3.4, 2)

    # 触须
    for k in range(12):
        ang = k * math.pi * 2 / 12 + b.rot * .6
        L = b.r * (1.55 + math.sin(b.t * 1.6 + k) * .16)
        p0 = (x + math.cos(ang) * b.r * .82, y + math.sin(ang) * b.r * .82)
        p1 = (x + math.cos(ang + .22) * b.r * 1.3, y + math.sin(ang + .22) * b.r * 1.3)
        p2 = (x + math.cos(ang - .12) * L, y + math.sin(ang - .12) * L)
        pygame.draw.lines(surf, mix(COL['bg0'], col, .5), False, quad_points(p0, p1, p2, 8), 1)

    # 甲壳
    pts = []
    for k in range(10):
        ang = k * math.pi * 2 / 10 + b.rot * .18
        rr = b.r * (1.0 if k % 2 == 0 else .84)
        pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
    pygame.draw.polygon(surf, (16, 18, 22), pts)
    pygame.draw.polygon(surf, COL['white'] if fl else col, pts, 2)

    # 内环
    for k in range(3):
        rr = b.r * (.42 + k * .16)
        pygame.draw.arc(surf, mix(COL['bg0'], COL['white'], .22),
                        (x - rr, y - rr, rr * 2, rr * 2), k + b.rot, k + b.rot + 1.4, 1)

    # 后三位 BOSS 的专属轮廓
    if b.pattern == 6:
        for k in range(10):
            ang = k * math.pi / 5 + b.rot * .5
            r0 = b.r * 1.02
            r1 = b.r * (1.42 + math.sin(b.t * 2 + k) * .2)
            p0 = (x + math.cos(ang) * r0, y + math.sin(ang) * r0)
            p1 = (x + math.cos(ang + .16) * r1, y + math.sin(ang + .16) * r1)
            p2 = (x + math.cos(ang - .16) * r1, y + math.sin(ang - .16) * r1)
            pygame.draw.polygon(surf, mix(COL['bg0'], col, .55), [p0, p1, p2], 0)
            pygame.draw.polygon(surf, mix(COL['bg0'], COL['white'], .35), [p0, p1, p2], 1)
    elif b.pattern == 7:
        sq = [(x + math.cos(b.rot * .3 + k * math.pi / 2) * b.r * 1.15,
               y + math.sin(b.rot * .3 + k * math.pi / 2) * b.r * 1.15) for k in range(4)]
        pygame.draw.polygon(surf, mix(COL['bg0'], col, .35), sq, 0)
        pygame.draw.polygon(surf, COL['white'] if fl else col, sq, 2)
        for k in range(4):
            ang = b.rot * .3 + k * math.pi / 2
            pygame.draw.rect(surf, mix(COL['bg0'], col, .8),
                             (x + math.cos(ang) * b.r * 1.18 - 5,
                              y + math.sin(ang) * b.r * 1.18 - 5, 10, 10))
    elif b.pattern == 8:
        for k in range(3):
            rr = b.r * (1.25 + k * .2) + math.sin(b.t * 1.4 + k) * 4
            pygame.draw.arc(surf, mix(COL['bg0'], col, .65 - k * .14),
                            (x - rr, y - rr, rr * 2, rr * 2), b.rot * (1 + k), b.rot * (1 + k) + 2.4, 2)
        for k in range(8):
            ang = -b.rot * 1.4 + k * math.pi / 4
            pygame.draw.line(surf, mix(COL['bg0'], COL['gold'], .6),
                             (x + math.cos(ang) * b.r * .9, y + math.sin(ang) * b.r * .9),
                             (x + math.cos(ang) * b.r * 1.4, y + math.sin(ang) * b.r * 1.4), 1)

    if b.kind == 21:
        # 静默观测者：三层观测环 + 一只不眨的透镜
        for k in range(3):
            rr = b.r * (1.05 + k * .28)
            pygame.draw.arc(surf, mix(COL['bg0'], COL['aqua'], .55 - k * .12),
                            (x - rr, y - rr, rr * 2, rr * 2), b.rot * (.6 + k * .3),
                            b.rot * (.6 + k * .3) + 2.7, 2)
        for k in range(6):
            a = b.rot * .35 + k * math.pi / 3
            pygame.draw.line(surf, mix(COL['bg0'], COL['white'], .3),
                             (x + math.cos(a) * b.r * .7, y + math.sin(a) * b.r * .7),
                             (x + math.cos(a) * b.r * 1.55, y + math.sin(a) * b.r * 1.55), 1)
        pygame.draw.ellipse(surf, (5, 14, 20), (x - b.r * .8, y - b.r * .34, b.r * 1.6, b.r * .68))
        pygame.draw.ellipse(surf, mix(COL['bg0'], COL['aqua'], .8),
                            (x - b.r * .8, y - b.r * .34, b.r * 1.6, b.r * .68), 2)
    elif b.kind == 22:
        # 铸世者：铁砧与两柄锻锤
        hexp = [(x + math.cos(b.rot * .2 + k * math.pi / 3) * b.r * .95,
                 y + math.sin(b.rot * .2 + k * math.pi / 3) * b.r * .95) for k in range(6)]
        pygame.draw.polygon(surf, (36, 26, 8), hexp)
        pygame.draw.polygon(surf, mix(COL['bg0'], COL['gold'], .9), hexp, 3)
        for side in (-1, 1):
            hx = x + side * b.r * 1.35
            hy = y + math.sin(b.t * 1.9 + side) * b.r * .25
            pygame.draw.line(surf, mix(COL['bg0'], COL['white'], .45),
                             (hx, hy - b.r * .55), (hx, hy + b.r * .1), 4)
            pygame.draw.rect(surf, mix(COL['bg0'], COL['amber'], .85),
                             (hx - b.r * .34, hy, b.r * .68, b.r * .34))
        for k in range(14):
            a = b.rot * 1.3 + k * math.pi * 2 / 14
            rr = b.r * (1.5 + .2 * math.sin(b.t * 5 + k))
            pygame.draw.circle(surf, mix(COL['bg0'], COL['gold'], .65),
                               (int(x + math.cos(a) * rr), int(y + math.sin(a) * rr)), 2)
    elif b.kind == 23:
        # 门后的东西：身后的门框与门缝里的触须
        fw, fh = b.r * 1.9, b.r * 2.2
        pygame.draw.rect(surf, (10, 10, 16), (x - fw / 2, y - fh * .62, fw, fh))
        pygame.draw.rect(surf, mix(COL['bg0'], COL['white'], .7),
                         (x - fw / 2, y - fh * .62, fw, fh), 3)
        for k in range(9):
            a = b.t * 1.1 + k * math.pi * 2 / 9
            pygame.draw.line(surf, mix(COL['bg0'], COL['violet'], .55),
                             (x + math.cos(a) * b.r * .12, y + math.sin(a) * b.r * .12),
                             (x + math.cos(a) * b.r * .95, y + math.sin(a) * b.r * .95), 2)
            pygame.draw.circle(surf, mix(COL['bg0'], COL['white'], .75),
                               (int(x + math.cos(a) * b.r * .18),
                                int(y + math.sin(a) * b.r * .18)), 2)
    elif b.kind == 24:
        # 盐圣：盐柱王座与结晶冠
        for k in range(7):
            a = b.rot * .2 + k * math.pi * 2 / 7
            px = x + math.cos(a) * b.r * 1.05
            py = y + math.sin(a) * b.r * 1.05
            h = b.r * (.55 + .2 * math.sin(b.t * 2 + k))
            pygame.draw.polygon(surf, mix(COL['bg0'], col, .5),
                                [(px, py - h), (px - b.r * .18, py), (px + b.r * .18, py)])
            pygame.draw.polygon(surf, mix(COL['bg0'], COL['white'], .45),
                                [(px, py - h), (px - b.r * .18, py), (px + b.r * .18, py)], 1)
        pygame.draw.line(surf, mix(COL['bg0'], COL['gold'], .5),
                         (x, y - b.r * 1.6), (x, y + b.r * 1.2), 3)
    elif b.kind == 25:
        # 齿轮圣像：双层齿轮与咬合齿
        for ring, teeth, rr in ((0, 14, b.r * 1.25), (1, 10, b.r * .78)):
            for k in range(teeth):
                a = b.rot * (.55 if ring == 0 else -.85) + k * math.pi * 2 / teeth
                x0 = x + math.cos(a) * rr
                y0 = y + math.sin(a) * rr
                x1 = x + math.cos(a) * (rr + b.r * .18)
                y1 = y + math.sin(a) * (rr + b.r * .18)
                pygame.draw.line(surf, mix(COL['bg0'], col, .8), (x0, y0), (x1, y1), 3)
            pygame.draw.circle(surf, mix(COL['bg0'], col, .45), (int(x), int(y)), int(rr), 2)
    elif b.kind == 26:
        # 虚数鲸：椭圆鲸体、尾鳍与分裂的潮汐环
        pygame.draw.ellipse(surf, mix(COL['bg0'], col, .32),
                            (x - b.r * 1.4, y - b.r * .55, b.r * 2.8, b.r * 1.1))
        pygame.draw.ellipse(surf, mix(COL['bg0'], COL['white'], .55),
                            (x - b.r * 1.4, y - b.r * .55, b.r * 2.8, b.r * 1.1), 2)
        for side in (-1, 1):
            pygame.draw.polygon(surf, mix(COL['bg0'], col, .7),
                                [(x + side * b.r * 1.05, y),
                                 (x + side * b.r * 1.55, y - b.r * .5),
                                 (x + side * b.r * 1.45, y + b.r * .35)])
        for k in range(3):
            rr = b.r * (1.65 + k * .18)
            pygame.draw.arc(surf, mix(COL['bg0'], COL['white'], .28 - k * .06),
                            (x - rr, y - rr, rr * 2, rr * 2),
                            b.rot * (.7 + k) + math.pi * .2, b.rot * (.7 + k) + math.pi * 1.3, 1)
    elif b.kind == 27:
        # 终末之眼：巨大眼睑、虹膜与收束的视界线
        ew, eh = b.r * 2.5, b.r * 1.35
        pygame.draw.ellipse(surf, (12, 8, 14), (x - ew / 2, y - eh / 2, ew, eh))
        pygame.draw.ellipse(surf, mix(COL['bg0'], col, .8),
                            (x - ew / 2, y - eh / 2, ew, eh), 3)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['gold'], .55), (int(x), int(y)), int(b.r * .52))
        pygame.draw.circle(surf, (6, 4, 8), (int(x), int(y)), int(b.r * .3))
        pygame.draw.circle(surf, mix(COL['bg0'], COL['white'], .85), (int(x), int(y)), max(3, int(b.r * .09)))
        for k in range(10):
            a = -b.rot * .8 + k * math.pi * 2 / 10
            pygame.draw.line(surf, mix(COL['bg0'], COL['gold'], .35),
                             (x + math.cos(a) * b.r * .9, y + math.sin(a) * b.r * .55),
                             (x + math.cos(a) * b.r * 1.7, y + math.sin(a) * b.r * 1.05), 1)

    # 核心
    beat = 1 + math.sin(b.t * (7 if b.phase == 3 else 3.6)) * .1
    core = b.r * .3 * beat
    glow_at(surf, col, x, y, core * 5, 2)
    pygame.draw.circle(surf, COL['white'], (int(x), int(y)), int(core))
    # 眼
    pygame.draw.ellipse(surf, (8, 10, 14), (x - core * .62, y - core * .3, core * 1.24, core * .6))
    pygame.draw.circle(surf, col, (int(x + math.sin(b.t * .8) * core * .2), int(y)), max(2, int(core * .13)))


def draw_well(surf, ox, oy):
    w = G.well
    if not w:
        return
    x, y = w['x'] + ox, w['y'] + oy
    k = w['t'] / w['max']
    glow_at(surf, COL['violet'], x, y, 170, 1)
    for i in range(3):
        rr = w['r'] * (.5 + .42 * k) * (1 - i * .27)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['violet'], .62 - i * .14),
                           (int(x), int(y)), int(rr), 1)
    for i in range(12):
        a = w['ang'] + i * math.pi / 6
        r0 = w['r'] * .32
        r1 = w['r'] * (.68 + .22 * math.sin(w['ang'] * 2 + i))
        pygame.draw.line(surf, mix(COL['bg1'], COL['violet'], .6),
                         (x + math.cos(a) * r0, y + math.sin(a) * r0),
                         (x + math.cos(a) * r1, y + math.sin(a) * r1), 1)


def draw_bullets(surf, ox, oy):
    for b in G.eb:
        x, y = b['x'] + ox, b['y'] + oy
        col = COL[b['col']]
        if b.get('kind') == 'mine':
            pp = .5 + .5 * math.sin(b['t'] * 7)
            pygame.draw.circle(surf, mix(COL['bg0'], col, .5 + pp * .4),
                               (int(x), int(y)), int(b['r'] + 4 + pp * 4), 1)
            glow_at(surf, col, x, y, 24, 2)
            pygame.draw.circle(surf, col, (int(x), int(y)), int(b['r'] * .45))
            continue
        dx, dy = b['vx'], b['vy']
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        pygame.draw.line(surf, mix(COL['bg0'], col, .34),
                         (x - ux * (8 + b['r']), y - uy * (8 + b['r'])), (x, y), 1)
        glow_at(surf, col, x, y, b['r'] * 4.2, 2)
        pygame.draw.circle(surf, mix(COL['white'], col, .35), (int(x), int(y)), int(b['r'] * .55))
        pygame.draw.circle(surf, mix(COL['bg0'], col, .7), (int(x), int(y)), int(b['r']), 1)
    for b in G.pb:
        x, y = b['x'] + ox, b['y'] + oy
        col = COL['gold'] if b.get('crit') else COL[G.run.ship.get('col', 'amber')]
        if b.get('drone'):
            col = COL['violet']
        if b.get('kind') == 'pmine':
            pp = .5 + .5 * math.sin(G.t * 12)
            pygame.draw.circle(surf, mix(COL['bg0'], col, .35 + pp * .35),
                               (int(x), int(y)), int(7 + pp * 3), 1)
            pygame.draw.circle(surf, col, (int(x), int(y)), 4, 1)
            pygame.draw.circle(surf, COL['white'], (int(x), int(y)), 2)
            continue
        if b.get('kind') == 'blade':
            a = math.atan2(b['vy'], b['vx'])
            ux, uy = math.cos(a), math.sin(a)
            size = b['r'] * 1.8 + 5
            side = b['r'] * .9 + 2
            pts = [(x + ux * size, y + uy * size),
                   (x - ux * size * .35 - uy * side, y - uy * size * .35 + ux * side),
                   (x - ux * size * .7, y - uy * size * .7),
                   (x - ux * size * .35 + uy * side, y - uy * size * .35 - ux * side)]
            glow_at(surf, col, x, y, 26, 1)
            pygame.draw.polygon(surf, col, pts, 0)
            pygame.draw.polygon(surf, mix(COL['white'], col, .55), pts, 1)
            continue
        if b.get('boomer'):
            a = math.atan2(b['vy'], b['vx'])
            pts = [(x + math.cos(a) * 13, y + math.sin(a) * 13),
                   (x + math.cos(a + 2.2) * 9, y + math.sin(a + 2.2) * 9),
                   (x + math.cos(a - 2.2) * 9, y + math.sin(a - 2.2) * 9)]
            glow_at(surf, COL['gold'], x, y, 34, 1)
            pygame.draw.polygon(surf, COL['gold'], pts, 0)
            pygame.draw.polygon(surf, COL['white'], pts, 1)
            continue
        dx, dy = b['vx'], b['vy']
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        glow_at(surf, col, x, y, 24, 1)
        pygame.draw.line(surf, mix(COL['white'], col, .35),
                         (x - ux * 11, y - uy * 11), (x + ux * 9, y + uy * 9), 2)
        pygame.draw.line(surf, COL['white'], (x - ux * 4, y - uy * 4), (x + ux * 4, y + uy * 4), 2)
        if b.get('crit'):
            pygame.draw.circle(surf, COL['gold'], (int(x), int(y)), 5, 1)
    for d in G.drones:
        x, y = d['x'] + ox, d['y'] + oy
        glow_at(surf, COL['violet'], x, y, 34, 1)
        pygame.draw.circle(surf, (30, 22, 50), (int(x), int(y)), 6)
        pygame.draw.circle(surf, COL['violet'], (int(x), int(y)), 6, 1)
        pygame.draw.circle(surf, COL['white'], (int(x), int(y)), 2)


def draw_drops(surf, ox=0, oy=0):
    for d in G.drops:
        col = COL[DROP_INFO[d['kind']][1]]
        x, y = d['x'] + ox, d['y'] + oy
        glow_at(surf, col, x, y, 40, 2)
        pts = [(x, y - 9), (x + 9, y), (x, y + 9), (x - 9, y)]
        pygame.draw.polygon(surf, col, pts, 1)
        pygame.draw.circle(surf, COL['white'], (int(x), int(y)), 3)


def draw_particles(surf, ox, oy):
    for p in G.parts:
        life_k = p['life'] / p['max']
        x, y = p['x'] + ox, p['y'] + oy
        if p.get('ring'):
            r = int(p.get('r', p.get('r0', 0)))
            if r <= 1:
                continue
            c = mix(COL['bg0'], COL[p['col']], life_k * .9)
            pygame.draw.circle(surf, c, (int(x), int(y)), r, max(1, int(p['w'] * (.4 + life_k * .8))))
        else:
            col = COL[p['col']]
            sz = p['size'] * (0.5 + life_k * .9)
            glow_at(surf, col, x, y, sz, 1)

    for b in G.beams:
        k = b['life'] / b['max']
        x = b['x'] + ox
        y = b['y'] + oy
        col = COL[b.get('col', 'green')]
        w = int(6 + 20 * k)
        if b.get('ang') is None:
            top = 0
            h = max(0, b['y'] + oy)
            c = mix(COL['bg0'], col, .85)
            pygame.draw.rect(surf, c, (int(x) - w // 2, top, w, h), 0)
            pygame.draw.rect(surf, COL['white'], (int(x) - 2, top, 4, h), 0)
            glow_at(surf, col, x, b['y'] + oy - 100, 160, 2)
        else:
            aim = b['ang']
            dx, dy = math.sin(aim), -math.cos(aim)
            ex, ey = x + dx * 1800, y + dy * 1800
            pygame.draw.line(surf, mix(COL['bg0'], col, .85), (int(x), int(y)),
                             (int(ex), int(ey)), w)
            pygame.draw.line(surf, COL['white'], (int(x), int(y)),
                             (int(ex), int(ey)), max(2, w // 4))
            glow_at(surf, col, x + dx * 220, y + dy * 220, 150, 2)


# ---------------------------------------------------------------- HUD
def draw_minimap(surf):
    """大图导航：世界、视野框、敌人、掉落、BOSS"""
    r = pygame.Rect(W - 180, H - 130, 150, 102)
    pygame.draw.rect(surf, (3, 10, 13), (r.x - 2, r.y - 18, r.w + 4, 18))
    pygame.draw.line(surf, mix(COL['bg1'], COL['dim'], .3), (r.x - 2, r.y - 1), (r.right + 2, r.y - 1), 1)
    pygame.draw.rect(surf, (5, 14, 18), r)
    pygame.draw.rect(surf, mix(COL['bg1'], COL['dim'], .45), r, 1)
    sx = (r.w - 8) / max(1, G.ww)
    sy = (r.h - 8) / max(1, G.wh)
    pygame.draw.rect(surf, mix(COL['bg0'], COL['aqua'], .25),
                     (r.x + 4, r.y + 4, int(W * sx), int(H * sy)), 1)
    for d in G.drops[:30]:
        pygame.draw.circle(surf, COL['gold'],
                           (int(r.x + 4 + d['x'] * sx), int(r.y + 4 + d['y'] * sy)), 1)
    for e in G.enemies:
        if e.dead:
            continue
        pygame.draw.circle(surf, COL['coral'] if not e.elite else COL['gold'],
                           (int(r.x + 4 + e.x * sx), int(r.y + 4 + e.y * sy)), 1)
    if G.landmark:
        lx = int(r.x + 4 + G.landmark['x'] * sx)
        ly = int(r.y + 4 + G.landmark['y'] * sy)
        pygame.draw.polygon(surf, COL['white'], [(lx, ly - 4), (lx + 4, ly), (lx, ly + 4), (lx - 4, ly)], 1)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['white'], .45), (lx, ly), 7, 1)
    for c in G.caches:
        if c.get('taken'):
            continue
        cx = int(r.x + 4 + c['x'] * sx)
        cy = int(r.y + 4 + c['y'] * sy)
        pygame.draw.circle(surf, COL['aqua'], (cx, cy), 2)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['aqua'], .4), (cx, cy), 5, 1)
    if G.boss:
        bx = int(r.x + 4 + G.boss.x * sx)
        by = int(r.y + 4 + G.boss.y * sy)
        pygame.draw.circle(surf, COL['gold'], (bx, by), 3)
        pygame.draw.circle(surf, mix(COL['bg0'], COL['gold'], .5), (bx, by), 6, 1)
    p = G.player
    if p:
        px = int(r.x + 4 + p.x * sx)
        py = int(r.y + 4 + p.y * sy)
        pygame.draw.polygon(surf, COL['aqua'], [(px, py - 3), (px + 2, py + 3), (px - 2, py + 3)])
    draw_text(surf, L('区域图', 'SECTOR'), 9, COL['dim'],
              (r.x + 6, r.y - 15))
    draw_text(surf, L('信标 %d/%d' % (G.cache_taken, G.cache_total),
                     'BEACON %d/%d' % (G.cache_taken, G.cache_total)),
              9, mix(COL['aqua'], COL['white'], .35), (r.x + r.w, r.y - 15), align='right')


HUD_SCRIM = None


def draw_aim_reticle(surf):
    """鼠标瞄准模式的准星，绘制在系统光标位置。"""
    if G.aim_mode != 'mouse':
        return
    x, y = G.pointer
    col = mix(COL['bg0'], COL['aqua'], .82)
    pygame.draw.circle(surf, col, (int(x), int(y)), 9, 1)
    pygame.draw.circle(surf, col, (int(x), int(y)), 2)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pygame.draw.line(surf, col, (int(x + dx * 13), int(y + dy * 13)),
                         (int(x + dx * 18), int(y + dy * 18)), 1)


def draw_hud(surf):
    global HUD_SCRIM
    if HUD_SCRIM is None:
        top = pygame.Surface((W, 150), pygame.SRCALPHA)
        bot = pygame.Surface((W, 120), pygame.SRCALPHA)
        for y in range(150):
            top.fill((2, 8, 12, int(120 * (1 - y / 150) ** 1.5)), (0, y, W, 1))
        for y in range(120):
            bot.fill((2, 8, 12, int(130 * (y / 120) ** 1.4)), (0, y, W, 1))
        HUD_SCRIM = (top, bot)
    surf.blit(HUD_SCRIM[0], (0, 0))
    surf.blit(HUD_SCRIM[1], (0, H - 120))
    run, p = G.run, G.player
    draw_text(surf, '第 %d 层 · %s' % (run.layer, theme_of(run.layer)['name']), 25,
              COL['ink'], (30, 18), bold=True)
    wp = waves_for_layer()
    for w in range(wp):
        wx = 32 + w * 17
        if w < run.wave - 1:
            pygame.draw.circle(surf, COL['aqua'], (wx, 63), 3)
        elif w == run.wave - 1:
            pygame.draw.circle(surf, COL['gold'], (wx, 63), 4)
            pygame.draw.circle(surf, mix(COL['bg0'], COL['gold'], .5), (wx, 63), 7, 1)
        else:
            pygame.draw.circle(surf, COL['dim'], (wx, 63), 3, 1)
    draw_text(surf, '第 %d / %d 波' % (run.wave, wp), 11, COL['dim'],
              (32 + wp * 17 + 6, 56))
    draw_text(surf, '增幅 %d  ·  %s' % (len(run.augs), run.mut.get('name', '未知层域')),
              11, mix(COL['bg0'], COL['gold'], .8), (30, 78))
    df = DIFFS[G.diff]
    draw_text(surf, '%s · %s · %s' % (run.mode_name, df['name'], df['en']), 10,
              mix(COL['bg0'], COL[df['col']], .9), (30, 98))
    draw_text(surf, '区域 · %s' % run.lmod['name'], 10,
              mix(COL['bg0'], COL['gold'], .82), (30, 114))
    draw_text(surf, '%d:%02d' % (int(run.time) // 60, int(run.time) % 60), 10,
              mix(COL['bg0'], COL['dim'], .7), (30, 130))
    draw_text(surf, '{:,}'.format(run.score), 26, COL['ink'], (W - 30, 16), align='right', bold=True)
    draw_text(surf, '击杀 %d' % run.kills, 11, COL['dim'], (W - 30, 50), align='right')
    draw_text(surf, 'SEED %06X' % run.seed, 10, mix(COL['bg0'], COL['dim'], .55),
              (W - 30, 68), align='right')
    if G.combo >= 3:
        k = min(1, G.combo_t / .9)
        draw_text(surf, '× %d 连击' % G.combo, 13, mix(COL['bg2'], COL['gold'], k),
                  (W - 30, 86), align='right', bold=True)

    # 艇体
    draw_text(surf, '瞄准 %s  ·  %s  ·  航向 %03d°' % (
        '自动' if G.aim_mode == 'auto' else '鼠标',
        'T 切回鼠标' if G.aim_mode == 'auto' else 'T 自动索敌',
        int(math.degrees(p.aim)) % 360),
              10, COL['dimmer'], (30, H - 80))
    draw_text(surf, 'HULL', 10, COL['dimmer'], (30, H - 62))
    for i in range(run.max_hp):
        x = 30 + i * 20
        r = pygame.Rect(x, H - 44, 14, 7)
        if i < p.hp:
            pygame.draw.rect(surf, COL['aqua'], r)
        else:
            pygame.draw.rect(surf, (22, 48, 54), r)
            pygame.draw.rect(surf, (40, 70, 78), r, 1)

    # 技能条
    bw = 330
    bx = W / 2 - bw / 2
    by = H - 40
    cd = G.run.ship['cd'] * G.run.st['cd']
    k = 1 - max(0, p.skill_t) / cd
    pygame.draw.rect(surf, (16, 36, 42), (bx, by, bw, 6))
    if k >= 1:
        pygame.draw.rect(surf, mix(COL['bg0'], COL['aqua'], .9), (bx, by, bw, 6))
    else:
        pygame.draw.rect(surf, mix(COL['bg0'], COL['aqua'], .45), (bx, by, bw * k, 6))
    draw_text(surf, '%s  ·  空格' % G.run.ship['skill'], 11, COL['dim'], (W / 2, by - 18), align='center')
    if k >= 1:
        draw_text(surf, '就绪', 11, COL['aqua'], (bx + bw + 10, by - 6))

    # BOSS
    b = G.boss
    if b:
        nbw = 520
        nbx = W / 2 - nbw / 2
        draw_text(surf, b.cfg['name'], 16, COL['gold'], (nbx, 20), bold=True)
        draw_text(surf, 'PHASE %s' % ('I' if b.phase == 1 else ('II' if b.phase == 2 else 'III')),
                  10, COL['dim'], (nbx + nbw, 24), align='right')
        pygame.draw.rect(surf, (26, 34, 30), (nbx, 44, nbw, 4))
        pygame.draw.rect(surf, mix(COL['coral'], COL['gold'], .4),
                         (nbx, 44, int(nbw * max(0, b.hp / b.maxhp)), 4))
        draw_text(surf, '绝技 · %s   %.1fs' % (b.sig_name, max(0, b.sig_t)),
                  11, COL['violet'], (nbx, 52))
        cap = layers_for_run()
        draw_text(surf, '第 %d 层 / %s' % (G.run.layer, ('%d' % cap) if cap else '∞'),
                  11, COL['dim'], (nbx + nbw, 52), align='right')
        if b.phase >= 2:
            draw_text(surf, '绝技 II · %s   %.1fs' % (b.sig2_name, max(0, b.sig2_t)),
                      10, COL['coral'], (nbx, 66))
        else:
            draw_text(surf, '绝技 II · 第二阶段解锁', 10, COL['dim'], (nbx, 66))

    draw_minimap(surf)

    # 横幅
    if G.scene != 'play':
        return
    if G.banner:
        bt = G.banner
        life = bt['life']
        k2 = 1 if bt['t'] > .3 and bt['t'] < life - .4 else min(1, bt['t'] / .3)
        c = mix(COL['bg2'], COL[bt['col']], k2)
        draw_text(surf, bt['s'], 17, c, (W / 2, H * .28), align='center', bold=True)
    if G.banner2:
        life = G.banner2.get('life', 1.9)
        a = 1 - G.banner2['t'] / life
        tw = text_w(G.banner2['s'], 15)
        plate = pygame.Surface((int(tw) + 34, 30), pygame.SRCALPHA)
        plate.fill((2, 8, 12, int(178 * a)))
        pygame.draw.line(plate, mix(COL['bg0'], COL[G.banner2['col']], a),
                         (6, 6), (6, 24), 2)
        surf.blit(plate, (int(W / 2 - tw / 2 - 17), int(H * .36 - 6)))
        draw_text(surf, G.banner2['s'], 15,
                  mix(COL['bg2'], COL[G.banner2['col']], a), (W / 2, H * .36), align='center')


THEME_BG = {}
SHAFT = None
ZONE_BG = {}
BG_GRAD = {}
_ZT = 512


def _zone_grad(layer):
    s = BG_GRAD.get(layer)
    if s:
        return s
    if len(BG_GRAD) > 20:
        BG_GRAD.clear()
    th = theme_of(layer)
    s = pygame.Surface((W, H))
    top, bot = th['top'], th['bot']
    for y in range(H):
        t = y / max(1, H - 1)
        t = t * t * (.7 + .3 * t)
        s.fill(mix(top, bot, t), (0, y, W, 1))
    # 中心一点微光，避免纯渐变显得平
    glow_at(s, COL[th['accent']], W * .5, H * .42, 420, 1)
    BG_GRAD[layer] = s
    return s


def _motif_tile(motif, far):
    """生成 512×512 可平铺的抽象纹理（不同地貌用不同母题）"""
    s = pygame.Surface((_ZT, _ZT), pygame.SRCALPHA)
    r = random.Random(hash((motif, far)) & 0x7FFFFFFF)
    col = COL[theme_of(1)['accent']]
    # 取该母题对应的颜色
    for th in LAYER_THEME:
        if th['motif'] == motif:
            col = COL[th['accent']]
            break
    n = 26 if far else 40
    if motif == 'rust':
        for i in range(10 if far else 16):
            x0, y0 = r.randint(-80, _ZT), r.randint(0, _ZT)
            ln = r.randint(120, 300)
            a = (16 if far else 36) + r.randint(-6, 8)
            pygame.draw.line(s, (*col, a), (x0, y0), (x0 + ln, y0 + r.randint(-26, 26),
                                                 ), r.randint(2, 5))
        for i in range(n):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            rr = r.randint(2, 7 if far else 4)
            pygame.draw.circle(s, (*col, (18 if far else 44)), (x, y), rr, 1)
    elif motif == 'fungus':
        for i in range(8 if far else 14):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            rr = r.randint(34, 90) if far else r.randint(12, 30)
            pygame.draw.circle(s, (*col, 12 if far else 30), (x, y), rr)
        for i in range(n):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            h = r.randint(10, 34)
            pygame.draw.line(s, (*col, 30 if far else 60), (x, y), (x, y - h), 1)
            pygame.draw.circle(s, (*col, 40 if far else 90), (x, y - h), r.randint(2, 4))
    elif motif == 'magma':
        for i in range(5 if far else 9):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            pts = [(x, y)]
            for k in range(4):
                x += r.randint(-46, 46)
                y += r.randint(14, 52)
                pts.append((x, y))
            pygame.draw.lines(s, (*col, 20 if far else 55), False, pts, r.randint(2, 4))
            if not far:
                pygame.draw.lines(s, (255, 240, 210, 40), False, pts, 1)
        for i in range(n):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            pygame.draw.circle(s, (*col, 30 if far else 70), (x, y), r.randint(1, 3))
    elif motif == 'mirror':
        for i in range(0, _ZT + 1, 64):
            pygame.draw.line(s, (*col, 20 if far else 34), (i, 0), (i, _ZT), 1)
            pygame.draw.line(s, (*col, 20 if far else 34), (0, i), (_ZT, i), 1)
        for i in range(n):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            sz = r.randint(12, 46) if far else r.randint(6, 20)
            pts = [(x, y - sz), (x + sz // 2, y + sz), (x - sz // 2, y + sz)]
            pygame.draw.polygon(s, (*col, 20 if far else 44), pts, 1)
    elif motif == 'snow':
        for i in range(6 if far else 10):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            pygame.draw.ellipse(s, (*col, 14 if far else 26),
                                (x - 90, y - 20, 180, 40), 0)
        for i in range(n):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            ln = r.randint(8, 26)
            pygame.draw.line(s, (*col, 26 if far else 50),
                             (x, y), (x + r.randint(-8, 8), y + ln), 1)
    elif motif == 'mech':
        for i in range(5 if far else 9):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            w = r.randint(40, 140)
            h = r.randint(8, 20)
            pygame.draw.rect(s, (*col, 18 if far else 42), (x, y, w, h), 1)
        for i in range(4 if far else 7):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            rr = r.randint(14, 34)
            pygame.draw.circle(s, (*col, 20 if far else 46), (x, y), rr, 1)
            for k in range(6):
                a = k * math.pi / 3
                pygame.draw.line(s, (*col, 18 if far else 40),
                                 (x, y), (x + math.cos(a) * rr, y + math.sin(a) * rr), 1)
        for i in range(n // 3):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            pygame.draw.circle(s, (255, 120, 90, 70), (x, y), 2)
    elif motif == 'data':
        for i in range(0, _ZT + 1, 48):
            pygame.draw.line(s, (*col, 14 if far else 26), (i, 0), (i, _ZT), 1)
        for i in range(n):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            hh = r.randint(18, 70) if far else r.randint(8, 26)
            a = 18 if far else 52
            pygame.draw.line(s, (*col, a), (x, y), (x, y + hh), 1)
    elif motif == 'void':
        for i in range(n + 10):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            rr = r.randint(1, 3)
            pygame.draw.circle(s, (220, 230, 255, 30 if far else 60), (x, y), rr)
        for i in range(4 if far else 6):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            sz = r.randint(16, 44)
            pts = [(x, y), (x + sz, y + r.randint(-8, 8)), (x + sz // 2, y + sz)]
            pygame.draw.polygon(s, (*col, 16 if far else 30), pts, 1)
    else:  # core
        for i in range(4 if far else 6):
            cx, cy = r.randint(0, _ZT), r.randint(0, _ZT)
            for k in range(2):
                rr = r.randint(30, 120)
                pygame.draw.arc(s, (*col, 20 if far else 44),
                                (cx - rr, cy - rr, rr * 2, rr * 2), 0.4, 5.6, 1)
        for i in range(n):
            x, y = r.randint(0, _ZT), r.randint(0, _ZT)
            a = r.randint(0, 360)
            ln = r.randint(10, 40) if far else r.randint(6, 22)
            pygame.draw.line(s, (*col, 16 if far else 40), (x, y),
                             (x + math.cos(a) * ln, y + math.sin(a) * ln), 1)
    return s


def zone_bg(layer):
    z = ZONE_BG.get(layer)
    if z:
        return z
    th = theme_of(layer)
    far = _motif_tile(th['motif'], True)
    near = _motif_tile(th['motif'], False)
    z = (far, near)
    if len(ZONE_BG) > 24:
        ZONE_BG.clear()
    ZONE_BG[layer] = z
    return z


ZONE_CONTENT = {}
PROP_CACHE = {}
LANDMARK_CACHE = {}
STAR_CACHE = {}
FG_CACHE = {}
_FG_LRU = []


def _zone_colors(th):
    acc = COL[th['accent']]
    fill = mix(th['top'], acc, .16)
    deep = mix(th['bot'], (0, 0, 0), .30)
    edge = mix(mix(th['line'], acc, .28), th['bot'], .22)
    hi = mix(acc, COL['white'], .68)
    return acc, fill, deep, edge, hi


def zone_content(layer):
    """每层固定的地标、巨构残骸、回声信标与前景剪影。"""
    layer = max(1, int(layer))
    key = (layer, G.ww, G.wh)
    got = ZONE_CONTENT.get(key)
    if got is not None:
        return got
    th = theme_of(layer)
    rng = random.Random(0xA53 + layer * 7919 + G.ww)
    ww, wh = G.ww, G.wh
    spawn = (ww * .5, wh - 170)
    area_k = (ww * wh) / float(7000 * 4800)
    props = []
    # 先布置成“废墟群”，而不是均匀撒点：有密有疏，画面才像经过设计
    clusters = []
    for ci in range(max(60, int(120 * area_k))):
        cx = rng.uniform(260, ww - 260)
        cy = rng.uniform(220, wh - 180)
        if dist2((cx, cy), spawn) < 380 ** 2:
            continue
        clusters.append((cx, cy, rng.uniform(180, 460), rng.randint(5, 11)))
    for cx, cy, rad, n in clusters:
        for k in range(n):
            a = rng.uniform(0, math.pi * 2)
            rr = rng.uniform(40, rad)
            x = clamp(cx + math.cos(a) * rr, 160, ww - 160)
            y = clamp(cy + math.sin(a) * rr * .62, 140, wh - 60)
            props.append(dict(kind=th['motif'], variant=rng.choices(range(8), weights=(1, 2, 1, 2, 1, 2, 1, 1))[0],
                              x=x, y=y, sc=rng.uniform(.48, 1.28),
                              sub=rng.randrange(3),
                              tilt=rng.randint(-2, 2),
                              flip=rng.random() < .5))
    for i in range(max(80, int(160 * area_k))):
        x = rng.uniform(160, ww - 160)
        y = rng.uniform(140, wh - 60)
        if dist2((x, y), spawn) < 260 ** 2:
            continue
        props.append(dict(kind=th['motif'], variant=rng.choices(range(8), weights=(1, 2, 1, 2, 1, 2, 1, 1))[0],
                          x=x, y=y, sc=rng.uniform(.55, 1.35),
                          sub=rng.randrange(3),
                          tilt=rng.randint(-2, 2),
                          flip=rng.random() < .5))
    lx, ly = ww * .5, wh * .5
    for _ in range(40):
        lx = rng.uniform(420, ww - 420)
        ly = rng.uniform(380, wh - 260)
        if dist2((lx, ly), spawn) > 1600 ** 2:
            break
    landmark = dict(x=lx, y=ly, sc=rng.uniform(.9, 1.15),
                    name=landmark_name(layer), kind=th['motif'])
    caches = []
    tries = 0
    while len(caches) < 3 and tries < 160:
        tries += 1
        x = rng.uniform(300, ww - 300)
        y = rng.uniform(260, wh - 160)
        if dist2((x, y), spawn) < 460 ** 2:
            continue
        if any(dist2((x, y), (c['x'], c['y'])) < 760 ** 2 for c in caches):
            continue
        caches.append(dict(x=x, y=y, r=rng.uniform(28, 36)))
    fg = []
    for i in range(max(10, int(12 * area_k ** .5))):
        fg.append(dict(x=rng.uniform(-200, ww + 200), y=rng.uniform(-100, wh + 150),
                       sc=rng.uniform(.86, 1.8), kind=rng.randrange(3),
                       a=rng.uniform(52, 92)))
    data = dict(props=props, landmark=landmark, caches=caches, fg=fg)
    ZONE_CONTENT[key] = data
    while len(ZONE_CONTENT) > 3:
        ZONE_CONTENT.pop(next(iter(ZONE_CONTENT)))
    return data


def load_zone_content(layer):
    data = zone_content(layer)
    G.props = data['props']
    G.landmark = dict(data['landmark'])
    G.caches = [dict(c, taken=False, t=rnd(12)) for c in data['caches']]
    G.cache_total = len(G.caches)
    G.cache_taken = 0
    G.landmark_seen = False
    G.fg_props = data['fg']
    G.layer_card_t = 3.0


def _prop_sprite(layer, p):
    key = (layer, p['kind'], p['variant'], int(p['sc'] * 10),
           int(p.get('sub', 0)), int(p.get('tilt', 0)), bool(p['flip']))
    got = PROP_CACHE.get(key)
    if got is not None:
        return got
    th = theme_of(layer)
    acc, fill, deep, edge, hi = _zone_colors(th)
    cool = mix(COL['aqua'], acc, .45)
    w = max(44, int(148 * p['sc']))
    h = max(48, int(176 * p['sc']))
    sub = int(p.get('sub', 0))
    w = int(w * (1.0, .90, .79)[sub])
    h = int(h * (1.0, .86, .74)[sub])
    s = pygame.Surface((w + 56, h + 66), pygame.SRCALPHA)
    cx = (w + 56) / 2
    base = h + 30
    # 接地阴影
    pygame.draw.ellipse(s, (0, 0, 0, 74), (cx - w * .42, base - h * .12, w * .84, h * .2))
    _soft_blob(s, mix(deep, acc, .34), cx, base - h * .04, w * .35, h * .08, 18)
    v = p['variant']
    if v == 0:
        pts = [(cx - w * .18, base), (cx - w * .105, base - h * .42),
               (cx - w * .045, base - h * .68), (cx + w * .02, base - h * .9),
               (cx + w * .085, base - h * .7), (cx + w * .17, base)]
        _grad_poly(s, pts, mix(fill, hi, .16), deep, edge, 1)
        pygame.draw.line(s, mix(edge, hi, .3), (cx + w * .02, base - h * .86),
                         (cx - w * .01, base - h * .18), 1)
        pygame.draw.line(s, deep, (cx - w * .07, base - h * .55),
                         (cx + w * .1, base - h * .5), 2)
        for k in range(5):
            yy = base - h * (.2 + k * .12)
            pygame.draw.line(s, deep, (cx - w * .12, yy), (cx + w * .13, yy - 4), 1)
        pygame.draw.circle(s, acc, (int(cx + w * .07), int(base - h * .58)), max(1, int(w * .018)))
    elif v == 1:
        pts = [(cx - w * .4, base), (cx - w * .33, base - h * .4),
               (cx - w * .12, base - h * .58), (cx + w * .1, base - h * .46),
               (cx + w * .34, base - h * .2), (cx + w * .4, base)]
        _grad_poly(s, pts, mix(fill, hi, .10), deep, edge, 1)
        for k in range(4):
            pygame.draw.line(s, edge, (cx - w * .28 + k * w * .13, base - h * .12),
                             (cx - w * .2 + k * w * .13, base - h * .5), 1)
        pygame.draw.line(s, deep, (cx - w * .1, base - h * .5), (cx + w * .18, base - h * .3), 2)
        pygame.draw.circle(s, acc, (int(cx + w * .02), int(base - h * .3)), max(1, int(w * .015)))
    elif v == 2:
        for sx in (-1, 1):
            x0 = cx + sx * w * .26
            th2 = h * (.7 if not (sub == 2 and sx > 0) else .38)
            pts = [(x0 - w * .1, base), (x0 - w * .04, base - th2),
                   (x0 + w * .04, base - th2 * 1.02), (x0 + w * .1, base)]
            _grad_poly(s, pts, mix(fill, hi, .18), deep, edge, 1)
        if sub == 2:
            pygame.draw.line(s, edge, (cx - w * .34, base - h * .72), (cx - w * .08, base - h * .7), 2)
            pygame.draw.line(s, edge, (cx + w * .08, base - h * .4), (cx + w * .34, base - h * .4), 2)
        else:
            pygame.draw.rect(s, fill, (cx - w * .34, base - h * .78, w * .68, h * .075))
            pygame.draw.rect(s, edge, (cx - w * .34, base - h * .78, w * .68, h * .075), 1)
            for k in range(8):
                pygame.draw.line(s, deep, (cx - w * .3 + k * w * .085, base - h * .742),
                                 (cx - w * .3 + k * w * .085, base - h * .712), 1)
        pygame.draw.arc(s, edge, (cx - w * .3, base - h * .96, w * .6, h * .48), 0, math.pi, 2)
    elif v == 3:
        n = 3 if p['sc'] < 1.2 else 4
        for k in range(n):
            xx = cx + (k - (n - 1) / 2) * w * .15
            hh = h * (.28 + (k % 2) * .22)
            pts = [(xx, base), (xx - w * .055, base - hh * .6), (xx, base - hh),
                   (xx + w * .055, base - hh * .6)]
            _grad_poly(s, pts, mix(fill, hi, .42), deep, edge, 1)
            pygame.draw.line(s, hi, (xx, base - hh * .9), (xx, base - hh * .18), 1)
        if p['kind'] == 'fungus':
            cap = pygame.Rect(int(cx - w * .3), int(base - h * .78), int(w * .6), int(h * .24))
            pygame.draw.ellipse(s, deep, cap)
            pygame.draw.ellipse(s, fill, cap.inflate(-int(w * .05), -int(h * .035)).move(0, -3))
            pygame.draw.ellipse(s, mix(fill, hi, .24),
                                cap.inflate(-int(w * .16), -int(h * .09)).move(0, -5))
            pygame.draw.ellipse(s, edge, cap, 1)
            for k in range(4):
                xx = cap.left + cap.w * (.18 + k * .21)
                pygame.draw.circle(s, mix(acc, COL['white'], .35),
                                   (int(xx), int(cap.centery - 3)), max(1, int(w * .012)))
    elif v == 4:
        body = [(cx - w * .11, base), (cx - w * .11, base - h * .74),
                (cx + w * .11, base - h * .74), (cx + w * .11, base)]
        _grad_poly(s, body, mix(fill, hi, .16), deep, edge, 1)
        for k in range(1, 7):
            yy = base - h * (.74 - k * .095)
            pygame.draw.line(s, deep, (cx - w * .105, yy), (cx + w * .105, yy), 1)
            for j in range(2):
                pygame.draw.circle(s, mix(cool, hi, .45),
                                   (int(cx - w * .045 + j * w * .09), int(yy - h * .035)), max(1, int(w * .009)))
        pygame.draw.line(s, mix(fill, hi, .35), (cx - w * .095, base - h * .70),
                         (cx - w * .095, base - h * .06), 1)
        for k in range(3):
            rr = w * (.2 - k * .045)
            pygame.draw.ellipse(s, edge, (cx - rr, base - h * (.34 + k * .13), rr * 2, h * .055), 1)
        pygame.draw.line(s, edge, (cx, base - h * .74), (cx, base - h * 1.0), 1)
        pygame.draw.circle(s, acc, (int(cx), int(base - h * 1.0)), max(1, int(w * .014)))
    elif v == 5:
        rr = w * .32
        rect = pygame.Rect(cx - rr, base - h * .64 - rr, rr * 2, rr * 2)
        end = math.pi * 1.22 if sub < 2 else 2.2
        pygame.draw.arc(s, fill, rect, -.2, end, max(5, int(w * .085)))
        pygame.draw.arc(s, edge, rect, -.2, end, 1)
        inner = rect.inflate(-int(w * .06), -int(w * .06))
        pygame.draw.arc(s, mix(fill, hi, .22), inner, -.2, end, max(2, int(w * .022)))
        for k in range(5 if sub < 2 else 3):
            a = -.2 + k * .66
            px = cx + math.cos(a) * rr
            py = base - h * .64 + math.sin(a) * rr
            pygame.draw.circle(s, cool, (int(px), int(py)), max(1, int(w * .023)))
            pygame.draw.circle(s, mix(cool, COL['white'], .6), (int(px), int(py)), max(1, int(w * .009)))
            pygame.draw.line(s, edge, (cx, base - h * .64), (px, py), 1)
        pygame.draw.circle(s, mix(acc, COL['white'], .5), (int(cx), int(base - h * .64)), max(2, int(w * .035)), 1)
    elif v == 6:
        # 破裂的抛物面天线：细桅杆 + 半圆碟 + 馈源
        mast = cx - w * .04
        pygame.draw.line(s, mix(fill, deep, .3), (mast, base), (mast, base - h * .56), max(3, int(w * .03)))
        pygame.draw.line(s, edge, (mast, base), (mast, base - h * .56), 1)
        dcx, dcy, rr = mast + w * .03, base - h * .76, w * .24
        pts = [(dcx, dcy)]
        for k in range(10):
            a = math.pi * 1.02 + k * (math.pi * .96 / 9)
            pts.append((dcx + math.cos(a) * rr, dcy + math.sin(a) * rr * .9))
        _grad_poly(s, pts, mix(fill, hi, .28), deep, edge, 1)
        pygame.draw.line(s, mix(fill, hi, .38), (dcx - rr * .8, dcy - rr * .28),
                         (dcx + rr * .8, dcy - rr * .28), 1)
        for k in range(4):
            xx = dcx - rr * .55 + k * rr * .36
            pygame.draw.line(s, deep, (dcx, dcy), (xx, dcy - rr * .75), 1)
        pygame.draw.circle(s, mix(acc, COL['white'], .5), (int(dcx), int(dcy - rr * .2)), max(1, int(w * .018)))
        pygame.draw.line(s, edge, (dcx, dcy), (dcx, dcy - rr * .2), 1)
    else:
        # 断裂的桁架塔：方框骨架 + 斜撑
        fr = pygame.Rect(int(cx - w * .2), int(base - h * .64), int(w * .4), int(h * .27))
        pygame.draw.rect(s, mix(fill, deep, .4), fr)
        pygame.draw.rect(s, edge, fr, 1)
        for k in range(1, 4):
            xx = fr.left + fr.w * k / 4
            pygame.draw.line(s, edge, (xx, fr.top), (xx, fr.bottom), 1)
        pygame.draw.line(s, mix(fill, hi, .3), (fr.left, fr.bottom), (cx - w * .14, base), 2)
        pygame.draw.line(s, mix(fill, hi, .3), (fr.right, fr.bottom), (cx + w * .14, base), 2)
        pygame.draw.line(s, edge, (fr.left, base - h * .5), (fr.right, base - h * .18), 1)
        pygame.draw.line(s, deep, (fr.left, base - h * .2), (fr.right, base - h * .5), 1)
        pygame.draw.line(s, edge, (cx, fr.top), (cx, base - h * .78), 1)
        pygame.draw.circle(s, acc, (int(cx), int(base - h * .78)), max(1, int(w * .014)))
    # 统一的边缘轮廓光
    pygame.draw.line(s, mix(edge, hi, .6), (cx - w * .25, base - h * .18),
                     (cx - w * .06, base - h * .78), 1)
    if p.get('tilt'):
        s = pygame.transform.rotozoom(s, p['tilt'] * 3.0, 1.0)
    if p['flip']:
        s = pygame.transform.flip(s, True, False)
    PROP_CACHE[key] = s
    while len(PROP_CACHE) > 120:
        PROP_CACHE.pop(next(iter(PROP_CACHE)))
    return s


def _landmark_sprite(layer):
    got = LANDMARK_CACHE.get(layer)
    if got is not None:
        return got
    th = theme_of(layer)
    acc, fill, deep, edge, hi = _zone_colors(th)
    lm = (G.landmark or {}).get('sc', 1.0)
    w, h = int(560 * lm), int(380 * lm)
    s = pygame.Surface((w + 160, h + 160), pygame.SRCALPHA)
    cx, base = (w + 160) / 2, h + 100
    pygame.draw.ellipse(s, (0, 0, 0, 88), (cx - w * .38, base - h * .12, w * .76, h * .22))
    _soft_blob(s, mix(deep, acc, .35), cx, base - h * .06, w * .34, h * .1, 30)
    m = th['motif']
    if m in ('rust', 'void', 'magma'):
        # 巨骸：先给一段断裂船体，再叠脊椎与肋骨，远看能读成“船”
        p0 = (cx - w * .36, base - h * .09)
        p1 = (cx + w * .38, base - h * .44)
        # 脊椎：分段椎骨，避免一整块长条像木板
        for k in range(9):
            t = k / 8.0
            vx = p0[0] + (p1[0] - p0[0]) * t
            vy = p0[1] + (p1[1] - p0[1]) * t
            sw = w * (.048 + .014 * math.sin(t * math.pi * 3))
            sh = h * (.038 + .012 * (1 - t))
            verts = [(vx - sw, vy), (vx - sw * .45, vy - sh), (vx + sw * .55, vy - sh * .8),
                     (vx + sw, vy + sh * .25), (vx + sw * .2, vy + sh)]
            _grad_poly(s, verts, mix(fill, hi, .34), mix(deep, fill, .35), edge, 1)
        # 断裂的艏部与吊索
        pygame.draw.lines(s, edge, False, [(p1[0] - w * .04, p1[1] + h * .1),
                                           (p1[0] + w * .06, p1[1] - h * .02),
                                           (p1[0] - w * .02, p1[1] - h * .14)], 2)
        for k in range(5):
            xx = cx - w * .26 + k * w * .14
            yy = base - h * .14 - k * h * .06
            pygame.draw.line(s, mix(edge, deep, .35), (xx, yy + h * .1), (xx - 4, yy + h * .2), 1)
            pygame.draw.line(s, mix(edge, deep, .35), (xx, yy + h * .1), (xx + 6, yy + h * .18), 1)
        pygame.draw.line(s, mix(edge, hi, .18), (cx - w * .34, base - h * .1),
                         (cx + w * .36, base - h * .42), 2)
        for k in range(7):
            t = k / 6
            x = cx - w * .3 + t * w * .64
            y = base - h * .12 - t * h * .3
            rr = w * (.2 + .05 * math.sin(t * math.pi))
            rect = pygame.Rect(x - rr, y - rr, rr * 2, rr * 2)
            pygame.draw.arc(s, fill, rect, math.pi * .92, math.pi * 1.92, max(3, int(w * .012)))
            pygame.draw.arc(s, mix(fill, hi, .26), rect.inflate(-int(w * .022), -int(w * .022)),
                            math.pi * .92, math.pi * 1.92, 2)
            pygame.draw.arc(s, edge, rect, math.pi * .92, math.pi * 1.92, 1)
        pygame.draw.circle(s, mix(acc, COL['white'], .4), (int(cx + w * .02), int(base - h * .3)), max(4, int(w * .012)), 2)
    elif m == 'fungus':
        # 母树：粗茎、巨伞与发光菌褶
        stem = [(cx - w * .12, base), (cx - w * .05, base - h * .55),
                (cx + w * .06, base - h * .55), (cx + w * .14, base)]
        _grad_poly(s, stem, mix(fill, hi, .22), deep, edge, 1)
        pygame.draw.ellipse(s, fill, (cx - w * .38, base - h * .78, w * .76, h * .32))
        pygame.draw.ellipse(s, edge, (cx - w * .38, base - h * .78, w * .76, h * .32), 2)
        for k in range(9):
            xx = cx - w * .3 + k * w * .075
            pygame.draw.line(s, edge, (cx, base - h * .55), (xx, base - h * .78), 1)
        _soft_blob(s, acc, cx, base - h * .68, w * .28, h * .08, 62)
    elif m in ('magma', 'mech'):
        # 巨环熔炉 / 齿轮圣像
        rr = w * .3
        rect = pygame.Rect(cx - rr, base - h * .46 - rr, rr * 2, rr * 2)
        pygame.draw.arc(s, fill, rect, 0, math.pi * 1.86, max(7, int(w * .025)))
        pygame.draw.arc(s, edge, rect, 0, math.pi * 1.86, 2)
        for k in range(16):
            a = k * math.pi * 2 / 16
            x0, y0 = cx + math.cos(a) * rr, base - h * .46 + math.sin(a) * rr
            x1, y1 = cx + math.cos(a) * rr * 1.09, base - h * .46 + math.sin(a) * rr * 1.09
            pygame.draw.line(s, edge, (x0, y0), (x1, y1), 3)
        _soft_blob(s, acc, cx, base - h * .46, w * .2, h * .2, 90)
        pygame.draw.circle(s, mix(acc, COL['white'], .58), (int(cx), int(base - h * .46)), max(5, int(w * .012)), 1)
        for k in range(2):
            rr2 = w * (.16 + k * .09)
            pygame.draw.arc(s, edge, (cx - rr2, base - h * .46 - rr2, rr2 * 2, rr2 * 2),
                            math.pi * (.2 + k), math.pi * (1.1 + k), 1)
    else:
        # 巨门 / 圣堂：双塔、尖拱与玫瑰窗
        for sx in (-1, 1):
            x0 = cx + sx * w * .28
            pts = [(x0 - w * .1, base), (x0 - w * .065, base - h * .66),
                   (x0, base - h * .8), (x0 + w * .065, base - h * .66),
                   (x0 + w * .1, base)]
            _grad_poly(s, pts, mix(fill, hi, .20), deep, edge, 1)
        pygame.draw.arc(s, fill, (cx - w * .29, base - h * .78, w * .58, h * .52), 0, math.pi, max(6, int(w * .018)))
        pygame.draw.arc(s, edge, (cx - w * .29, base - h * .78, w * .58, h * .52), 0, math.pi, 1)
        pygame.draw.circle(s, mix(fill, acc, .3), (int(cx), int(base - h * .46)), int(w * .1), 2)
        for k in range(8):
            a = k * math.pi / 4
            pygame.draw.line(s, edge, (cx, base - h * .46),
                             (cx + math.cos(a) * w * .1, base - h * .46 + math.sin(a) * w * .1), 1)
        _soft_blob(s, acc, cx, base - h * .46, w * .2, h * .2, 72)
    # 顶部信标
    pygame.draw.line(s, edge, (cx, base - h * .8), (cx, base - h * 1.02), 1)
    pygame.draw.circle(s, mix(acc, COL['white'], .7), (int(cx), int(base - h * 1.02)), max(2, int(w * .008)))
    LANDMARK_CACHE[layer] = s
    while len(LANDMARK_CACHE) > 3:
        LANDMARK_CACHE.pop(next(iter(LANDMARK_CACHE)))
    return s


def _star_tile(layer):
    got = STAR_CACHE.get(layer)
    if got is not None:
        return got
    th = theme_of(layer)
    acc = COL[th['accent']]
    rng = random.Random(0x57A2 + layer * 3011)
    s = pygame.Surface((512, 512), pygame.SRCALPHA)
    # 只保留星尘，不放大面积星云：大面积色块会像贴图接缝
    for i in range(76):
        x, y = rng.randint(0, 511), rng.randint(0, 511)
        r = rng.choice((1, 1, 1, 2))
        a = rng.randint(18, 92)
        c = mix(mix(th['top'], COL['white'], .38), acc, rng.random() * .22)
        pygame.draw.circle(s, (c[0], c[1], c[2], a), (x, y), r)
        if r == 2 and i % 9 == 0:
            pygame.draw.line(s, (c[0], c[1], c[2], max(12, a // 3)), (x - 3, y), (x + 3, y), 1)
            pygame.draw.line(s, (c[0], c[1], c[2], max(12, a // 3)), (x, y - 3), (x, y + 3), 1)
    STAR_CACHE[layer] = s
    while len(STAR_CACHE) > 6:
        STAR_CACHE.pop(next(iter(STAR_CACHE)))
    return s


def draw_parallax(surf):
    tile = _star_tile(G.run.layer)
    sz = 512
    dx = int(-G.camx * .16) % sz
    dy = int(-G.camy * .12) % sz
    for yy in range(-dy, H, sz):
        for xx in range(-dx, W, sz):
            surf.blit(tile, (xx, yy), special_flags=pygame.BLEND_ADD)
    # 少量近景闪烁，给静态星图一点呼吸
    rng = random.Random(G.run.layer * 733)
    for i in range(14):
        x = (rng.randint(0, 4096) + G.t * (4 + i % 3) * 2) % (W + 40) - 20
        y = (rng.randint(0, 4096) - G.t * (2 + i % 4)) % (H + 40) - 20
        a = .25 + .35 * (math.sin(G.t * 1.8 + i) * .5 + .5)
        c = mix(COL['bg0'], COL[theme_of(G.run.layer)['accent']], a)
        pygame.draw.circle(surf, c, (int(x), int(y)), 1)


def draw_props(surf, ox, oy):
    if not G.props:
        return
    for p in G.props:
        sx = p['x'] + ox
        sy = p['y'] + oy
        if sx < -320 or sx > W + 320 or sy < -400 or sy > H + 220:
            continue
        spr = _prop_sprite(G.run.layer, p)
        if sx + spr.get_width() < -40 or sx - spr.get_width() > W + 40:
            continue
        if sy + spr.get_height() < -40 or sy - spr.get_height() > H + 40:
            continue
        surf.blit(spr, (int(sx - spr.get_width() / 2), int(sy - spr.get_height() + 26)))


def draw_landmark(surf, ox, oy):
    lm = G.landmark
    if not lm:
        return
    spr = _landmark_sprite(G.run.layer)
    sx = lm['x'] + ox
    sy = lm['y'] + oy
    if sx + spr.get_width() * .6 > -60 and sx - spr.get_width() * .6 < W + 60 and \
       sy + spr.get_height() * .4 > -80 and sy - spr.get_height() * .8 < H + 80:
        surf.blit(spr, (int(sx - spr.get_width() / 2), int(sy - spr.get_height() + 40)))
    if G.player:
        d = math.sqrt(dist2((G.player.x, G.player.y), (lm['x'], lm['y'])))
        if d < 980:
            name = lm['name'][1] if META.get('lang') else lm['name'][0]
            draw_text(surf, L('地标 · ' + lm['name'][0], 'LANDMARK · ' + name), 12,
                      mix(COL['bg0'], COL[theme_of(G.run.layer)['accent']], .9),
                      (sx, sy + 46), align='center')
            if not G.landmark_seen and d < 620 and G.layer_card_t <= 0:
                G.landmark_seen = True
                toast(L('发现地标 · ' + lm['name'][0], 'LANDMARK FOUND · ' + name), 'gold', 2.6)
                ring(lm['x'], lm['y'], 40, 190, 'gold', .9, 2)
                AUD.play('pick', .8)


def draw_foreground(surf):
    if not G.run or not G.fg_props:
        return
    for i, p in enumerate(G.fg_props):
        spr = _fg_sprite(G.run.layer, i)
        sx = p['x'] - G.camx * 1.18
        sy = p['y'] - G.camy * 1.18
        if sx + spr.get_width() < -80 or sx - spr.get_width() > W + 80:
            continue
        if sy + spr.get_height() < -80 or sy - spr.get_height() > H + 80:
            continue
        surf.blit(spr, (int(sx - spr.get_width() / 2), int(sy - spr.get_height() / 2)))


def _fg_sprite(layer, idx):
    key = (layer, idx)
    got = FG_CACHE.get(key)
    if got is not None:
        return got
    rng = random.Random(0xF6 + layer * 131 + idx * 17)
    th = theme_of(layer)
    acc, fill, deep, edge, hi = _zone_colors(th)
    w, h = rng.randint(240, 560), rng.randint(130, 300)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    col = (deep[0], deep[1], deep[2], rng.randint(34, 66))
    ln = (deep[0], deep[1], deep[2], rng.randint(86, 120))
    if idx % 3 == 0:
        pts = [(0, h), (w * .18, h * .2), (w * .5, 0), (w * .76, h * .28), (w, h)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.lines(s, ln, False, pts, 1)
        for k in range(3):
            xx = w * (.22 + k * .2)
            pygame.draw.line(s, ln, (xx, h), (xx + w * .04, h * .28), 1)
    elif idx % 3 == 1:
        pygame.draw.ellipse(s, col, (0, h * .24, w, h * .72))
        pygame.draw.ellipse(s, (col[0], col[1], col[2], col[3] // 2), (w * .18, h * .4, w * .64, h * .44))
        pygame.draw.ellipse(s, ln, (0, h * .24, w, h * .72), 1)
        for k in range(4):
            xx = w * (.18 + k * .18)
            pygame.draw.line(s, ln, (xx, h * .3), (xx + w * .03, h * .92), 1)
    else:
        pygame.draw.arc(s, col, (0, 0, w, h * 1.8), math.pi, math.pi * 2, max(8, w // 18))
        pygame.draw.arc(s, ln, (0, 0, w, h * 1.8), math.pi, math.pi * 2, 1)
        pygame.draw.arc(s, ln, (w * .12, h * .16, w * .76, h * 1.48), math.pi, math.pi * 2, 1)
    FG_CACHE[key] = s
    while len(FG_CACHE) > 16:
        FG_CACHE.pop(next(iter(FG_CACHE)))
    return s


def draw_caches(surf, ox, oy):
    if not G.run or not G.caches:
        return
    th = theme_of(G.run.layer)
    acc = COL[th['accent']]
    for c in G.caches:
        if c.get('taken'):
            continue
        sx = c['x'] + ox
        sy = c['y'] + oy
        if sx < -90 or sx > W + 90 or sy < -90 or sy > H + 120:
            continue
        pulse = .5 + .5 * math.sin(G.t * 2.4 + c['t'])
        # 地面环与光柱
        pygame.draw.ellipse(surf, mix(COL['bg0'], acc, .28), (sx - 34, sy - 10, 68, 22), 1)
        pygame.draw.ellipse(surf, mix(COL['bg0'], acc, .5 + pulse * .2), (sx - 22, sy - 6, 44, 14), 1)
        for k in range(4):
            a = .12 + k * .045
            pygame.draw.line(surf, mix(COL['bg0'], acc, a), (sx, sy - 12), (sx, sy - 96 - pulse * 12), 1)
        glow_at(surf, acc, sx, sy - 56, 42 + pulse * 10, 2)
        # 浮空棱晶
        yy = sy - 56 + math.sin(G.t * 2 + c['t']) * 7
        pts = [(sx, yy - 15), (sx + 9, yy), (sx, yy + 15), (sx - 9, yy)]
        pygame.draw.polygon(surf, mix(COL['bg0'], acc, .82), pts)
        pygame.draw.polygon(surf, mix(acc, COL['white'], .7), pts, 1)
        pygame.draw.circle(surf, mix(acc, COL['white'], .9), (int(sx), int(yy)), 3)
        if G.player and dist2((G.player.x, G.player.y), (c['x'], c['y'])) < 420 ** 2:
            draw_text(surf, L('回声信标', 'ECHO BEACON'), 9,
                      mix(COL['bg0'], acc, .7), (sx, sy + 12), align='center')


def update_caches(dt):
    if not G.run or not G.player:
        return
    p = G.player
    for c in G.caches:
        c['t'] += dt
        if c.get('taken'):
            continue
        if dist2((p.x, p.y), (c['x'], c['y'])) > (c['r'] + 16) ** 2:
            continue
        c['taken'] = True
        G.cache_taken += 1
        G.run.score += 800 + G.run.layer * 120
        G.run.shards_earned += 1
        p.skill_t = 0
        if p.hp < G.run.max_hp:
            heal_player(1, quiet=True)
        else:
            p.shield = min(3, p.shield + 1)
        acc_key = theme_of(G.run.layer)['accent']
        ring(c['x'], c['y'], 18, 92, acc_key, .7, 2)
        particle(c['x'], c['y'] - 40, 18, acc_key, 90, 14, .6)
        AUD.play('pick', .9)
        if G.cache_taken >= G.cache_total:
            G.run.score += 3000 + G.run.layer * 250
            G.run.shards_earned += 2
            heal_player(2, quiet=True)
            toast(L('共振完成 · 本层信标全部回收', 'RESONANCE COMPLETE · ALL BEACONS RECOVERED'), 'gold', 2.6)
            ring(p.x, p.y, 30, 240, 'gold', 1.1, 3)
        else:
            toast(L('回收信标 %d / %d · 技能已充满' % (G.cache_taken, G.cache_total),
                    'BEACON %d / %d · SKILL REFRESHED' % (G.cache_taken, G.cache_total)), 'aqua', 2.0)


def draw_layer_card(surf):
    if not G.run or G.layer_card_t <= 0:
        return
    t = G.layer_card_t
    k_in = clamp((3.0 - t) / .48, 0, 1)
    k_out = clamp(t / .58, 0, 1)
    k = min(k_in, k_out)
    if k <= 0:
        return
    th = theme_of(G.run.layer)
    acc = COL[th['accent']]
    zh, en = zone_tag(G.run.layer)
    top = H - 300
    band = pygame.Surface((W, 240), pygame.SRCALPHA)
    for y in range(240):
        a = int(222 * k * (1 - abs(y - 120) / 172))
        band.fill((2, 8, 12, max(0, a)), (0, y, W, 1))
    surf.blit(band, (0, top))
    pygame.draw.line(surf, mix(COL['bg0'], acc, .85 * k), (64, top + 42), (64, top + 186), 2)
    draw_text(surf, 'STRATUM %02d / %s' % (G.run.layer, ('%d' % layers_for_run()) if layers_for_run() else '∞'),
              12, mix(COL['dim'], acc, .9), (96, top + 30), shadow=(0, 0, 0))
    name = th['en'] if META.get('lang') else th['name']
    draw_text(surf, name, 46, COL['ink'], (96, top + 62), bold=True, shadow=(0, 0, 0))
    if not META.get('lang'):
        draw_text(surf, th['en'], 12, mix(acc, COL['ink'], .35), (98, top + 116), shadow=(0, 0, 0))
    draw_text(surf, zh if not META.get('lang') else en, 15,
              mix(COL['ink'], COL['dim'], .35), (96, top + 142), shadow=(0, 0, 0))
    lw = int(460 * k)
    pygame.draw.line(surf, mix(COL['bg0'], acc, .65 * k), (96, top + 164), (96 + lw, top + 164), 1)
    lm_name = landmark_name(G.run.layer)[1] if META.get('lang') else landmark_name(G.run.layer)[0]
    draw_text(surf, L('地标 · ' + landmark_name(G.run.layer)[0], 'LANDMARK · ' + lm_name),
              10, mix(COL['dim'], acc, .9), (96, top + 178), shadow=(0, 0, 0))

ZONE_WORLD = {}
_WORLD_LRU = []
FOG_CACHE = {}


def _soft_blob(dest, col, cx, cy, rx, ry, a):
    rx, ry = max(2, int(rx)), max(2, int(ry))
    tmp = pygame.Surface((rx * 2, ry * 2), pygame.SRCALPHA)
    for i in range(4, 0, -1):
        k = i / 4
        pygame.draw.ellipse(tmp, (col[0], col[1], col[2], int(a * (1 - k * .55))),
                            (rx * (1 - k), ry * (1 - k), rx * 2 * k, ry * 2 * k))
    dest.blit(tmp, (int(cx - rx), int(cy - ry)))


def _grad_poly(s, pts, c_top, c_bot, edge_col=None, edge_w=1):
    """带纵向明暗的实体多边形：顶部受光，底部沉入阴影，避免大块死板色块。"""
    pi = [(int(x), int(y)) for x, y in pts]
    if len(pi) < 3:
        return
    xs = [p[0] for p in pi]
    ys = [p[1] for p in pi]
    x0, x1 = max(0, min(xs)), min(s.get_width() - 1, max(xs))
    y0, y1 = max(0, min(ys)), min(s.get_height() - 1, max(ys))
    if x1 <= x0 or y1 <= y0:
        return
    w, h = x1 - x0 + 1, y1 - y0 + 1
    c_bot = mix(c_bot, c_top, .28)
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), [(x - x0, y - y0) for x, y in pi])
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    for yy in range(h):
        c = mix(c_top, c_bot, yy / max(1, h - 1))
        pygame.draw.line(grad, (c[0], c[1], c[2], 255), (0, yy), (w, yy))
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(grad, (x0, y0))
    if edge_col is not None:
        pygame.draw.polygon(s, edge_col, pi, edge_w)


def _world_features(s, layer, r, th):
    """每层一张世界大小的地形/遗迹底图：锈船、菌菇、熔岩、镜城……"""
    ww, wh = G.ww, G.wh
    ak = (ww * wh) / float(7000 * 4800)
    acc = COL[th['accent']]
    mid = mix(th['top'], th['bot'], .55)
    fill = mix(mid, acc, .045)
    fill2 = mix(mid, acc, .11)
    edge = mix(mid, acc, .18)
    hi = mix(mid, COL['white'], .20)
    dark = mix(th['bot'], (0, 0, 0), .30)
    m = th['motif']

    # 远景：大块暗色地形与远塔，先铺一层，让主特征不再悬在空黑里
    for i in range(max(80, int(80 * ak))):
        x, y = r.randint(-200, ww + 100), r.randint(-80, wh + 60)
        rx, ry = r.randint(260, 860), r.randint(120, 420)
        _soft_blob(s, mix(th['bot'], (0, 0, 0), .42), x, y, rx, ry, r.randint(10, 26))
        pygame.draw.arc(s, mix(edge, th['bot'], .5),
                        (x - rx, y - ry, rx * 2, ry * 2), .1, math.pi * .9, 1)
    for i in range(max(140, int(140 * ak))):
        x, y = r.randint(0, ww), r.randint(int(wh * .1), wh)
        w2, h2 = r.randint(70, 230), r.randint(120, 420)
        n = r.randint(5, 9)
        pts = [(x, y)]
        for k in range(1, n):
            px = x + w2 * k / (n - 1)
            py = y - h2 * r.uniform(.18, 1.0) * (.72 + .28 * math.sin(k * 1.7))
            pts.append((px, py))
        pts.append((x + w2, y))
        pygame.draw.polygon(s, mix(th['bot'], COL['white'], .028), pts)
        for k in range(1, max(2, n // 2)):
            px = x + w2 * k / max(1, n - 1)
            pygame.draw.line(s, mix(edge, th['bot'], .62), (px, y - h2 * .12), (px, y - h2 * .7), 1)
        pygame.draw.lines(s, mix(edge, th['bot'], .64), False, pts, 1)

    if m == 'rust':
        for i in range(max(6, int(6 * ak))):
            x, y = r.randint(-140, ww), r.randint(int(wh * .12), wh)
            L, Hh = r.randint(150, 360), r.randint(30, 70)
            a = r.uniform(-.24, .24)
            pts = [(x, y), (x + L * .22, y + L * a * .3 - Hh * .28),
                   (x + L * .62, y + L * a * .8 - Hh * .18), (x + L, y + L * a),
                   (x + L - 26, y + L * a + Hh), (x + 22, y + Hh)]
            _grad_poly(s, pts, mix(th['bot'], COL['white'], .025), mix(th['bot'], (0, 0, 0), .4),
                       mix(edge, th['bot'], .34), 1)
            for k in range(1, 5):
                pygame.draw.line(s, mix(fill2, edge, .35), (x + k * L // 6, y + 10),
                                 (x + k * L // 6, y + Hh - 8), 1)
            for k in range(0, L, 52):
                pygame.draw.circle(s, mix(edge, fill2, .4), (x + 10 + k, y + Hh * .62), 1)
            pygame.draw.line(s, mix(edge, hi, .22), (x, y), (x + L, y + L * a), 1)
        for i in range(7):
            x, y = r.randint(0, ww), r.randint(0, int(wh * .55))
            px, py = x, y
            pts = [(px, py)]
            for k in range(5):
                px += r.randint(-26, 26)
                py += r.randint(30, 70)
                pts.append((px, py))
            pygame.draw.lines(s, fill, False, pts, 3)
            pygame.draw.lines(s, edge, False, pts, 1)
        for i in range(7):
            _soft_blob(s, mix(th['line'], th['bot'], .65), r.randint(0, ww), r.randint(int(wh * .4), wh),
                       r.randint(90, 260), r.randint(40, 110), 9)

    elif m == 'fungus':
        for i in range(15):
            x, y = r.randint(0, ww), r.randint(int(wh * .16), wh)
            h, cw = r.randint(80, 300), r.randint(56, 230)
            pygame.draw.line(s, fill, (x, y), (x, y - h), max(3, cw // 7))
            cap = pygame.Rect(int(x - cw / 2), int(y - h - cw * .26), cw, int(cw * .46))
            pygame.draw.ellipse(s, fill, cap)
            pygame.draw.ellipse(s, edge, cap, 1)
            for k in range(5):
                pygame.draw.circle(s, edge, (int(x - cw * .28 + k * cw * .14),
                                             int(cap.centery - cw * .03)), 1)
        for i in range(10):
            _soft_blob(s, acc, r.randint(0, ww), r.randint(int(wh * .3), wh),
                       r.randint(70, 180), r.randint(50, 140), 18)
        for i in range(6):
            x, y = r.randint(0, ww), r.randint(int(wh * .2), wh)
            for k in range(3):
                pygame.draw.circle(s, fill2, (x, y - k * 18), 10 - k * 3, 1)

    elif m == 'magma':
        for i in range(13):
            x = r.randint(-60, ww)
            base = wh if i % 2 == 0 else 0
            h = r.randint(140, 470) * (1 if i % 2 == 0 else -1)
            pts = [(x - r.randint(40, 100), base), (x, base - h),
                   (x + r.randint(30, 90), base - h * .62), (x + r.randint(80, 170), base)]
            pygame.draw.polygon(s, fill, pts)
            pygame.draw.polygon(s, edge, pts, 1)
        for i in range(10):
            x, y = r.randint(0, ww), r.randint(0, wh)
            pts = [(x, y)]
            px, py = x, y
            for k in range(5):
                px += r.randint(-60, 60)
                py += r.randint(-50, 50)
                pts.append((px, py))
            pygame.draw.lines(s, fill2, False, pts, 3)
            pygame.draw.lines(s, acc, False, pts, 1)
        for i in range(8):
            _soft_blob(s, acc, r.randint(0, ww), r.randint(int(wh * .55), wh),
                       r.randint(100, 300), r.randint(40, 90), 26)

    elif m == 'mirror':
        for i in range(22):
            x, y = r.randint(-30, ww), r.randint(int(wh * .25), wh)
            w, h = r.randint(46, 150), r.randint(110, 520)
            rect = pygame.Rect(x, y - h, w, h)
            pygame.draw.rect(s, fill, rect)
            pygame.draw.rect(s, edge, rect, 1)
            for yy in range(rect.top + 16, rect.bottom - 8, 26):
                for xx in range(rect.left + 12, rect.right - 8, 20):
                    pygame.draw.rect(s, hi, (xx, yy, 5, 3))
        for i in range(9):
            x, y = r.randint(0, ww), r.randint(0, wh)
            sz = r.randint(80, 240)
            pts = [(x, y - sz), (x + sz * .4, y), (x, y + sz * .7), (x - sz * .5, y - sz * .1)]
            pygame.draw.polygon(s, fill2, pts)
            pygame.draw.polygon(s, edge, pts, 1)
        for i in range(5):
            _soft_blob(s, acc, r.randint(0, ww), r.randint(0, wh),
                       r.randint(140, 320), r.randint(90, 200), 14)

    elif m == 'snow':
        for i in range(15):
            x, y = r.randint(-80, ww), r.randint(int(wh * .35), wh)
            w, h = r.randint(120, 430), r.randint(90, 280)
            pts = [(x, y), (x + w * .22, y - h), (x + w * .45, y - h * .74),
                   (x + w * .66, y - h * 1.1), (x + w, y)]
            pygame.draw.polygon(s, fill, pts)
            pygame.draw.polygon(s, edge, pts, 1)
        for i in range(9):
            x, y = r.randint(0, ww), r.randint(0, wh)
            pygame.draw.ellipse(s, fill2, (x - 160, y - 26, 320, 52))
        for i in range(6):
            _soft_blob(s, acc, r.randint(0, ww), r.randint(0, wh),
                       r.randint(150, 340), r.randint(40, 90), 18)

    elif m == 'mech':
        for i in range(14):
            x, y = r.randint(-40, ww), r.randint(int(wh * .18), wh)
            w, h = r.randint(90, 280), r.randint(70, 230)
            rect = pygame.Rect(x, y - h, w, h)
            pygame.draw.rect(s, fill, rect)
            pygame.draw.rect(s, edge, rect, 1)
            pygame.draw.rect(s, fill2, rect.inflate(-20, -20), 1)
            pygame.draw.circle(s, fill2, rect.center, min(w, h) // 5, 1)
            for k in range(6):
                pygame.draw.line(s, fill2, (rect.left + 8 + k * (w - 16) / 6, rect.top + 6),
                                 (rect.left + 8 + k * (w - 16) / 6, rect.bottom - 6), 1)
        for i in range(8):
            x, y = r.randint(0, ww), r.randint(0, wh)
            pts = [(x, y), (x + r.randint(-120, 120), y), (x + r.randint(-120, 120), y), (x, y + r.randint(90, 260))]
            pygame.draw.lines(s, fill2, False, pts, 6)
            pygame.draw.lines(s, edge, False, pts, 1)
        for i in range(5):
            _soft_blob(s, acc, r.randint(0, ww), r.randint(0, wh),
                       r.randint(120, 280), r.randint(70, 160), 16)

    elif m == 'data':
        for i in range(30):
            x, y = r.randint(-20, ww), r.randint(0, wh)
            w, h = r.randint(58, 132), r.randint(230, 700)
            rect = pygame.Rect(x, y - h, w, h)
            pygame.draw.rect(s, mix(th['bot'], acc, .11), rect)
            pygame.draw.rect(s, mix(edge, acc, .45), rect, 1)
            pygame.draw.line(s, edge, (rect.centerx, rect.top - 30), (rect.centerx, rect.top), 1)
            pygame.draw.circle(s, acc, (rect.centerx, rect.top - 32), 2)
            _soft_blob(s, acc, rect.centerx, rect.top, 40, 26, 16)
            for yy in range(rect.top + 18, rect.bottom - 10, 58):
                pygame.draw.line(s, fill2, (rect.left + 5, yy), (rect.right - 5, yy), 1)
                pygame.draw.rect(s, hi, (rect.left + 8, yy + 8, 6, 3))
                pygame.draw.rect(s, acc, (rect.right - 15, yy + 8, 5, 3))
            for yy in range(rect.top + 14, rect.bottom - 6, 24):
                for k in range(3):
                    pygame.draw.rect(s, hi, (rect.left + 12 + k * (w - 30) // 3, yy, 6, 2))
        for i in range(9):
            x = r.randint(0, ww)
            y0 = r.randint(0, wh)
            for k in range(8):
                pygame.draw.line(s, edge, (x, y0 + k * 34), (x, y0 + k * 34 + 16), 1)
        for i in range(6):
            _soft_blob(s, acc, r.randint(0, ww), r.randint(0, wh),
                       r.randint(120, 300), r.randint(80, 180), 15)

    elif m == 'void':
        for i in range(12):
            x, y = r.randint(0, ww), r.randint(int(wh * .1), wh)
            w, h = r.randint(50, 130), r.randint(160, 460)
            a = r.uniform(-.18, .18)
            pts = [(x, y), (x + w, y + w * a), (x + w, y + w * a + h), (x, y + h)]
            pygame.draw.polygon(s, fill, pts)
            pygame.draw.polygon(s, edge, pts, 1)
            pygame.draw.line(s, fill2, (x + 10, y + 20), (x + 10, y + h - 30), 2)
        for i in range(7):
            x, y = r.randint(0, ww), 0
            px, py = x, y
            pts = [(px, py)]
            for k in range(5):
                px += r.randint(-40, 40)
                py += r.randint(80, 160)
                pts.append((px, py))
            pygame.draw.lines(s, fill, False, pts, 3)
            pygame.draw.lines(s, edge, False, pts, 1)
        for i in range(6):
            _soft_blob(s, acc, r.randint(0, ww), r.randint(0, wh),
                       r.randint(140, 320), r.randint(100, 220), 14)

    else:  # core
        for i in range(max(8, int(9 * ak))):
            cx, cy = r.randint(0, ww), r.randint(0, wh)
            for rr in (r.randint(280, 420), r.randint(500, 700), r.randint(760, 980)):
                wd = max(5, rr // 32)
                pygame.draw.circle(s, fill, (cx, cy), rr, wd)
                pygame.draw.circle(s, edge, (cx, cy), rr, 1)
                pygame.draw.circle(s, fill2, (cx, cy), rr - wd, 1)
                for k in range(8):
                    a0 = k * math.pi / 4 + i
                    pygame.draw.arc(s, fill2, (cx - rr, cy - rr, rr * 2, rr * 2),
                                    a0, a0 + .38, 2)
            _soft_blob(s, acc, cx, cy, 120, 120, 46)
            pygame.draw.circle(s, mix(acc, COL['white'], .45), (cx, cy), 26, 2)
            pygame.draw.circle(s, acc, (cx, cy), 8, 1)
        for i in range(max(14, int(14 * ak))):
            cx, cy = r.randint(0, ww), r.randint(0, wh)
            a = r.uniform(0, math.pi * 2)
            L = r.randint(120, 380)
            pygame.draw.line(s, edge, (cx, cy), (cx + math.cos(a) * L, cy + math.sin(a) * L), 2)
        for i in range(max(8, int(8 * ak))):
            _soft_blob(s, acc, r.randint(0, ww), r.randint(0, wh),
                       r.randint(120, 300), r.randint(80, 180), 20)

    # 中景废墟群：细碎的支架、断墙和漂浮残骸，填满主特征之间的空白
    for i in range(max(90, int(90 * ak))):
        x, y = r.randint(-80, ww + 40), r.randint(0, wh)
        w2, h2 = r.randint(38, 140), r.randint(46, 210)
        kind = i % 4
        if kind == 0:
            pts = [(x, y), (x + w2 * .3, y - h2), (x + w2 * .7, y - h2 * .7), (x + w2, y)]
            pygame.draw.polygon(s, fill2, pts)
            pygame.draw.polygon(s, edge, pts, 1)
        elif kind == 1:
            rect = pygame.Rect(x, y - h2, w2, h2)
            pygame.draw.rect(s, mix(edge, th['bot'], .55), rect, 1)
            for k in range(1, 4):
                xx = rect.left + rect.w * k / 4
                pygame.draw.line(s, mix(edge, th['bot'], .55), (xx, rect.top), (xx, rect.bottom), 1)
            pygame.draw.line(s, mix(fill2, edge, .35), (rect.left, rect.bottom),
                             (rect.right, rect.top), 1)
            pygame.draw.line(s, mix(edge, th['bot'], .55), (rect.left, rect.centery),
                             (rect.right, rect.centery), 1)
        elif kind == 2:
            pygame.draw.arc(s, fill2, (x, y - h2, w2 * 2, h2 * 2), math.pi * .1, math.pi * 1.4, 2)
            pygame.draw.arc(s, edge, (x, y - h2, w2 * 2, h2 * 2), math.pi * .1, math.pi * 1.4, 1)
        else:
            for k in range(3):
                rr = r.randint(10, 32)
                pygame.draw.circle(s, fill2, (x + k * 28, y - h2 * .2 - k * 16), rr, 1)
        if i % 5 == 0:
            _soft_blob(s, acc, x + w2 * .4, y - h2 * .2, w2 * .6, h2 * .2, 14)

    # 全层共有的微粒与残骸
    for i in range(max(700, int(700 * ak))):
        x, y = r.randint(0, ww), r.randint(0, wh)
        kd = i % 7
        if kd == 0:
            L = r.randint(8, 30)
            a = r.uniform(0, math.pi * 2)
            pygame.draw.line(s, mix(edge, th['bot'], .35),
                             (x, y), (x + math.cos(a) * L, y + math.sin(a) * L), 1)
        elif kd == 1:
            sz = r.randint(3, 11)
            pts = [(x, y), (x + sz, y + r.randint(-2, 3)), (x + r.randint(1, sz), y + sz)]
            pygame.draw.polygon(s, fill2, pts)
            pygame.draw.polygon(s, edge, pts, 1)
        elif kd == 2:
            pygame.draw.circle(s, edge, (x, y), r.choice((1, 1, 2)))
        elif kd == 3:
            rr = r.randint(6, 20)
            pygame.draw.arc(s, fill2, (x - rr, y - rr, rr * 2, rr * 2),
                            r.uniform(0, 3), r.uniform(3.2, 5.8), 1)
        if i % 37 == 0:
            _soft_blob(s, mix(acc, hi, .25), x, y, r.randint(12, 34), r.randint(8, 20), 12)



def zone_world(layer):
    key = (layer, G.ww, G.wh)
    s = ZONE_WORLD.get(key)
    if s is not None:
        return s
    th = theme_of(layer)
    s = pygame.Surface((G.ww, G.wh))
    for y in range(G.wh):
        t = y / max(1, G.wh - 1)
        s.fill(mix(th['top'], th['bot'], t ** 1.08), (0, y, G.ww, 1))
    r = random.Random(hash(key) & 0x7FFFFFFF)
    _world_features(s, layer, r, th)
    for i in range(4):
        _soft_blob(s, mix(th['top'], COL[th['accent']], .30), r.randint(0, G.ww),
                   int(G.wh * (.12 + i * .27)), r.randint(500, 1000),
                   r.randint(90, 200), 14)
    ZONE_WORLD[key] = s
    _WORLD_LRU.append(key)
    while len(_WORLD_LRU) > 2:
        k = _WORLD_LRU.pop(0)
        if k != key:
            ZONE_WORLD.pop(k, None)
    return s


def fog_of(layer):
    fs = FOG_CACHE.get(layer)
    if fs:
        return fs
    th = theme_of(layer)
    fs = []
    for i in range(3):
        sp = pygame.Surface((620, 330), pygame.SRCALPHA)
        col = mix(mix(th['bot'], th['top'], .35), COL[th['accent']], .22)
        _soft_blob(sp, col, 200, 150, 190, 82, 18)
        _soft_blob(sp, col, 405, 178, 235, 96, 13)
        _soft_blob(sp, col, 520, 132, 150, 64, 9)
        fs.append(sp)
    FOG_CACHE[layer] = fs
    return fs


def draw_zone_bg(surf, layer):
    surf.blit(zone_world(layer), (0, 0), (int(G.camx), int(G.camy), W, H))
    draw_parallax(surf)
    fs = fog_of(layer)
    for i, sp in enumerate(fs):
        x = int((G.t * (-6 - i * 5) + i * 520) % (W + 440)) - 220
        y = int(H * (.12 + i * .34)) - 100
        surf.blit(sp, (x, y))
    # 区域光柱
    sh = shaft_for(theme_of(layer)['accent'])
    if sh:
        for k in range(3):
            sx = int((G.t * 15 + k * 470) % (W + 300)) - 220
            surf.blit(sh, (sx, 0))


AMB = []


def build_ambient(layer):
    """每层换一套环境粒子：气泡、孢子、余烬、碎镜、雪、火星、雨、尘、波纹"""
    AMB.clear()
    th = theme_of(layer)
    n = {'wave': 34, 'rain': 110, 'snow': 110, 'spore': 80, 'bubble': 90,
         'ember': 80, 'shard': 70, 'spark': 80, 'dust': 70}.get(th['amb'], 80)
    for i in range(n):
        AMB.append({'x': rnd(W), 'y': rnd(H), 's': rnd(120, 20), 'r': rnd(2.6, .7),
                    'ph': rnd(6.28), 'a': rnd(.6, .14), 'k': th['amb']})
    load_zone_content(layer)


def draw_ambient(surf, dt):
    if not G.run:
        return
    th = theme_of(G.run.layer)
    acc = COL[th['accent']]
    for p in AMB:
        k = p['k']
        sp = p['s']
        if k == 'bubble':
            p['y'] -= sp * .55 * dt
            p['x'] += math.sin(G.t * .8 + p['ph']) * 7 * dt
            if p['y'] < -10:
                p['y'] = H + 10
                p['x'] = rnd(W)
            c = mix(COL['bg0'], acc, p['a'])
            pygame.draw.circle(surf, c, (int(p['x']), int(p['y'])), int(p['r']), 1)
        elif k == 'rain':
            p['y'] += sp * 2.1 * dt
            p['x'] -= sp * .18 * dt
            if p['y'] > H + 12 or p['x'] < -8:
                p['y'] = -14
                p['x'] = rnd(W + 60)
            c = mix(COL['bg0'], acc, p['a'])
            ln = int(9 + p['r'] * 6)
            pygame.draw.line(surf, c, (int(p['x']), int(p['y'])),
                             (int(p['x']), int(p['y']) - ln), 1)
        elif k == 'ember':
            p['y'] -= sp * .9 * dt
            p['x'] += math.sin(G.t * 1.4 + p['ph']) * 12 * dt
            if p['y'] < -8:
                p['y'] = H + 8
                p['x'] = rnd(W)
            c = mix(COL['bg0'], acc, p['a'])
            pygame.draw.circle(surf, c, (int(p['x']), int(p['y'])), int(max(1, p['r'] * .8)))
            if p['a'] > .4:
                glow_at(surf, acc, p['x'], p['y'], 16, 1)
        elif k == 'snow':
            p['y'] += sp * .7 * dt
            p['x'] += math.sin(G.t * .5 + p['ph']) * 14 * dt
            if p['y'] > H + 6:
                p['y'] = -6
                p['x'] = rnd(W)
            c = mix(COL['bg0'], COL['white'], p['a'])
            pygame.draw.circle(surf, c, (int(p['x']), int(p['y'])), int(max(1, p['r'] * .7)))
        elif k == 'shard':
            p['x'] += sp * .35 * dt
            p['y'] += math.sin(G.t * .4 + p['ph']) * 10 * dt
            if p['x'] > W + 10:
                p['x'] = -10
                p['y'] = rnd(H)
            c = mix(COL['bg0'], acc, p['a'])
            sz = 3 + p['r'] * 2
            pygame.draw.polygon(surf, c, [(p['x'], p['y'] - sz), (p['x'] + sz * .6, p['y'] + sz),
                                          (p['x'] - sz * .6, p['y'] + sz)], 1)
        elif k == 'spark':
            p['y'] -= sp * 1.5 * dt
            p['x'] += math.sin(G.t * 3 + p['ph']) * 18 * dt
            if p['y'] < -8:
                p['y'] = H + 8
                p['x'] = rnd(W)
            c = mix(COL['bg0'], acc, p['a'])
            pygame.draw.line(surf, c, (int(p['x']), int(p['y'])),
                             (int(p['x']), int(p['y']) + 5), 1)
        elif k == 'wave':
            p['y'] += sp * .22 * dt
            p['x'] += sp * .1 * dt
            if p['y'] > H + 8 or p['x'] > W + 8:
                p['y'] = rnd(H)
                p['x'] = rnd(W)
            c = mix(COL['bg0'], acc, p['a'] * .8)
            pygame.draw.ellipse(surf, c, (p['x'] - 30, p['y'] - 9, 60, 18), 1)
            pygame.draw.ellipse(surf, mix(COL['bg0'], acc, p['a'] * .35),
                                (p['x'] - 18, p['y'] - 5, 36, 10), 1)
        else:  # spore / dust
            p['y'] -= sp * .25 * dt
            p['x'] += math.sin(G.t * .3 + p['ph']) * 10 * dt
            if p['y'] < -8:
                p['y'] = H + 8
                p['x'] = rnd(W)
            c = mix(COL['bg0'], acc, p['a'])
            pygame.draw.circle(surf, c, (int(p['x']), int(p['y'])), int(max(1, p['r'])))


def draw_edge_markers(surf):
    """屏幕外目标的边缘指示，大图不至于迷路"""
    if not G.run or not G.player:
        return
    p = G.player
    marks = []
    for e in G.enemies:
        if e.dead:
            continue
        sx, sy = e.x - G.camx, e.y - G.camy
        if -40 < sx < W + 40 and -40 < sy < H + 40:
            continue
        marks.append((dist2((e.x, e.y), (p.x, p.y)), e.x, e.y, 4, e.elite))
    if G.boss:
        b = G.boss
        sx, sy = b.x - G.camx, b.y - G.camy
        if not (-80 < sx < W + 80 and -80 < sy < H + 80):
            marks.append((0, b.x, b.y, 8, True))
    marks.sort(key=lambda z: z[0])
    for d, wx, wy, sz, elite in marks[:8]:
        sx, sy = wx - G.camx, wy - G.camy
        ang = math.atan2(sy - H / 2, sx - W / 2)
        ex = clamp(sx, 26, W - 26)
        ey = clamp(sy, 74, H - 26)
        dx, dy = math.cos(ang), math.sin(ang)
        tip = (ex + dx * 10, ey + dy * 10)
        left = (ex - dy * 4 - dx * 5, ey + dx * 4 - dy * 5)
        right = (ex + dy * 4 - dx * 5, ey - dx * 4 - dy * 5)
        c = mix(COL['bg0'], COL['coral' if elite else 'amber'], .8)
        pygame.draw.polygon(surf, c, [tip, left, right], 0)


def draw_world(surf, dt):
    if G.run:
        draw_zone_bg(surf, G.run.layer)
    else:
        surf.blit(BG or _zone_grad(1), (0, 0))
    draw_ambient(surf, dt)

    ox = -G.camx
    oy = -G.camy
    if G.shake > 0:
        s = G.shake * G.shake_scale
        ox += random.uniform(-s, s) * .6
        oy += random.uniform(-s, s) * .6

    if G.run:
        draw_landmark(surf, ox, oy)
        draw_props(surf, ox, oy)
    draw_drops(surf, ox, oy)
    draw_fires(surf, ox, oy)
    for e in G.enemies:
        draw_enemy(surf, e, ox, oy)
    if G.boss:
        draw_boss(surf, G.boss, ox, oy)
    draw_well(surf, ox, oy)
    draw_bullets(surf, ox, oy)
    if G.run:
        draw_caches(surf, ox, oy)
    if G.player and G.scene in ('play', 'cards', 'pause', 'win') and G.player.hp > 0:
        draw_player(surf, ox, oy)
        draw_player_blades(surf, ox, oy)
    draw_particles(surf, ox, oy)
    draw_foreground(surf)
    draw_post_fx(surf)
    draw_edge_markers(surf)
    if G.scene in ('play', 'pause'):
        draw_hud(surf)
        draw_layer_card(surf)

    if G.flashv > 0:
        c = mix(COL['bg0'], COL['white'], G.flashv * .5 * G.flash_scale)
        surf.fill(c, special_flags=pygame.BLEND_ADD)
    if G.scene == 'play':
        draw_aim_reticle(surf)

# ---------------------------------------------------------------- 统一后处理
_POST_FX = {}


def _make_post_fx():
    global _POST_FX
    if _POST_FX:
        return _POST_FX
    vig = pygame.Surface((W, H), pygame.SRCALPHA)
    # 外围逐圈压暗，中心和四角保持可读；这是全游戏统一的“深水镜头”层
    for i in range(26):
        a = int(4 + i * 1.7)
        rect = pygame.Rect(i * 5, i * 4, W - i * 10, H - i * 8)
        pygame.draw.rect(vig, (0, 2, 5, a), rect, 1)
    for i in range(10):
        a = int(2 + i * 1.5)
        pygame.draw.rect(vig, (0, 2, 5, a), pygame.Rect(i * 3, i * 2, W - i * 6, H - i * 4), 1)
    scan = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(0, H, 3):
        pygame.draw.line(scan, (0, 0, 0, 7), (0, y), (W, y))
    noise = pygame.Surface((180, 180), pygame.SRCALPHA)
    for y in range(180):
        for x in range(0, 180, 2):
            v = random.randint(0, 22)
            noise.set_at((x, y), (220, 240, 255, v))
    _POST_FX = {'vig': vig, 'scan': scan, 'noise': noise}
    return _POST_FX


def draw_post_fx(surf):
    fx = _make_post_fx()
    surf.blit(fx['vig'], (0, 0))
    surf.blit(fx['scan'], (0, 0))
    ox = int((G.t * 13) % 180)
    oy = int((G.t * 9) % 180)
    for y in range(-oy, H, 180):
        for x in range(-ox, W, 180):
            surf.blit(fx['noise'], (x, y))

# -*- coding: utf-8 -*-
# ================================================================
#  布局 / 场景
# ================================================================
CARD_W, CARD_H, CARD_GAP = 316, 420, 24


def layout():
    G.rects = []
    if G.scene == 'title':
        G.rects = [('newgame', pygame.Rect(86, 300, 344, 58)),
                   ('continue', pygame.Rect(86, 366, 344, 54)),
                   ('codex', pygame.Rect(86, 430, 344, 44)),
                   ('settings', pygame.Rect(86, 486, 164, 36)),
                   ('help', pygame.Rect(266, 486, 164, 36)),
                   ('exitgame', pygame.Rect(86, 536, 344, 32))]
    elif G.scene == 'intro':
        G.intro_skip = pygame.Rect(W - 190, H - 82, 130, 38)
        G.rects = [('introskip', G.intro_skip)]
    elif G.scene == 'slots':
        G.slot_rects = [pygame.Rect(150, 176 + i * 122, 980, 104) for i in range(SLOT_COUNT)]
        G.rects = [('slot%d' % i, r) for i, r in enumerate(G.slot_rects)]
        G.slot_back = pygame.Rect(W / 2 - 100, H - 96, 200, 46)
        G.rects.append(('slotback', G.slot_back))
    elif G.scene == 'hub':
        d = read_slot(G.save_slot) if G.save_slot is not None and int(G.save_slot) >= 0 else None
        G.rects = [('hubdive', pygame.Rect(640, 154, 540, 54)),
                   ('hublab', pygame.Rect(640, 292, 260, 52)),
                   ('hubshards', pygame.Rect(920, 292, 260, 52)),
                   ('hubdelete', pygame.Rect(640, 362, 260, 38)),
                   ('hubback', pygame.Rect(920, 362, 260, 38))]
        if d and d.get('run_active'):
            G.rects.insert(1, ('hubnew', pygame.Rect(640, 220, 540, 52)))
    elif G.scene == 'shards':
        G.rects = [('shardslab', pygame.Rect(W / 2 - 250, H - 154, 220, 50)),
                   ('shardsback', pygame.Rect(W / 2 + 30, H - 154, 220, 50))]
    elif G.scene == 'select':
        G.mode_rects = [pygame.Rect(420 + i * 132, 70, 124, 32) for i in range(len(MODES))]
        start = G.ship_page * SHIPS_PER_PAGE
        for j, i in enumerate(range(start, min(start + SHIPS_PER_PAGE, len(SHIPS)))):
            col = j % 2
            row = j // 2
            G.rects.append(('ship%d' % i,
                            pygame.Rect(56 + col * 168, 132 + row * 64, 160, 60)))
        G.rects.append(('shipprev', pygame.Rect(56, 524, 120, 34)))
        G.rects.append(('shipnext', pygame.Rect(184, 524, 120, 34)))
        G.rects.append(('dive', pygame.Rect(W - 56 - 236, 700, 236, 50)))
        G.rects.append(('back', pygame.Rect(W - 56 - 236 - 16 - 176, 700, 176, 50)))
    elif G.scene == 'cards':
        total = CARD_W * 3 + CARD_GAP * 2
        x0 = (W - total) // 2
        for i in range(3):
            G.rects.append(('card%d' % i, pygame.Rect(x0 + i * (CARD_W + CARD_GAP), 168, CARD_W, CARD_H)))
    elif G.scene == 'pause':
        G.rects = [('resume', pygame.Rect(W / 2 - 440, 470, 200, 54)),
                   ('savegame', pygame.Rect(W / 2 - 220, 470, 200, 54)),
                   ('saveexit', pygame.Rect(W / 2, 470, 200, 54)),
                   ('quit', pygame.Rect(W / 2 + 220, 470, 200, 54)),
                   ('settings', pygame.Rect(W / 2 - 232, 558, 140, 34)),
                   ('codex', pygame.Rect(W / 2 - 70, 558, 140, 34)),
                   ('help', pygame.Rect(W / 2 + 92, 558, 140, 34))]
    elif G.scene == 'settings':
        G.rects = [
            ('setvol-', pygame.Rect(W - 334, 147, 42, 34)),
            ('setvol+', pygame.Rect(W - 138, 147, 42, 34)),
            ('setshake', pygame.Rect(W - 260, 197, 190, 34)),
            ('setflash', pygame.Rect(W - 260, 247, 190, 34)),
            ('setfull', pygame.Rect(W - 260, 297, 190, 34)),
            ('setaim', pygame.Rect(W - 260, 347, 190, 34)),
            ('setlang', pygame.Rect(W - 260, 397, 190, 34)),
            ('setvoice', pygame.Rect(W - 260, 447, 190, 34)),
            ('setjoy', pygame.Rect(W - 260, 497, 190, 34)),
            ('setback', pygame.Rect(W / 2 - 100, H - 108, 200, 50)),
        ]
    elif G.scene == 'help':
        G.rects = [('helpback', pygame.Rect(W / 2 - 100, H - 96, 200, 50))]
    elif G.scene == 'lab':
        G.lab_rects = [pygame.Rect(120, 158 + i * 54, 1040, 44) for i in range(len(UPGRADES))]
        G.rects = [('lab%d' % i, r) for i, r in enumerate(G.lab_rects)]
        G.rects.append(('labbuy', pygame.Rect(W / 2 - 210, 650, 200, 48)))
        G.rects.append(('labback', pygame.Rect(W / 2 + 10, 650, 200, 48)))
    elif G.scene == 'codex':
        G.rects = []
        for i, nm in enumerate(('飞船', 'BOSS', '增幅', '敌机')):
            G.rects.append(('codex%d' % i, pygame.Rect(56 + i * 112, 106, 102, 34)))
        G.rects.append(('codeprev', pygame.Rect(W - 330, H - 92, 90, 42)))
        G.rects.append(('codenext', pygame.Rect(W - 230, H - 92, 90, 42)))
        G.rects.append(('codexback', pygame.Rect(W - 130, H - 92, 74, 42)))
    elif G.scene in ('dead', 'win'):
        G.rects = [('again', pygame.Rect(W / 2 - 232, 512, 216, 54)),
                   ('ships', pygame.Rect(W / 2 + 16, 512, 216, 54))]



def wrap(s, size, maxw, bold=False):
    s = tr(s)
    f = font(size, bold)
    lines = []
    cur = ''
    for ch in s:
        if ch == '\n':
            lines.append(cur)
            cur = ''
            continue
        if cur and f.size(cur + ch)[0] > maxw:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def draw_button(surf, rect, label, col='aqua', size=14, filled=False):
    size = fit_size(label, size, rect.width - 24, True, 10)
    hover = rect.collidepoint(G.pointer)
    c = COL[col]
    if hover or filled:
        bgc = mix(COL['bg1'], c, .22 if hover else .14)
        pygame.draw.rect(surf, bgc, rect)
    pygame.draw.rect(surf, c if hover else mix(COL['bg1'], c, .55), rect, 1)
    tx = rect.centerx
    ty = rect.centery - font(size, True).get_height() // 2
    draw_text(surf, label, size, COL['ink'] if hover else mix(COL['ink'], COL['bg0'], .25),
              (tx, ty), align='center', bold=True)
    if hover:
        pygame.draw.line(surf, c, (rect.left + 10, rect.bottom - 1), (rect.right - 10, rect.bottom - 1))


def draw_panel(surf, rect, col='steel', fill=(5, 15, 21)):
    pygame.draw.rect(surf, fill, rect)
    pygame.draw.rect(surf, COL[col], rect, 1)


def draw_link(surf, rect, label, col='aqua'):
    hover = rect.collidepoint(G.pointer)
    c = COL[col] if hover else COL['dimmer']
    draw_text(surf, label, 11, c, (rect.centerx, rect.centery), align='center')
    if hover:
        pygame.draw.line(surf, c, (rect.left + 6, rect.bottom - 2),
                         (rect.right - 6, rect.bottom - 2))


def rect_of(act):
    for a, r in G.rects:
        if a == act:
            return r
    return None


# ---------------------------------------------------------------- 标题
def menu_button(surf, rect, zh, en, col='aqua', sel=False, disabled=False, num=''):
    hover = rect.collidepoint(G.pointer) and not disabled
    c = COL[col] if not disabled else COL['dim']
    if sel and not disabled:
        pygame.draw.rect(surf, mix(COL['bg1'], c, .20), rect)
        pygame.draw.rect(surf, c, rect, 2)
        pygame.draw.rect(surf, c, (rect.left, rect.top, 4, rect.height))
    elif hover and not disabled:
        pygame.draw.rect(surf, mix(COL['bg1'], c, .10), rect)
        pygame.draw.rect(surf, mix(COL['bg1'], c, .6), rect, 1)
    else:
        pygame.draw.rect(surf, (4, 13, 19), rect)
        pygame.draw.rect(surf, mix(COL['bg1'], c, .30), rect, 1)
    if num:
        draw_text(surf, num, 9, mix(COL['bg0'], c, .9), (rect.left + 16, rect.top + 9))
    if rect.height >= 52:
        draw_text(surf, zh, fit_size(zh, 21, rect.width - 70, True),
                  COL['ink'] if not disabled else COL['dimmer'], (rect.left + 44, rect.top + 9), bold=True)
        draw_text(surf, en, 9, mix(COL['bg0'], c, .85) if not disabled else COL['dimmer'],
                  (rect.left + 44, rect.top + 36))
    else:
        draw_text(surf, zh, fit_size(zh, 15, rect.width - 90, True),
                  COL['ink'] if not disabled else COL['dimmer'], (rect.left + 44, rect.top + 8), bold=True)
        if en:
            draw_text(surf, en, 8, mix(COL['bg0'], c, .8) if not disabled else COL['dimmer'],
                      (rect.right - 16, rect.top + 11), align='right')
    if not disabled and (sel or hover):
        draw_text(surf, '›', 18, c, (rect.right - 14, rect.centery - 12), align='right')


def draw_title(surf, dt):
    draw_bg(surf, dt)
    sx, sy = int(W * .61), int(H * .62)
    draw_sonar(surf, int(W * .74), int(H * .60), G.t)
    bob = math.sin(G.t * .9) * 9
    glow_at(surf, COL['aqua'], sx, sy + bob, 160, 1)
    draw_ship_at(surf, sx, sy + bob, math.sin(G.t * .55) * .06, scale=1.35)

    draw_text(surf, TITLE_EN if META.get('lang') else TITLE, 66, COL['ink'], (86, 78), bold=True)
    draw_text(surf, (TITLE_EN + ' · DEEP-SEA ROGUELIKE') if not META.get('lang') else 'DEEP-SEA ROGUELIKE · SIX MODES',
              15, mix(COL['bg0'], COL['aqua'], .85), (88, 158))
    draw_text(surf, L('深海肉鸽 · 每一次下潜都不相同', 'A ROGUELIKE DESCENT INTO THE ABYSS'),
              11, COL['dimmer'], (88, 184))
    pygame.draw.line(surf, mix(COL['bg1'], COL['aqua'], .35), (88, 214), (430, 214))
    draw_text(surf, 'ABYSS ECHO  //  DIVE CONTROL', 9, COL['dimmer'], (88, 226))

    slots = [read_slot(i) for i in range(SLOT_COUNT)]
    has_save = any(slots)
    df = DIFFS[G.diff]
    md = MODES[G.mode]
    menu = [
        ('newgame', L('开始新的下潜', 'NEW DIVE'), 'START A FRESH RUN', 'aqua', False, '01'),
        ('continue', L('继续游戏', 'CONTINUE'), 'ENTER A SAVE SLOT', 'gold', not has_save, '02'),
        ('codex', L('回廊档案', 'ARCHIVE'), 'SHIPS · BOSSES · AUGMENTS', 'steel', False, '03'),
        ('settings', L('设置', 'SETTINGS'), '', 'steel', False, '04'),
        ('help', L('操作说明', 'HOW TO PLAY'), '', 'steel', False, '05'),
        ('exitgame', L('退出游戏', 'QUIT'), '', 'steel', False, '06'),
    ]
    for i, (act, zh, en, col, dis, num) in enumerate(menu):
        r = rect_of(act)
        if r:
            menu_button(surf, r, zh, en, col, sel=(G.menu_sel == i), disabled=dis, num=num)

    # 右侧状态卡：只放玩家真正需要的信息，不做资料墙
    card = pygame.Rect(W - 390, 292, 312, 236)
    draw_panel(surf, card, 'steel', (4, 12, 18))
    draw_text(surf, L('下潜准备', 'DIVE STATUS'), 10, COL['dimmer'], (card.left + 18, card.top + 14))
    pygame.draw.line(surf, mix(COL['bg1'], COL['aqua'], .30), (card.left + 18, card.top + 34),
                     (card.right - 18, card.top + 34))
    draw_text(surf, L('%s · %s' % (md['name'], df['name']), '%s · %s' % (md['en'], df['en'])),
              16, COL['ink'], (card.left + 18, card.top + 46), bold=True)
    draw_text(surf, L('模式与难度在选船页调整', 'Mode and difficulty are set on the diver screen'),
              9, COL['dimmer'], (card.left + 18, card.top + 74))
    rec = best_record(G.mode, G.diff)
    draw_text(surf, L('本模式最深', 'BEST DEPTH'), 9, COL['dimmer'], (card.left + 18, card.top + 104))
    draw_text(surf, ('第 %d 层' % rec.get('layer', 0)) if rec.get('layer', 0) else L('尚未下潜', 'NO DIVE YET'),
              15, COL['ink'], (card.left + 18, card.top + 120), bold=True)
    draw_text(surf, L('最高分', 'BEST SCORE'), 9, COL['dimmer'], (card.left + 170, card.top + 104))
    draw_text(surf, '{:,}'.format(rec.get('score', 0)), 15, COL['gold'],
              (card.left + 170, card.top + 120), bold=True)
    used = sum(1 for s in slots if s)
    draw_text(surf, L('存档槽', 'SAVE SLOTS'), 9, COL['dimmer'], (card.left + 18, card.top + 158))
    for i in range(SLOT_COUNT):
        x = card.left + 18 + i * 28
        pygame.draw.rect(surf, COL['aqua'] if slots[i] else mix(COL['bg1'], COL['dim'], .35),
                         (x, card.top + 176, 20, 8))
    draw_text(surf, L('%d / %d 已使用' % (used, SLOT_COUNT), '%d / %d USED' % (used, SLOT_COUNT)),
              9, COL['dim'], (card.left + 18, card.top + 192))
    draw_text(surf, L('工坊与结晶随存档独立', 'Workshop & shards live in each save'),
              9, COL['dimmer'], (card.left + 18, card.top + 212))

    draw_text(surf, L('↑ ↓ 选择   ·   Enter 确认   ·   鼠标点击   ·   C 档案   ·   O 设置   ·   H 说明',
                     'UP/DOWN SELECT   ·   ENTER CONFIRM   ·   CLICK   ·   C ARCHIVE   ·   O SETTINGS   ·   H HELP'),
              10, COL['dimmer'], (88, 616))
    draw_text(surf, 'v%s' % VERSION, 9, COL['dimmer'], (W - 30, H - 32), align='right')


def draw_intro(surf, dt):
    draw_bg(surf, dt)
    sx, sy = int(W * .74), int(H * .58)
    draw_sonar(surf, sx, sy, G.t * .7)
    draw_ship_at(surf, sx, sy + math.sin(G.t * .6) * 8, .04, scale=1.3, alpha_blink=False)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((1, 5, 9, 96))
    surf.blit(veil, (0, 0))

    draw_text(surf, L('序章', 'PROLOGUE'), 11, mix(COL['bg0'], COL['gold'], .95), (88, 68))
    draw_text(surf, L('新存档 · 第一次下潜', 'NEW SAVE · THE FIRST DIVE'), 34, COL['ink'], (88, 92), bold=True)
    pygame.draw.line(surf, mix(COL['bg1'], COL['gold'], .45), (88, 146), (620, 146))

    panel = pygame.Rect(88, 178, 760, 354)
    draw_panel(surf, panel, 'steel', (3, 10, 16))
    txt = intro_page_text(G.intro_page)
    shown = txt[:int(G.intro_t)] if G.intro_t < len(txt) else txt
    y = panel.top + 30
    for line in wrap(shown, 18, panel.width - 56):
        draw_text(surf, line, 18, COL['ink'] if line else COL['dim'], (panel.left + 28, y))
        y += 31
    if G.intro_t < len(txt):
        if int(G.t * 2) % 2 == 0:
            w = text_w(shown.split('\n')[-1], 18)
            draw_text(surf, '_', 18, COL['aqua'], (panel.left + 28 + w, y - 31))

    # 页码
    for i in range(len(INTRO_PAGES)):
        x = panel.left + 28 + i * 20
        pygame.draw.rect(surf, COL['gold'] if i == G.intro_page else mix(COL['bg1'], COL['dim'], .4),
                         (x, panel.bottom - 22, 12, 4))

    last = (G.intro_page >= len(INTRO_PAGES) - 1)
    draw_text(surf, L('点击 / 空格 / Enter 继续', 'CLICK / SPACE / ENTER TO CONTINUE') if not last else
              L('点击 / 空格 / Enter 进入存档', 'CLICK / SPACE / ENTER TO ENTER SAVE'),
              11, COL['dim'], (88, 574))
    skip = G.intro_skip or pygame.Rect(W - 190, H - 82, 130, 38)
    draw_button(surf, skip, L('跳过 · SKIP', 'SKIP'), 'steel', 12)
    draw_text(surf, L('ESC 也可以直接跳过', 'ESC also skips'), 9, COL['dimmer'],
              (skip.right, skip.bottom + 8), align='right')
    draw_text(surf, 'v%s' % VERSION, 9, COL['dimmer'], (W - 30, H - 32), align='right')


def draw_slots(surf, dt):
    draw_bg(surf, dt)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((2, 7, 11, 135))
    surf.blit(veil, (0, 0))
    loading = (G.slot_mode == 'load')
    draw_text(surf, L('存档槽', 'SAVE SLOTS'), 38, COL['ink'], (W / 2, 58), align='center', bold=True)
    draw_text(surf, L('进入一个存档；工坊、结晶和局内检查点都独立保存在槽内',
                     'Enter a save; workshop, shards and checkpoint are stored per slot'),
              11, COL['dim'], (W / 2, 108), align='center')
    for i in range(SLOT_COUNT):
        r = G.slot_rects[i]
        d = read_slot(i)
        hover = r.collidepoint(G.pointer)
        sel = (G.slot_sel == i)
        c = COL['aqua'] if d else COL['dim']
        if hover or sel:
            pygame.draw.rect(surf, mix(COL['bg1'], c, .07 if hover else .04), r)
        else:
            pygame.draw.rect(surf, (4, 12, 18), r)
        pygame.draw.rect(surf, c, r, 2 if sel else 1)
        pygame.draw.rect(surf, c, (r.left, r.top, 4, r.height))
        draw_text(surf, '0%d' % (i + 1), 11, mix(COL['bg0'], c, .95), (r.left + 18, r.top + 14))
        if d:
            p = normalize_profile(d.get('profile'))
            active = bool(d.get('run_active'))
            if active:
                md = MODES[min(len(MODES) - 1, max(0, d.get('mode', 0)))]
                df = DIFFS[min(len(DIFFS) - 1, max(0, d.get('diff', 0)))]
                draw_text(surf, d.get('ship_name', '—'), 20, COL['ink'], (r.left + 62, r.top + 12), bold=True)
                draw_text(surf, L('%s · %s' % (md['name'], df['name']), '%s · %s' % (md['en'], df['en'])),
                          10, mix(COL['bg0'], c, .85), (r.left + 62, r.top + 42))
                draw_text(surf, L('第 %d 层 · 第 %d 波' % (d.get('layer', 1), d.get('wave', 1)),
                                 'STRATUM %d · WAVE %d' % (d.get('layer', 1), d.get('wave', 1))),
                          12, COL['dim'], (r.left + 62, r.top + 64))
            else:
                draw_text(surf, L('存档已建立', 'SAVE READY'), 18, COL['ink'], (r.left + 62, r.top + 14), bold=True)
                draw_text(surf, L('没有进行中的下潜；工坊与结晶保留', 'No active dive; workshop and shards kept'),
                          10, COL['dim'], (r.left + 62, r.top + 42))
                draw_text(surf, L('最深 第 %d 层' % int(p.get('best_layer', 0)) if p.get('best_layer') else L('尚未下潜', 'NO DIVE'),
                                 'BEST STRATUM %d' % int(p.get('best_layer', 0)) if p.get('best_layer') else 'NO DIVE'),
                          12, COL['dim'], (r.left + 62, r.top + 64))
            draw_text(surf, '{:,}'.format(int(p.get('shards', 0))), 17, COL['gold'], (r.left + 470, r.top + 34), bold=True)
            draw_text(surf, L('结晶', 'SHARDS'), 9, COL['dimmer'], (r.left + 470, r.top + 56))
            draw_text(surf, str(d.get('updated', p.get('updated', '—'))), 9, COL['dimmer'], (r.left + 610, r.top + 20))
            draw_text(surf, L('工坊合计 %d 级' % sum(int(v) for v in p.get('upg', {}).values()),
                             'WORKSHOP %d LV' % sum(int(v) for v in p.get('upg', {}).values())),
                      10, COL['dim'], (r.left + 610, r.top + 42))
            draw_button(surf, pygame.Rect(r.right - 190, r.top + 28, 160, 44),
                        L('进入存档', 'ENTER SAVE'), 'aqua', 12)
        else:
            draw_text(surf, L('空存档槽', 'EMPTY SLOT'), 18, COL['dimmer'], (r.left + 62, r.top + 18), bold=True)
            draw_text(surf, L('创建后，工坊与结晶会跟随这个存档', 'After creation, workshop and shards belong here'),
                      10, COL['dimmer'], (r.left + 62, r.top + 46))
            if not loading:
                draw_button(surf, pygame.Rect(r.right - 190, r.top + 30, 160, 44),
                            L('创建存档', 'CREATE SAVE'), 'aqua', 12)
    draw_button(surf, G.slot_back or pygame.Rect(W / 2 - 100, H - 96, 200, 46),
                L('返回主菜单', 'BACK'), 'steel', 13)
    draw_text(surf, L('每个槽独立保存工坊等级、回声结晶与局内检查点；成就、设置与记录仍为账号全局。',
                     'Each slot stores its own workshop, shards and checkpoint; achievements, settings and records stay account-wide.'),
              10, COL['dimmer'], (W / 2, H - 38), align='center')


def draw_hub(surf, dt):
    draw_bg(surf, dt)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((2, 7, 11, 138))
    surf.blit(veil, (0, 0))
    slot = int(G.save_slot) if G.save_slot is not None and int(G.save_slot) >= 0 else 0
    d = read_slot(slot)
    p = normalize_profile(d.get('profile')) if d else (G.profile or blank_profile())
    draw_text(surf, L('存档 %02d' % (slot + 1), 'SAVE SLOT %02d' % (slot + 1)),
              38, COL['ink'], (56, 34), bold=True)
    draw_text(surf, L('SAVE HUB  ·  这个存档独立的工坊、结晶与下潜记录',
                     'SAVE HUB  ·  this save owns its workshop, shards and dive record'),
              11, COL['dimmer'], (56, 88))

    panel = pygame.Rect(56, 122, 540, 548)
    draw_panel(surf, panel, 'gold', (4, 13, 19))
    draw_text(surf, L('当前下潜', 'ACTIVE DIVE'), 12, COL['dimmer'], (80, 146))
    if d and d.get('run_active'):
        md = MODES[min(len(MODES) - 1, max(0, int(d.get('mode', 0))))]
        df = DIFFS[min(len(DIFFS) - 1, max(0, int(d.get('diff', 0))))]
        draw_text(surf, d.get('ship_name', '—'), 26, COL['ink'], (80, 170), bold=True)
        draw_text(surf, L('%s · %s' % (md['name'], df['name']),
                         '%s · %s' % (md['en'], df['en'])), 12,
                  mix(COL['bg0'], COL['aqua'], .9), (80, 206))
        draw_text(surf, L('第 %d 层 · 第 %d 波' % (d.get('layer', 1), d.get('wave', 1)),
                         'STRATUM %d · WAVE %d' % (d.get('layer', 1), d.get('wave', 1))),
                  12, COL['dim'], (80, 232))
        draw_text(surf, L('%s 分  ·  %s' % ('{:,}'.format(d.get('score', 0)), fmt_time(d.get('time', 0))),
                         '%s PTS  ·  %s' % ('{:,}'.format(d.get('score', 0)), fmt_time(d.get('time', 0)))),
                  11, COL['dimmer'], (80, 258))
        draw_text(surf, L('检查点：%s' % d.get('updated', '—'), 'CHECKPOINT: %s' % d.get('updated', '—')),
                  9, COL['dimmer'], (80, 284))
    else:
        draw_text(surf, L('没有进行中的下潜', 'NO ACTIVE DIVE'), 18, COL['dimmer'], (80, 170), bold=True)
        draw_text(surf, L('可以开始一次新的下潜；工坊和结晶会保留。',
                         'Start a new dive; workshop and shards stay here.'),
                  11, COL['dim'], (80, 204))
    pygame.draw.line(surf, mix(COL['bg1'], COL['gold'], .3), (80, 326), (572, 326))
    draw_text(surf, L('本存档进度', 'SAVE PROGRESS'), 12, COL['dimmer'], (80, 344))
    draw_text(surf, L('%d' % int(p.get('shards', 0)), '%d' % int(p.get('shards', 0))),
              30, COL['gold'], (80, 366), bold=True)
    draw_text(surf, L('回声结晶', 'ECHO SHARDS'), 10, COL['dimmer'], (82, 408))
    draw_text(surf, L('%d' % int(p.get('shards_total', 0)), '%d' % int(p.get('shards_total', 0))),
              17, COL['ink'], (312, 374), bold=True)
    draw_text(surf, L('累计获得', 'TOTAL EARNED'), 10, COL['dimmer'], (314, 400))
    upg_total = sum(int(v) for v in p.get('upg', {}).values()) if isinstance(p.get('upg'), dict) else 0
    draw_text(surf, '%d' % upg_total, 17, COL['ink'], (80, 462), bold=True)
    draw_text(surf, L('工坊等级合计', 'WORKSHOP LEVELS'), 10, COL['dimmer'], (82, 488))
    draw_text(surf, '%d' % int(p.get('runs', 0)), 17, COL['ink'], (312, 462), bold=True)
    draw_text(surf, L('此存档出击', 'SORTIES'), 10, COL['dimmer'], (314, 488))
    draw_text(surf, L('第 %d 层' % int(p.get('best_layer', 0)) if p.get('best_layer') else L('尚未下潜', 'NO DIVE'),
                     'STRATUM %d' % int(p.get('best_layer', 0)) if p.get('best_layer') else 'NO DIVE'),
              17, COL['ink'], (80, 524), bold=True)
    draw_text(surf, L('本存档最深', 'BEST DEPTH'), 10, COL['dimmer'], (82, 550))
    draw_text(surf, '{:,}'.format(int(p.get('best_score', 0))), 17, COL['gold'], (312, 524), bold=True)
    draw_text(surf, L('本存档最高分', 'BEST SCORE'), 10, COL['dimmer'], (314, 550))
    pygame.draw.line(surf, mix(COL['bg1'], COL['gold'], .25), (80, 574), (572, 574))
    draw_text(surf, L('工坊加成快照', 'WORKSHOP SNAPSHOT'), 11, COL['dimmer'], (80, 588))
    upg = p.get('upg', {}) if isinstance(p.get('upg'), dict) else {}
    for i, u in enumerate(UPGRADES):
        ux = 80 + (i % 4) * 122
        uy = 612 + (i // 4) * 20
        lv = int(upg.get(u['id'], 0))
        nm = u.get('en', u['name']) if META.get('lang') else u['name']
        lab = '%s Lv.%d' % (nm, lv)
        draw_text(surf, lab, fit_size(lab, 8, 114, False, 7),
                  COL['gold'] if lv else COL['dimmer'], (ux, uy))
    unlocked_n = len([s for s in SHIPS if ship_unlocked(s)])
    draw_text(surf, L('已解锁 %d / %d 艘下潜器 · 序章 %s' % (
                        unlocked_n, len(SHIPS), '已播放' if p.get('intro_seen') else '未播放'),
                     '%d / %d divers unlocked · intro %s' % (
                        unlocked_n, len(SHIPS), 'seen' if p.get('intro_seen') else 'not seen')),
              8, COL['dimmer'], (80, 656))

    draw_text(surf, L('存档操作', 'SAVE ACTIONS'), 12, COL['dimmer'], (640, 132))
    active = bool(d and d.get('run_active'))
    draw_button(surf, rect_of('hubdive'), L('继续下潜', 'CONTINUE DIVE') if active else L('开始新的下潜', 'START A NEW DIVE'),
                'aqua', 14)
    if active:
        lab_new = L('再次点击重开新局', 'CLICK AGAIN TO RESTART') if G.hub_confirm_new else L('重开新局', 'START A NEW RUN')
        draw_button(surf, rect_of('hubnew'), lab_new, 'gold' if G.hub_confirm_new else 'steel', 12)
    draw_button(surf, rect_of('hublab'), L('回声工坊', 'ECHO WORKSHOP'), 'gold', 14)
    draw_button(surf, rect_of('hubshards'), L('回声结晶', 'ECHO SHARDS'), 'violet', 14)
    lab_del = L('再次点击删除存档', 'CLICK AGAIN TO DELETE') if G.hub_confirm_del else L('删除存档', 'DELETE SAVE')
    draw_button(surf, rect_of('hubdelete'), lab_del, 'coral' if G.hub_confirm_del else 'steel', 12)
    draw_button(surf, rect_of('hubback'), L('返回存档列表', 'BACK TO SAVES'), 'steel', 12)
    draw_text(surf, L('工坊与结晶只属于这个存档，换槽不会带走。',
                     'Workshop and shards belong to this save only.'),
              10, COL['dimmer'], (640, 432))
    flow = pygame.Rect(640, 454, 540, 176)
    draw_panel(surf, flow, 'steel', (4, 12, 18))
    draw_text(surf, L('接下来', 'NEXT STEPS'), 11, COL['dimmer'], (660, 468))
    steps = [
        L('1  继续下潜，或开始一次新的下潜', '1  Continue the dive, or start a new run'),
        L('2  在选船页挑下潜器、模式与难度', '2  Pick a diver, mode and difficulty'),
        L('3  每 5 波选择增幅，死亡后回到本页', '3  Choose augments every 5 waves; death returns here'),
    ]
    for i, s in enumerate(steps):
        draw_text(surf, s, 10, COL['dim'], (660, 496 + i * 26))
    draw_text(surf, L('检查点会在每波开始时自动写入本槽。',
                     'A checkpoint is written to this slot at every wave start.'),
              9, COL['dimmer'], (660, 590))
    draw_text(surf, L('ESC 返回存档列表  ·  点击按钮操作', 'ESC BACK  ·  CLICK TO ACT'),
              10, COL['dimmer'], (W / 2, H - 38), align='center')


def draw_shards(surf, dt):
    draw_bg(surf, dt)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((2, 7, 11, 145))
    surf.blit(veil, (0, 0))
    slot = int(G.save_slot) if G.save_slot is not None and int(G.save_slot) >= 0 else 0
    d = read_slot(slot)
    p = normalize_profile(d.get('profile')) if d else (G.profile or blank_profile())
    draw_text(surf, L('回声结晶', 'ECHO SHARDS'), 40, COL['ink'], (56, 34), bold=True)
    draw_text(surf, L('存档 %02d  ·  只在本存档工坊消费' % (slot + 1),
                     'SAVE %02d  ·  spent only in this save\'s workshop' % (slot + 1)),
              11, COL['dimmer'], (56, 88))
    panel = pygame.Rect(56, 122, W - 112, 424)
    draw_panel(surf, panel, 'violet', (4, 13, 19))
    sh = int(p.get('shards', 0))
    draw_text(surf, L('%d' % sh, '%d' % sh), 58, COL['gold'], (W / 2, 176), align='center', bold=True)
    draw_text(surf, L('当前可用', 'AVAILABLE'), 11, COL['dimmer'], (W / 2, 246), align='center')
    pygame.draw.line(surf, mix(COL['bg1'], COL['violet'], .35), (130, 284), (W - 130, 284))
    stats = [
        (L('累计获得', 'TOTAL EARNED'), '%d' % int(p.get('shards_total', 0))),
        (L('已投入工坊', 'SPENT IN WORKSHOP'), '%d' % max(0, int(p.get('shards_total', 0)) - sh)),
        (L('此存档出击', 'SORTIES'), '%d' % int(p.get('runs', 0))),
        (L('本存档最深', 'BEST DEPTH'), ('第 %d 层' % int(p.get('best_layer', 0))) if p.get('best_layer') else L('尚未下潜', 'NO DIVE')),
    ]
    for i, (lab, val) in enumerate(stats):
        x = 120 + i * 270
        draw_text(surf, val, 20, COL['ink'], (x, 306), bold=True)
        draw_text(surf, lab, 10, COL['dimmer'], (x, 338))
    draw_text(surf, L('结晶来自击杀、波次、层域与结算；工坊升级只影响这个存档的下一次下潜。',
                     'Shards come from kills, waves, depth and results; workshop upgrades affect this save only.'),
              10, COL['dim'], (W / 2, 388), align='center')
    draw_text(surf, L('提示：结晶不会自动转换成工坊等级，需要在工坊里手动选择升级。',
                     'Tip: shards do not auto-convert; choose upgrades manually in the workshop.'),
              10, COL['dimmer'], (W / 2, 414), align='center')
    pygame.draw.line(surf, mix(COL['bg1'], COL['violet'], .3), (120, 440), (W - 120, 440))
    draw_text(surf, L('本存档工坊加成', "THIS SAVE'S WORKSHOP"), 11, COL['dimmer'], (120, 454))
    upg = p.get('upg', {}) if isinstance(p.get('upg'), dict) else {}
    for i, u in enumerate(UPGRADES):
        ux = 120 + (i % 5) * 190
        uy = 478 + (i // 5) * 22
        lv = int(upg.get(u['id'], 0))
        nm = u.get('en', u['name']) if META.get('lang') else u['name']
        draw_text(surf, '%s  Lv.%d' % (nm, lv), 9,
                  COL['gold'] if lv else COL['dimmer'], (ux, uy))
    draw_button(surf, rect_of('shardslab'), L('前往工坊', 'OPEN WORKSHOP'), 'gold', 14)
    draw_button(surf, rect_of('shardsback'), L('返回存档', 'BACK TO SAVE'), 'steel', 13)
    draw_text(surf, L('ESC 返回存档  ·  工坊和结晶都随槽位独立', 'ESC BACK  ·  workshop and shards are per-save'),
              10, COL['dimmer'], (W / 2, H - 38), align='center')


# ---------------------------------------------------------------- 选船
def draw_select(surf, dt):
    draw_bg(surf, dt)
    draw_text(surf, '选择下潜器', 40, COL['ink'], (56, 34), bold=True)
    unlocked_n = len([s for s in SHIPS if ship_unlocked(s)])
    draw_text(surf, 'SELECT DIVER  ·  已解锁 %d / %d' % (unlocked_n, len(SHIPS)),
              12, COL['dimmer'], (56, 88))
    df = DIFFS[G.diff]
    draw_text(surf, L('难度 · %s  %s' % (df['name'], df['en']), 'DIFFICULTY · %s' % df['en']), 13,
              mix(COL['bg0'], COL[df['col']], .95), (W - 56, 44), align='right', bold=True)
    draw_text(surf, 'Tab 切换难度', 10, COL['dimmer'], (W - 56, 64), align='right')
    if G.save_slot is not None and int(G.save_slot) >= 0:
        draw_text(surf, L('存档槽 %02d' % (int(G.save_slot) + 1), 'SAVE SLOT %02d' % (int(G.save_slot) + 1)),
                  10, mix(COL['bg0'], COL['gold'], .9), (W - 56, 86), align='right')

    # ---------------- 模式 ----------------
    draw_text(surf, '模式', 10, COL['dimmer'], (420, 52))
    for i, md in enumerate(MODES):
        rect = G.mode_rects[i]
        sel = (G.mode == i)
        hover = rect.collidepoint(G.pointer)
        c = COL[md['col']]
        pygame.draw.rect(surf, mix(COL['bg1'], c, .17 if sel else (.08 if hover else .03)), rect)
        pygame.draw.rect(surf, c if (sel or hover) else mix(COL['bg1'], c, .4), rect, 2 if sel else 1)
        draw_text(surf, md['name'], 13, COL['ink'] if sel else COL['dim'],
                  (rect.centerx, rect.top + 5), align='center', bold=True)
        draw_text(surf, md['en'], 8, mix(COL['bg0'], c, .85),
                  (rect.centerx, rect.top + 23), align='center')
    md = MODES[G.mode]
    draw_text(surf, md['desc'], 9, mix(COL['bg0'], COL[md['col']], .85), (420, 108))
    draw_text(surf, '上下键 切换  ·  1-6 切模式  ·  PgUp / PgDn 翻页  ·  Enter 进入', 11,
              mix(COL['bg0'], COL['dim'], .55), (56, 700))

    # ---------------- 左侧名录 ----------------
    start = G.ship_page * SHIPS_PER_PAGE
    nvis = max(0, min(SHIPS_PER_PAGE, len(SHIPS) - start))
    visible = range(start, min(start + SHIPS_PER_PAGE, len(SHIPS)))
    for j, i in enumerate(visible):
        s = SHIPS[i]
        rect = G.rects[j][1]
        unlocked = ship_unlocked(s)
        sel = (i == G.sel)
        hover = rect.collidepoint(G.pointer)
        c = COL[s['col']] if unlocked else mix(COL['bg1'], COL['dim'], .45)
        act = sel and unlocked
        pygame.draw.rect(surf, mix(COL['bg1'], c, .13 if act else (.06 if hover else .025)), rect)
        pygame.draw.rect(surf, c if (act or hover) else mix(COL['bg1'], c, .36), rect, 2 if act else 1)
        pygame.draw.rect(surf, c, (rect.left, rect.top, 3 if act else 2, rect.height))
        compact = rect.width < 200
        if compact:
            draw_text(surf, '%02d' % (i + 1), 9, mix(COL['bg0'], c, .85),
                      (rect.left + 8, rect.top + 6))
            draw_text(surf, s['name'], fit_size(s['name'], 17, 94, True),
                      COL['ink'] if unlocked else COL['dimmer'],
                      (rect.left + 29, rect.top + 3), bold=True)
            draw_text(surf, s['role'], 10, COL['dim'], (rect.left + 29, rect.top + 27))
            if unlocked:
                draw_ship_icon(surf, (rect.right - 20, rect.top + 31), s['id'], s['col'],
                               height=34, glow=False)
                draw_text(surf, s['skill'], fit_size(s['skill'], 9, 88, False),
                          mix(COL['bg0'], c, .82), (rect.left + 29, rect.top + 45))
            else:
                draw_text(surf, L('第 %d 层解锁' % s['unlock'], 'LOCKED · L%d' % s['unlock']), 9, COL['amber'],
                          (rect.left + 29, rect.top + 46))
        else:
            draw_text(surf, '%02d' % (i + 1), 10, mix(COL['bg0'], c, .85), (rect.left + 12, rect.top + 10))
            draw_text(surf, s['name'], fit_size(s['name'], 21, 190, True),
                      COL['ink'] if unlocked else COL['dimmer'],
                      (rect.left + 36, rect.top + 6), bold=True)
            draw_text(surf, s['role'], 11, COL['dim'], (rect.left + 36, rect.top + 34))
            for k in range(s['hp']):
                pygame.draw.rect(surf, c, (rect.right - 16 - k * 10, rect.top + 46, 7, 4))
            if not unlocked:
                draw_text(surf, L('第 %d 层解锁' % s['unlock'], 'LOCKED · L%d' % s['unlock']), 10, COL['amber'],
                          (rect.right - 14, rect.top + 12), align='right')
            else:
                draw_text(surf, s['skill'], fit_size(s['skill'], 10, 150, False),
                          mix(COL['bg0'], c, .8), (rect.right - 14, rect.top + 12), align='right')

    # ---------------- 右侧详情 ----------------
    s = SHIPS[G.sel]
    pr = pygame.Rect(420, 132, W - 476, 560)
    draw_panel(surf, pr, 'steel')
    unlocked = ship_unlocked(s)
    c = COL[s['col']] if unlocked else COL['dim']
    if unlocked:
        draw_ship_at(surf, pr.left + 140, pr.top + 232, math.sin(G.t * .7) * .07,
                     s['col'], alpha_blink=False, scale=3.0, sid=s['id'])
        glow_at(surf, c, pr.left + 140, pr.top + 246, 150, 1)
    else:
        pygame.draw.rect(surf, COL['dimmer'], (pr.left + 138, pr.top + 220, 24, 19), 1)
        pygame.draw.arc(surf, COL['dimmer'], (pr.left + 141, pr.top + 204, 18, 26), .15, math.pi - .15, 2)
        draw_text(surf, '未解锁', 12, COL['dimmer'], (pr.left + 150, pr.top + 262), align='center')
        draw_text(surf, L('通关第 %d 层后开放' % s['unlock'], 'CLEAR STRATUM %d TO UNLOCK' % s['unlock']), 11, COL['amber'],
                  (pr.left + 150, pr.top + 284), align='center')

    draw_text(surf, s['name'], fit_size(s['name'], 34, pr.width - 340, True),
              COL['ink'] if unlocked else COL['dimmer'], (pr.left + 302, pr.top + 38), bold=True)
    draw_text(surf, s['role'] + '  ·  技能冷却 %.1fs' % s['cd'], 12, COL['dim'],
              (pr.left + 302, pr.top + 86))
    if unlocked:
        draw_text(surf, '第 %d 层解锁' % s['unlock'] if s['unlock'] else '初始可用', 11,
                  COL['dimmer'], (pr.right - 24, pr.top + 44), align='right')

    ident = SHIP_IDENTITIES.get(s['id'], {})
    if unlocked and ident:
        draw_text(surf, L('特性 · ', 'TRAIT · ') + L(ident['trait'], ident['trait_en']), 12, c,
                  (pr.left + 302, pr.top + 108), bold=True)
        ty = pr.top + 126
        for line in wrap(L(ident['desc'], ident['desc_en']), 9, pr.width - 330)[:2]:
            draw_text(surf, line, 9, COL['dim'], (pr.left + 302, ty))
            ty += 13

    # 三项数值
    sy = pr.top + 166
    for lab, val, bar in (('艇体', str(s['hp']), min(1, s['hp'] / 7)),
                          ('速度', str(s['speed']), min(1, s['speed'] / 420)),
                          ('伤害', '×%.2f' % s['dmg'], min(1, s['dmg'] / 1.6))):
        draw_text(surf, lab, 11, COL['dimmer'], (pr.left + 302, sy))
        draw_text(surf, val, 15, COL['ink'] if unlocked else COL['dimmer'],
                  (pr.left + 360, sy - 4), bold=True)
        pygame.draw.rect(surf, mix(COL['bg0'], COL['dim'], .25), (pr.left + 302, sy + 24, 300, 3))
        if unlocked:
            pygame.draw.rect(surf, c, (pr.left + 302, sy + 24, int(300 * bar), 3))
        sy += 46
    pat = ident.get('pattern', 'echo')
    pname = L(*SHIP_PATTERN_NAMES.get(pat, ('标准弹道', 'STANDARD')))
    stat_line = L('射速 %.1f/s  ·  穿透 %d  ·  弹道 %d  ·  %s',
                  'FIRE %.1f/s  ·  PIERCE %d  ·  SHOTS %d  ·  %s') % (
                      1 / s['rate'], s['pierce'], s['bullets'], pname)
    draw_text(surf, stat_line, fit_size(stat_line, 10, pr.width - 330, False), COL['dim'],
              (pr.left + 302, sy - 4))

    pygame.draw.line(surf, mix(COL['bg1'], COL['dim'], .3), (pr.left + 302, pr.top + 312),
                     (pr.right - 24, pr.top + 312))
    draw_text(surf, '技能 · ' + s['skill'], 16, c if unlocked else COL['dimmer'],
              (pr.left + 302, pr.top + 328), bold=True)
    yy = pr.top + 360
    for line in wrap(s['desc'], 13, pr.width - 320):
        draw_text(surf, line, 13, COL['dim'] if unlocked else COL['dimmer'], (pr.left + 302, yy))
        yy += 23

    pygame.draw.line(surf, mix(COL['bg1'], COL['dim'], .3), (pr.left + 302, pr.top + 424),
                     (pr.right - 24, pr.top + 424))
    tips = SHIP_TIPS.get(s['id'], ())
    draw_text(surf, '推荐增幅', 11, COL['dimmer'], (pr.left + 302, pr.top + 438))
    for k, aid in enumerate(tips):
        nm = AUG_BY_ID.get(aid, (aid, aid))[1]
        rr = pygame.Rect(pr.left + 302 + k * 110, pr.top + 460, 100, 26)
        pygame.draw.rect(surf, mix(COL['bg1'], c, .16), rr)
        pygame.draw.rect(surf, mix(COL['bg1'], c, .55), rr, 1)
        draw_text(surf, nm, fit_size(nm, 11, rr.width - 8, False), COL['ink'],
                  (rr.centerx, rr.top + 6), align='center')

    draw_text(surf, '本局回廊事件 · 每局随机（Boss 顺序与波次风格同样随机）', 11,
              COL['dimmer'], (pr.left + 302, pr.top + 494))
    for k, mu in enumerate(MUT_PREVIEW):
        mx = pr.left + 302 + k * 166
        mname = tr(mu['name'])
        draw_text(surf, '· ' + mname, fit_size(mname, 11, 150, False),
                  mix(COL['bg0'], COL['gold'], .85), (mx, pr.top + 514))
        mdesc = tr(mu['desc'])
        draw_text(surf, mdesc, fit_size(mdesc, 9, 150, False), COL['dim'], (mx + 8, pr.top + 530))

    draw_text(surf, '回廊记录 · %s · %s' % (MODES[G.mode]['name'], df['name']),
              10, COL['dimmer'], (pr.left + 40, pr.top + 448))
    rec_b = best_record(G.mode, G.diff)
    dep = '尚未下潜' if rec_b.get('layer', 0) <= 0 else '第 %d 层' % rec_b.get('layer', 0)
    for k, (lab, val) in enumerate((('最深', dep),
                                     ('最高分', '{:,}'.format(rec_b.get('score', 0))),
                                     ('出击', '%d 次' % (int((G.profile or {}).get('runs', 0)) if isinstance(G.profile, dict) else META.get('runs', 0))))):
        xx = pr.left + 40
        draw_text(surf, lab, 10, COL['dimmer'], (xx, pr.top + 475 + k * 24))
        vx = xx + max(56, text_w(lab, 10) + 10)
        draw_text(surf, val, 14, COL['dim'], (vx, pr.top + 471 + k * 24), bold=True)

    pages = (len(SHIPS) + SHIPS_PER_PAGE - 1) // SHIPS_PER_PAGE
    draw_button(surf, G.rects[nvis][1], '‹ 上一页', 'steel', 11)
    draw_button(surf, G.rects[nvis + 1][1], '下一页 ›', 'steel', 11)
    draw_text(surf, '第 %d / %d 页' % (G.ship_page + 1, pages), 10, COL['dimmer'],
              (192, 572), align='center')
    draw_button(surf, G.rects[-2][1], '下潜', 'aqua', 15)
    draw_button(surf, G.rects[-1][1], L('返回存档', 'BACK TO SAVE'), 'steel', 13)


# ---------------------------------------------------------------- 增幅卡
def draw_cards(surf):
    surf.blit(DIM, (0, 0))
    pact = getattr(G, 'card_kind', 'aug') == 'pact'
    draw_text(surf, L('签订深渊契约', 'SIGN A PACT') if pact else '选择增幅', 36,
              COL['ink'], (W / 2, 92), align='center', bold=True)
    if pact:
        sub = L('第 %d 层之后 · 选择一条风险契约' % G.run.layer,
                'AFTER STRATUM %d · CHOOSE A RISK PACT' % G.run.layer)
    else:
        sub = '第 %d 层结束 · 艇体回升' % G.run.layer if G.card_ctx == 'boss' else '第 %d 层 · 战斗间隙' % G.run.layer
    draw_text(surf, sub, 12, COL['dimmer'], (W / 2, 136), align='center')

    for i, a in enumerate(G.cards):
        rect = G.rects[i][1]
        hover = rect.collidepoint(G.pointer)
        rc = COL[RARITY_COL[a[3]]]
        pulse = .5 + .5 * math.sin(G.t * 2.4 + i * 1.7)
        if a[3] == 'l':
            pygame.draw.rect(surf, mix((4, 12, 18), rc, .12 + .1 * pulse),
                             rect.inflate(8 + 6 * pulse, 8 + 6 * pulse), 1)
        pygame.draw.rect(surf, mix((4, 12, 18), rc, .08 if hover else .035), rect)
        pygame.draw.rect(surf, rc if hover else mix((4, 12, 18), rc, .5), rect, 2 if hover else 1)
        pygame.draw.rect(surf, rc, (rect.left, rect.top, rect.width, 3))
        if hover:
            pygame.draw.line(surf, rc, (rect.left + 20, rect.bottom), (rect.right - 20, rect.bottom), 1)

        draw_text(surf, L('契约', 'PACT') if pact else RARITY_NAME[a[3]], 10, rc,
                  (rect.left + 22, rect.top + 20))

        # 徽记
        cx, cy = rect.centerx, rect.top + 104
        pygame.draw.circle(surf, mix((4, 12, 18), rc, .30), (cx, cy), 46, 1)
        pygame.draw.circle(surf, mix((4, 12, 18), rc, .16), (cx, cy), 36, 1)
        for k in range(12):
            ang = k * math.pi / 6 + len(a[0]) * .1
            pygame.draw.line(surf, mix((4, 12, 18), rc, .24),
                             (cx + math.cos(ang) * 48, cy + math.sin(ang) * 48),
                             (cx + math.cos(ang) * 56, cy + math.sin(ang) * 56), 1)
        dia = [(cx, cy - 14), (cx + 14, cy), (cx, cy + 14), (cx - 14, cy)]
        pygame.draw.polygon(surf, rc, dia, 1)
        pygame.draw.circle(surf, rc, (cx, cy), 3)

        draw_text(surf, a[1], fit_size(a[1], 25, rect.width - 40, True), COL['ink'],
                  (rect.centerx, rect.top + 172), align='center', bold=True)
        yy = rect.top + 212
        for line in wrap(a[2], 15, rect.width - 56):
            draw_text(surf, line, 15, COL['dim'], (rect.centerx, yy), align='center')
            yy += 25
        pygame.draw.line(surf, mix((4, 12, 18), rc, .34), (rect.left + 30, rect.top + 296),
                         (rect.right - 30, rect.top + 296))
        fy = rect.top + 308
        if pact:
            fl = (a[5].get('flavor_en') or PACT_FLAVOR_EN.get(a[0], 'A pact written in the corridor\'s own hand.')) if META.get('lang', 1) else a[5].get('flavor', '')
        else:
            fl = tr(FLAVOR.get(a[0], ''))
        if not fl and META.get('lang', 1):
            fl = {'c': 'A common fragment, still humming with the corridor.',
                  'r': 'The corridor remembers this shape.',
                  'l': 'A forbidden echo, warm to the touch.'}[a[3]]
        for line in wrap(fl, 11, rect.width - 60):
            draw_text(surf, line, 11, mix(COL['dimmer'], rc, .35), (rect.centerx, fy), align='center')
            fy += 18
        pygame.draw.line(surf, mix((4, 12, 18), rc, .3), (rect.left + 22, rect.bottom - 58),
                         (rect.right - 22, rect.bottom - 58))
        if pact:
            lab = L('本局已签 %d 条' % len(G.run.pacts), 'PACKED %d THIS RUN' % len(G.run.pacts))
        else:
            n = G.run.aug_count(a[0])
            lab = '已选 %d / %d' % (n, a[6])
        draw_text(surf, lab, 11, COL['dimmer'], (rect.left + 22, rect.bottom - 40))
        pygame.draw.rect(surf, mix((4, 12, 18), rc, .5), (rect.right - 44, rect.bottom - 44, 26, 26), 1)
        draw_text(surf, str(i + 1), 14, rc, (rect.right - 31, rect.bottom - 41), align='center', bold=True)

    pygame.draw.rect(surf, (3, 10, 14), (W / 2 - 190, 646, 380, 30))
    pygame.draw.rect(surf, (18, 34, 40), (W / 2 - 190, 646, 380, 30), 1)
    draw_text(surf, L('按 1 / 2 / 3 签订契约', 'PRESS 1 / 2 / 3 TO SIGN')
              if pact else '按 1 / 2 / 3 或点击选择', 11, COL['dimmer'], (W / 2, 656), align='center')


# ---------------------------------------------------------------- 暂停 / 结算
def draw_pause(surf):
    surf.blit(DIM, (0, 0))
    draw_text(surf, '回声中断', 40, COL['ink'], (W / 2, 232), align='center', bold=True)
    draw_text(surf, 'SONAR PAUSED  ·  %s  ·  %s  ·  第 %d 层 第 %d 波' % (
        G.run.ship['name'], G.run.mode_name, G.run.layer, G.run.wave), 11, COL['dimmer'],
              (W / 2, 288), align='center')
    draw_text(surf, '回廊事件 · %s    %s    SEED %06X' %
              (G.run.mut.get('name', '—'), G.run.mut.get('desc', ''), G.run.seed),
              11, mix(COL['bg0'], COL['gold'], .8), (W / 2, 312), align='center')
    draw_text(surf, '本层区域 · %s    %s' % (G.run.lmod['name'], G.run.lmod['desc']),
              11, mix(COL['bg0'], COL['aqua'], .75), (W / 2, 332), align='center')

    if G.run.augs:
        items = []
        for aid, n in G.run.augs.items():
            nm = AUG_BY_ID.get(aid, (aid, aid))[1]
            items.append('%s ×%d' % (nm, n) if n > 1 else nm)
        yy = 360
        for line in wrap('增幅  ' + '  ·  '.join(items), 12, 860)[:4]:
            draw_text(surf, line, 12, COL['dim'], (W / 2, yy), align='center')
            yy += 22

    draw_button(surf, rect_of('resume'), '继续下潜', 'aqua', 13)
    save_lab = L('保存进度', 'SAVE')
    if G.save_slot is not None and int(G.save_slot) >= 0:
        save_lab = L('保存 · 槽 %02d' % (int(G.save_slot) + 1), 'SAVE · SLOT %02d' % (int(G.save_slot) + 1))
    draw_button(surf, rect_of('savegame'), save_lab, 'gold', 13)
    draw_button(surf, rect_of('saveexit'), L('保存并退出', 'SAVE & EXIT'), 'steel', 13)
    draw_button(surf, rect_of('quit'), L('放弃本次下潜', 'ABANDON DIVE'), 'steel', 13)
    draw_text(surf, '鼠标瞄准  ·  T 切换自动索敌  ·  空格 / 手柄 A / RT 释放技能', 11,
              mix(COL['bg0'], COL['aqua'], .75), (W / 2, 616), align='center')
    draw_text(surf, L('ESC 继续  ·  S 保存  ·  手柄 B / Start 继续',
                     'ESC resume  ·  S save  ·  Pad B / Start resume'), 11, COL['dimmer'],
              (W / 2, 642), align='center')
    for act, label in (('settings', '设置'), ('codex', '档案'), ('help', '说明')):
        r = rect_of(act)
        if r:
            draw_button(surf, r, label, 'gold' if act == 'settings' else 'steel', 12)


def fmt_time(t):
    m = int(t // 60)
    s = int(t % 60)
    return '%02d:%02d' % (m, s)


def rank_of(score):
    if score >= 120000:
        return 'S', 'gold'
    if score >= 60000:
        return 'A', 'aqua'
    if score >= 25000:
        return 'B', 'green'
    return 'C', 'steel'


def draw_stats(surf, y):
    run = G.run
    vals = [
        ('层数', '%d' % run.layer),
        ('得分', '{:,}'.format(run.score)),
        ('击杀', '%d' % run.kills),
        ('连击', '×%d' % G.combo_best),
        ('用时', fmt_time(run.time)),
        ('增幅', '%d' % run.cards_taken),
    ]
    if run.pacts:
        vals.append(('契约', '%d' % len(run.pacts)))
    bw = 132
    if len(vals) > 6:
        bw = 112
    total = bw * len(vals)
    x = W / 2 - total / 2
    for i, (k, v) in enumerate(vals):
        r = pygame.Rect(int(x + i * bw), y, bw - 6, 76)
        pygame.draw.rect(surf, (5, 14, 20), r)
        pygame.draw.rect(surf, (18, 34, 40), r, 1)
        draw_text(surf, k, 9, COL['dimmer'], (r.centerx, r.top + 16), align='center')
        draw_text(surf, v, fit_size(v, 19, r.width - 10, True), COL['ink'],
                  (r.centerx, r.top + 34), align='center', bold=True)


def draw_settings(surf):
    draw_bg(surf, 0)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((2, 7, 11, 150))
    surf.blit(veil, (0, 0))
    draw_text(surf, L('系统设置', 'SYSTEM SETTINGS'), 40, COL['ink'], (56, 40), bold=True)
    draw_text(surf, L('SETTINGS  ·  所有选项即时保存', 'SETTINGS  ·  everything is saved instantly'),
              11, COL['dimmer'], (56, 92))
    panel = pygame.Rect(56, 120, W - 112, H - 232)
    draw_panel(surf, panel, 'steel', (5, 14, 20))

    rows = [
        (L('主音量', 'Master Volume'), L('整体音效与程序化背景音乐', 'SFX and procedural ambience')),
        (L('屏幕震动', 'Screen Shake'), L('受击、爆炸和 BOSS 技能的画面震动', 'Camera shake on hits, blasts and boss skills')),
        (L('闪光强度', 'Flash Intensity'), L('爆炸与技能命中的全屏白闪', 'Full-screen flashes on blasts and skill hits')),
        (L('显示模式', 'Display Mode'), L('窗口 / 全屏（F11 也可切换）', 'Windowed / fullscreen (F11 also works)')),
        (L('默认瞄准', 'Default Aim'), L('新一局开始时的瞄准方式', 'Aim mode at the start of a run')),
        (L('语言', 'Language'), L('界面与档案的显示语言', 'Language used by menus and archives')),
        (L('语音播报', 'Voice Lines'), L('关键事件的战术播报', 'Tactical radio lines for key events')),
        (L('手柄', 'Controller'), L('左摇杆移动 · 右摇杆瞄准 · A / RT 技能', 'Left stick move · right stick aim · A / RT skill')),
    ]
    for i, (lab, desc) in enumerate(rows):
        cy = 164 + i * 50
        if G.set_sel == i:
            pygame.draw.rect(surf, mix(COL['bg1'], COL['aqua'], .10),
                             pygame.Rect(92, cy - 22, W - 286, 44))
            pygame.draw.line(surf, COL['aqua'], (92, cy - 22), (92, cy + 22))
        h1 = font(16, True).get_height()
        top = cy - h1 // 2
        draw_text(surf, lab, 16, COL['ink'], (100, top), bold=True)
        draw_text(surf, desc, 10, COL['dimmer'], (100, top + h1 + 1))
        if i < len(rows) - 1:
            pygame.draw.line(surf, mix(COL['bg1'], COL['steel'], .35),
                             (100, cy + 27), (W - 100, cy + 27))

    # 音量：数值、滑条、按钮都在同一行中线上
    cy = 164
    draw_button(surf, rect_of('setvol-'), '−', 'steel', 16)
    draw_button(surf, rect_of('setvol+'), '＋', 'aqua', 16)
    v = int(META.get('vol', .7) * 100)
    bar = pygame.Rect(W - 284, cy - 9, 142, 18)
    pygame.draw.rect(surf, (3, 10, 15), bar)
    pygame.draw.rect(surf, mix(COL['bg1'], COL['aqua'], .4), bar, 1)
    pygame.draw.rect(surf, COL['aqua'], pygame.Rect(bar.x, bar.y, int(bar.w * v / 100), bar.h))
    vh = font(12, True).get_height()
    draw_text(surf, '%d%%' % v, 12, COL['ink'], (W - 396, cy - vh // 2), bold=True)

    vals = {
        'setshake': (META.get('shake', 1), L('开启', 'ON'), L('关闭', 'OFF')),
        'setflash': (META.get('flash', 1), L('开启', 'ON'), L('关闭', 'OFF')),
        'setfull': (META.get('fullscreen', 0), L('全屏', 'Fullscreen'), L('窗口', 'Windowed')),
        'setaim': (META.get('aim', 0), L('自动索敌', 'Auto-aim'), L('鼠标瞄准', 'Mouse')),
        'setvoice': (META.get('voice', 1), L('开启', 'ON'), L('关闭', 'OFF')),
    }
    for act, (on, yes, no) in vals.items():
        draw_button(surf, rect_of(act), yes if on else no,
                    'gold' if on else 'steel', 12, filled=bool(on))
    lang_label = 'English' if META.get('lang', 0) else '中文'
    draw_button(surf, rect_of('setlang'), lang_label, 'aqua', 12, filled=bool(META.get('lang', 0)))

    joy = G.joy_name or L('未检测到手柄', 'No controller detected')
    draw_text(surf, joy, 10, COL['aqua'] if G.joy else COL['dimmer'],
              (W - 70, 536), align='right')
    draw_button(surf, rect_of('setjoy'), L('重新检测', 'Detect'), 'steel', 12)
    draw_text(surf, L('提示：手柄热插拔后也可以在这里重新检测。', 'Tip: hot-plug a controller, then detect it here.'),
              10, COL['dimmer'], (100, 566))
    draw_text(surf, L('F11 全屏  ·  M 静音  ·  ESC 返回', 'F11 fullscreen  ·  M mute  ·  ESC back'),
              11, COL['dimmer'], (W / 2, H - 132), align='center')
    draw_button(surf, rect_of('setback'), L('返回', 'Back'), 'aqua', 14)


def draw_lab(surf):
    draw_bg(surf, 0)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((2, 7, 11, 150))
    surf.blit(veil, (0, 0))
    draw_text(surf, L('回声工坊', 'ECHO WORKSHOP'), 40, COL['ink'], (56, 34), bold=True)
    slot_txt = L('存档 %02d' % (int(G.save_slot) + 1), 'SAVE %02d' % (int(G.save_slot) + 1)) if G.save_slot is not None and int(G.save_slot) >= 0 else L('未选择存档', 'NO SAVE')
    draw_text(surf, L('PERMANENT UPGRADES  ·  %s  ·  用本存档的回声结晶升级' % slot_txt,
                     'PERMANENT UPGRADES  ·  %s  ·  spend this save\'s shards' % slot_txt),
              11, COL['dimmer'], (56, 86))
    draw_text(surf, L('持有 %d 枚回声结晶' % profile_shards(),
                     '%d ECHO SHARDS' % profile_shards()), 15,
              COL['gold'], (W - 56, 46), align='right', bold=True)

    panel = pygame.Rect(56, 112, W - 112, H - 244)
    draw_panel(surf, panel, 'gold', (5, 14, 20))
    for i, u in enumerate(UPGRADES):
        r = G.lab_rects[i]
        sel = (G.lab_sel == i)
        hover = r.collidepoint(G.pointer)
        lvl = upg_level(u['id'])
        cost = upg_cost(u)
        if sel:
            pygame.draw.rect(surf, mix(COL['bg1'], COL['gold'], .12), r)
            pygame.draw.line(surf, COL['gold'], (r.x, r.y), (r.x, r.bottom))
        pygame.draw.rect(surf, COL['gold'] if sel else mix(COL['bg1'], COL['steel'], .5),
                         r, 1)
        nm = L(u['name'], u['en'])
        ds = L(u['desc'], u['desc_en'])
        ns = fit_size(nm, 15, r.width - 250, True)
        draw_text(surf, nm, ns, COL['ink'] if sel else COL['dim'],
                  (r.x + 14, r.y + 7), bold=True)
        ds_size = fit_size(ds, 10, r.width - 250, False)
        draw_text(surf, ds, ds_size, COL['dimmer'], (r.x + 14, r.y + 27))
        draw_text(surf, 'LV %d / %d' % (lvl, u['max']), 11,
                  COL['gold'] if lvl >= u['max'] else COL['dim'],
                  (r.right - 112, r.y + 9), align='right', bold=(lvl >= u['max']))
        if cost is None:
            draw_text(surf, L('已满级', 'MAXED'), 10, COL['gold'], (r.right - 14, r.y + 9),
                      align='right')
        else:
            draw_text(surf, L('%d 结晶' % cost, '%d SHARDS' % cost), 10, COL['gold'],
                      (r.right - 14, r.y + 9), align='right')
        # 等级刻度：用方块而不是小圆点，避免中英文字体差异
        px = r.right - 212
        for k in range(u['max']):
            col = COL['gold'] if k < lvl else mix(COL['bg1'], COL['steel'], .55)
            pygame.draw.rect(surf, col, pygame.Rect(px + k * 16, r.y + 27, 10, 10))
    u = UPGRADES[G.lab_sel]
    lvl = upg_level(u['id'])
    cost = upg_cost(u)
    if cost is None:
        buy_label = L('已满级', 'MAXED')
    else:
        buy_label = L('升级 · %d 结晶' % cost, 'UPGRADE · %d SHARDS' % cost)
    draw_button(surf, G.rects[-2][1], buy_label,
                'gold' if (cost is not None and profile_shards() >= cost) else 'steel', 13)
    back_lab = L('返回存档', 'BACK TO SAVE') if G.menu_back == 'hub' else L('返回', 'BACK')
    draw_button(surf, G.rects[-1][1], back_lab, 'steel', 13)
    draw_text(surf, L('工坊升级只属于当前存档；换槽位不会带走结晶和等级。',
                     'Workshop levels and shards belong to this save slot only.'),
              10, COL['dimmer'], (W / 2, 716), align='center')


def draw_help(surf):
    draw_bg(surf, 0)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((2, 7, 11, 135))
    surf.blit(veil, (0, 0))
    draw_text(surf, '操作手册', 40, COL['ink'], (56, 36), bold=True)
    draw_text(surf, 'FIELD MANUAL  ·  第一次下潜前看一遍就够', 11, COL['dimmer'], (56, 88))
    panel = pygame.Rect(56, 118, W - 112, H - 222)
    draw_panel(surf, panel, 'steel', (5, 14, 20))

    left = 92
    right = 656
    draw_text(surf, '基础操作', 15, COL['aqua'], (left, 146), bold=True)
    basics = [
        ('WASD / 左摇杆', '移动；Shift / LB 减速，便于穿弹。'),
        ('鼠标 / 右摇杆', '决定船头方向，主炮与光束跟随船头。'),
        ('自动开火', '主炮持续射击，不需要按住鼠标。'),
        ('空格 / A / RT', '释放飞船技能。'),
        ('T / 手柄 Y', '切换鼠标瞄准与自动索敌。'),
        ('ESC / Start', '暂停；暂停里可看档案、设置和说明。'),
        (L('存档页 → 工坊', 'SAVE HUB → WORKSHOP'),
         L('工坊与结晶跟随存档；在存档总览页打开工坊。',
           'Workshop and shards are per-save; open them from the save hub.')),
        ('M / F11', '静音 / 切换全屏。'),
    ]
    yy = 180
    for key, desc in basics:
        draw_text(surf, key, 11, mix(COL['bg0'], COL['gold'], .9), (left, yy), bold=True)
        draw_text(surf, desc, 11, COL['dim'], (left + 154, yy))
        yy += 34

    draw_text(surf, '局内成长', 15, COL['gold'], (right, 146), bold=True)
    growth = [
        ('击杀与拾取', '敌机掉落回声，靠近自动吸收。'),
        ('三选一增幅', '每波结束选择一张卡，构筑本局。'),
        ('BOSS 双绝技', '第二阶段解锁第二绝技，第三阶段连携。'),
        ('护盾', '优先吸收伤害；护盾清空后才扣艇体。'),
        ('危险感知', '低血量时画面边缘变红，别硬吃弹。'),
    ]
    yy = 180
    for key, desc in growth:
        draw_text(surf, key, 11, mix(COL['bg0'], COL['gold'], .9), (right, yy), bold=True)
        draw_text(surf, desc, 11, COL['dim'], (right + 116, yy))
        yy += 35

    draw_text(surf, '六种模式', 15, COL['violet'], (left, 438), bold=True)
    modes = [('远航', '28 层完整回廊，标准流程。'),
             ('无尽', '越过 28 层后循环主题，直到静默。'),
             ('急行', '12 层、每层 3 波，高压速通。'),
             ('猎王', '12 层，每层直接进 BOSS 战。'),
             ('每日', '每日固定种子，和大家跑同一条回廊。'),
             ('契约', '每层 BOSS 后三选一，收益与代价同时生效。')]
    yy = 468
    for key, desc in modes:
        draw_text(surf, key, 11, COL['ink'], (left, yy), bold=True)
        draw_text(surf, desc, 11, COL['dim'], (left + 54, yy))
        yy += 24

    draw_text(surf, '设置与发行版', 15, COL['coral'], (right, 438), bold=True)
    draw_text(surf, '主音量、震动、闪光、全屏、默认瞄准都可调；', 11, COL['dim'], (right, 468))
    draw_text(surf, '设置即时写入本地存档，不会影响已有记录。', 11, COL['dim'], (right, 490))
    joy = ('已连接：' + G.joy_name) if G.joy else '未连接手柄（支持 Xbox / DS4 标准映射）'
    draw_text(surf, joy, 11, COL['aqua'] if G.joy else COL['dimmer'], (right, 520))
    draw_text(surf, '手柄：左摇杆移动 · 右摇杆瞄准 · A / RT 技能 · Y 自动索敌 · Start 暂停。',
              10, COL['dimmer'], (right, 548))
    draw_text(surf, '版本 v%s  ·  桌面发行候选版  ·  ESC / B 返回' % VERSION,
              10, COL['dimmer'], (W / 2, H - 132), align='center')
    draw_button(surf, rect_of('helpback'), '返回', 'aqua', 14)


ENEMY_NAMES = {
    'drifter': '漂移体', 'lantern': '灯笼', 'hunter': '猎手', 'turret': '炮塔',
    'spark': '火花', 'marc': '标记体', 'splitter': '分裂体', 'orbiter': '绕行体',
    'charger': '冲锋体', 'weaver': '织网者', 'bulwark': '壁垒', 'spinner': '旋刃',
    'bomber': '爆破体', 'sniper': '狙击体', 'dart': '飞镖', 'spawner': '巢母',
    'laser': '激光体', 'orb': '球体', 'sweeper': '清扫者', 'warden': '守卫',
    'siphoner': '虹吸体', 'spear': '标枪', 'miner': '雷巢', 'titan': '巨像',
    'drake': '龙骑', 'mortar': '迫击', 'shade': '幽影', 'wisp': '光蛾',
    'juggernaut': '破城', 'webber': '织网', 'prism': '棱镜', 'hive': '蜂巢',
    'lancer': '长枪', 'cryo': '霜冻', 'torch': '炬火', 'voidling': '虚空幼体',
}

ENEMY_EN = {
    'drifter': 'DRIFTER', 'lantern': 'LANTERN', 'hunter': 'HUNTER', 'turret': 'TURRET',
    'spark': 'SPARK', 'marc': 'MARC', 'splitter': 'SPLITTER', 'orbiter': 'ORBITER',
    'charger': 'CHARGER', 'weaver': 'WEAVER', 'bulwark': 'BULWARK', 'spinner': 'SPINNER',
    'bomber': 'BOMBER', 'sniper': 'SNIPER', 'dart': 'DART', 'spawner': 'SPAWNER',
    'laser': 'LASER', 'orb': 'ORB', 'sweeper': 'SWEEPER', 'warden': 'WARDEN',
    'siphoner': 'SIPHONER', 'spear': 'SPEAR', 'miner': 'MINER', 'titan': 'TITAN',
    'drake': 'DRAKE', 'mortar': 'MORTAR', 'shade': 'SHADE', 'wisp': 'WISP',
    'juggernaut': 'JUGGERNAUT', 'webber': 'WEBBER', 'prism': 'PRISM', 'hive': 'HIVE',
    'lancer': 'LANCER', 'cryo': 'CRYO', 'torch': 'TORCH', 'voidling': 'VOIDLING',
}


def codex_items(tab):
    if tab == 0:
        return SHIPS, 12
    if tab == 1:
        return BOSSCFG, 8
    if tab == 2:
        return AUGS, 12
    return list(EKIND.items()), 12


def codex_page_count(tab):
    items, per = codex_items(tab)
    return max(1, (len(items) + per - 1) // per)


def draw_codex(surf):
    draw_bg(surf, 0)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((2, 7, 11, 150))
    surf.blit(veil, (0, 0))
    draw_text(surf, '深渊档案', 40, COL['ink'], (56, 36), bold=True)
    draw_text(surf, 'ARCHIVE  ·  数据来自当前版本，随内容更新自动扩充', 11, COL['dimmer'], (56, 88))

    tabs = ('飞船 %d' % len(SHIPS), 'BOSS %d' % len(BOSSCFG),
            '增幅 %d' % len(AUGS), '敌机 %d' % len(EKIND))
    for i, nm in enumerate(tabs):
        r = rect_of('codex%d' % i)
        if not r:
            continue
        sel = (G.codex_tab == i)
        c = COL['gold'] if sel else COL['steel']
        if sel:
            pygame.draw.rect(surf, mix(COL['bg1'], c, .18), r)
        pygame.draw.rect(surf, c if sel else mix(COL['bg1'], c, .5), r, 2 if sel else 1)
        draw_text(surf, nm, 12, COL['ink'] if sel else COL['dim'],
                  (r.centerx, r.centery), align='center', bold=sel)

    tab = G.codex_tab
    items, per = codex_items(tab)
    pages = codex_page_count(tab)
    G.codex_page = min(max(0, G.codex_page), pages - 1)
    start = G.codex_page * per
    chunk = items[start:start + per]
    content = pygame.Rect(56, 154, W - 112, H - 304)
    draw_panel(surf, content, 'steel', (5, 14, 20))

    if tab == 0:
        for j, ship in enumerate(chunk):
            col, row = j % 2, j // 2
            r = pygame.Rect(76 + col * 570, 160 + row * 76, 550, 64)
            draw_panel(surf, r, ship['col'], (6, 16, 22))
            draw_text(surf, ship['name'], 17, COL['ink'], (r.x + 14, r.y + 7), bold=True)
            draw_text(surf, ship['role'] + ' · ' + ship['skill'], 11, COL[ship['col']],
                      (r.x + 120, r.y + 9))
            draw_text(surf, '艇体 %d   ·   航速 %d   ·   伤害 %.2f   ·   CD %.1fs' % (
                ship['hp'], ship['speed'], ship['dmg'], ship['cd']), 10, COL['dim'],
                      (r.x + 14, r.y + 30))
            draw_text(surf, '解锁：%s' % ('初始' if ship['unlock'] == 0 else '抵达第 %d 层' % ship['unlock']),
                      9, COL['dimmer'], (r.right - 14, r.y + 31), align='right')
            draw_text(surf, ship['desc'], 10, COL['dim'], (r.x + 14, r.y + 47))
    elif tab == 1:
        for j, boss in enumerate(chunk):
            i = start + j
            col, row = j % 2, j // 2
            r = pygame.Rect(76 + col * 570, 160 + row * 108, 550, 96)
            draw_panel(surf, r, boss['col'], (6, 16, 22))
            draw_text(surf, boss['name'], 17, COL['ink'], (r.x + 14, r.y + 7), bold=True)
            if META.get('lang', 0) == 0:
                nw = text_w(boss['name'], 17, True) + 12
                if r.x + 14 + nw + text_w(boss['en'], 9) < r.right - 14:
                    draw_text(surf, boss['en'], 9, COL['dimmer'], (r.x + 14 + nw, r.y + 11))
            draw_text(surf, 'HP %d   ·   半径 %d   ·   第 %d 层王座' % (boss['hp'], boss['r'], i + 1),
                      10, COL['dim'], (r.x + 14, r.y + 29))
            draw_text(surf, '绝技一 · %s' % BOSS_SIG_NAMES[i], 10,
                      mix(COL['bg0'], COL['gold'], .9), (r.x + 14, r.y + 46))
            draw_text(surf, '绝技二 · %s' % BOSS_SIG2_NAMES[i], 10,
                      mix(COL['bg0'], COL['aqua'], .9), (r.x + 14, r.y + 64))
            draw_text(surf, '第二阶段解锁第二绝技，第三阶段双绝技连携', 9, COL['dimmer'],
                      (r.x + 14, r.y + 82))
    elif tab == 2:
        for j, aug in enumerate(chunk):
            col, row = j % 3, j // 3
            r = pygame.Rect(76 + col * 380, 160 + row * 110, 360, 96)
            draw_panel(surf, r, RARITY_COL[aug[3]], (6, 16, 22))
            draw_text(surf, aug[1], 16, COL['ink'], (r.x + 12, r.y + 7), bold=True)
            draw_text(surf, RARITY_NAME[aug[3]], 9, COL[RARITY_COL[aug[3]]],
                      (r.right - 12, r.y + 9), align='right')
            draw_text(surf, aug[2], 10, COL['dim'], (r.x + 12, r.y + 32))
            draw_text(surf, '可叠加上限 %d' % aug[6], 9, COL['dimmer'], (r.x + 12, r.y + 76))
    else:
        for j, (eid, d) in enumerate(chunk):
            col, row = j % 2, j // 2
            r = pygame.Rect(76 + col * 570, 160 + row * 72, 550, 62)
            draw_panel(surf, r, d.get('col', 'steel'), (6, 16, 22))
            draw_text(surf, ENEMY_NAMES.get(eid, eid), 16, COL['ink'],
                      (r.x + 14, r.y + 7), bold=True)
            draw_text(surf, eid, 9, COL['dimmer'], (r.x + 116, r.y + 10))
            draw_text(surf, '基础血量 %.1f  ·  半径 %d  ·  击破分 %d' % (
                d['hp'], d['r'], d['score']), 10, COL['dim'], (r.x + 14, r.y + 30))
            draw_text(surf, '高危度 %.2f' % d.get('cr', 1), 9, COL['dimmer'],
                      (r.right - 14, r.y + 32), align='right')
    draw_text(surf, '第 %d / %d 页' % (G.codex_page + 1, pages), 12,
              COL['dimmer'], (W / 2, H - 70), align='center')
    draw_button(surf, rect_of('codeprev'), '上一页', 'steel', 12)
    draw_button(surf, rect_of('codenext'), '下一页', 'aqua', 12)
    draw_button(surf, rect_of('codexback'), '返回', 'steel', 12)


def draw_dead(surf):
    surf.blit(DIM, (0, 0))
    draw_text(surf, L('静默', 'SILENCE'), 46, COL['ink'], (W / 2, 250), align='center', bold=True)
    draw_text(surf, 'SIGNAL LOST', 11, COL['dimmer'], (W / 2, 312), align='center')
    rk, rc = rank_of(G.run.score)
    draw_text(surf, rk, 54, COL[rc], (W - 92, 226), align='center', bold=True)
    draw_text(surf, 'RANK', 9, COL['dimmer'], (W - 92, 288), align='center')
    if G.run and G.run.shards_earned:
        draw_text(surf, L('+%d 结晶（本存档 %d）' % (G.run.shards_earned, profile_shards()),
                         '+%d SHARDS (%d IN SAVE)' % (G.run.shards_earned, profile_shards())),
                  10, COL['gold'], (W - 92, 307), align='center')
    draw_stats(surf, 356)
    df = DIFFS[G.diff]
    mr = best_record(G.run.mode, G.diff)
    mut_name = tr(G.run.mut.get('name', '—')) if META.get('lang') else G.run.mut.get('name', '—')
    mode_name = MODES[G.run.mode]['en'] if META.get('lang') else MODES[G.run.mode]['name']
    diff_name = df['en'] if META.get('lang') else df['name']
    draw_text(surf, L('%s · 难度 %s · 本局层域 %s    SEED %06X' % (
                        mode_name, diff_name, mut_name, G.run.seed),
                     '%s · %s · MUTATOR %s    SEED %06X' % (
                        mode_name, diff_name, mut_name, G.run.seed)),
              11, mix(COL['bg0'], COL['gold'], .7), (W / 2, 470), align='center')
    draw_button(surf, G.rects[0][1], L('再次进入', 'DIVE AGAIN'), 'aqua', 14)
    draw_button(surf, G.rects[1][1], L('更换飞船', 'CHANGE DIVER'), 'steel', 14)
    draw_text(surf, L('Enter 重开 · %s · %s 最深 第 %d 层 · 最高分 %s' % (
                        mode_name, diff_name, mr.get('layer', 0), '{:,}'.format(mr.get('score', 0))),
                     'Enter retry · %s · %s best stratum %d · best score %s' % (
                        mode_name, diff_name, mr.get('layer', 0), '{:,}'.format(mr.get('score', 0)))),
              11, COL['dimmer'], (W / 2, 596), align='center')


def draw_win(surf):
    surf.blit(DIM, (0, 0))
    head = '抵达回廊之底'
    en = 'THE END OF THE CORRIDOR'
    sub = '二十八层之后，回声终于安静下来。'
    sub_en = 'Past the twenty-eighth stratum, the echo finally falls silent.'
    mid = MODES[G.run.mode]['id'] if G.run else 'voyage'
    if mid == 'rush':
        head, en = '急行通关', 'RUSH CLEARED'
        sub, sub_en = '十二层高压航道，被你一路撞穿。', 'Twelve strata of pressure, torn straight through.'
    elif mid == 'hunt':
        head, en = '猎王归途', 'HUNT COMPLETE'
        sub, sub_en = '十二位王座，全部沉入回声。', 'Twelve thrones, all sunk into the echo.'
    elif mid == 'daily':
        head, en = '今日回声', 'DAILY CLEARED'
        sub, sub_en = '今天的回廊，被你先走完了。', "Today's corridor was cleared first by you."
    draw_text(surf, L(head, en), 44, COL['gold'], (W / 2, 240), align='center', bold=True)
    if not META.get('lang'):
        draw_text(surf, en, 11, COL['dimmer'], (W / 2, 300), align='center')
    draw_text(surf, L(sub, sub_en), 15, COL['dim'], (W / 2, 334), align='center')
    rk, rc = rank_of(G.run.score)
    draw_text(surf, rk, 54, COL[rc], (W - 92, 220), align='center', bold=True)
    draw_text(surf, 'RANK', 9, COL['dimmer'], (W - 92, 282), align='center')
    if G.run and G.run.shards_earned:
        total_sh = int((G.profile or {}).get('shards', 0)) if isinstance(G.profile, dict) else 0
        draw_text(surf, L('+%d 结晶（本存档共 %d）' % (G.run.shards_earned, total_sh),
                         '+%d SHARDS (%d IN SAVE)' % (G.run.shards_earned, total_sh)),
                  10, COL['gold'], (W - 92, 301), align='center')
    draw_stats(surf, 376)
    mut_name = tr(G.run.mut.get('name', '—')) if META.get('lang') else G.run.mut.get('name', '—')
    mode_name = MODES[G.run.mode]['en'] if META.get('lang') else MODES[G.run.mode]['name']
    diff_name = DIFFS[G.diff]['en'] if META.get('lang') else DIFFS[G.diff]['name']
    draw_text(surf, L('%s · 难度 %s · 本局层域 %s    SEED %06X' % (
                        mode_name, diff_name, mut_name, G.run.seed),
                     '%s · %s · MUTATOR %s    SEED %06X' % (
                        mode_name, diff_name, mut_name, G.run.seed)),
              11, mix(COL['bg0'], COL['gold'], .7), (W / 2, 488), align='center')
    draw_button(surf, G.rects[0][1], L('再来一趟', 'DIVE AGAIN'), 'gold', 14)
    draw_button(surf, G.rects[1][1], L('更换飞船', 'CHANGE DIVER'), 'steel', 14)


# ================================================================
#  事件
# ================================================================
def settings_selected_action():
    acts = ('setvol+', 'setshake', 'setflash', 'setfull', 'setaim', 'setlang', 'setvoice', 'setjoy')
    return acts[int(clamp(G.set_sel, 0, len(acts) - 1))]


def do_action(act):
    if act == 'newgame':
        G.slot_mode = 'new'
        G.confirm_slot = -1
        G.scene = 'slots'
        layout()
        AUD.play('pick', .45)
        return
    if act == 'continue':
        if not any(read_slot(i) for i in range(SLOT_COUNT)):
            toast(L('还没有可继续的存档', 'No save to continue'), 'gold', 1.8)
            AUD.play('pick', .35)
            return
        G.slot_mode = 'load'
        G.confirm_slot = -1
        G.scene = 'slots'
        layout()
        AUD.play('pick', .45)
        return
    if act == 'exitgame':
        G.quit_requested = True
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        return
    if act == 'savegame':
        save_checkpoint()
        return
    if act == 'saveexit':
        if not save_checkpoint(quiet=True):
            toast(L('保存失败，仍停留在暂停菜单', 'Save failed; staying in pause menu'), 'coral')
            return
        G.scene = 'title'
        G.menu_sel = 1
        G.run = None
        G.player = None
        G.save_slot = -1
        layout()
        AUD.play('pick', .45)
        return
    if act == 'intronext':
        advance_intro()
        return
    if act == 'introskip':
        finish_intro()
        return
    if act == 'slotback':
        G.confirm_slot = -1
        G.scene = 'title'
        G.menu_sel = 0
        layout()
        AUD.play('pick', .4)
        return
    if act.startswith('slot') and act[4:].isdigit():
        i = int(act[4:])
        if i < 0 or i >= SLOT_COUNT:
            return
        G.slot_sel = i
        d = read_slot(i)
        if G.slot_mode == 'load' and not d:
            toast(L('这个存档槽是空的', 'This slot is empty'), 'steel', 1.8)
            AUD.play('pick', .35)
            return
        open_slot(i)
        return
    if act == 'hubdive':
        d = read_slot(G.save_slot)
        if d and d.get('run_active'):
            if not load_slot(G.save_slot):
                toast(L('读取存档失败', 'Failed to load save'), 'coral', 2.0)
        else:
            G.scene = 'select'
            G.sel = 0
            G.ship_page = 0
            layout()
            AUD.play('pick', .45)
        return
    if act == 'hubnew':
        d = read_slot(G.save_slot)
        if d and d.get('run_active') and not G.hub_confirm_new:
            G.hub_confirm_new = True
            toast(L('当前存档有进行中的下潜，再次点击确认重开新局',
                   'This save has an active dive; click again to start a new run'), 'gold', 2.2)
            layout()
            AUD.play('pick', .35)
            return
        G.hub_confirm_new = False
        G.scene = 'select'
        G.sel = 0
        G.ship_page = 0
        layout()
        AUD.play('pick', .45)
        return
    if act == 'hublab':
        G.menu_back = 'hub'
        G.scene = 'lab'
        layout()
        AUD.play('pick', .4)
        return
    if act == 'hubshards':
        G.menu_back = 'hub'
        G.scene = 'shards'
        layout()
        AUD.play('pick', .4)
        return
    if act == 'shardslab':
        G.menu_back = 'hub'
        G.scene = 'lab'
        layout()
        AUD.play('pick', .4)
        return
    if act == 'hubdelete':
        if not G.hub_confirm_del:
            G.hub_confirm_del = True
            toast(L('再次点击确认删除这个存档（工坊与结晶一并清除）',
                   'Click again to delete this save (workshop and shards included)'), 'coral', 2.2)
            layout()
            AUD.play('pick', .35)
            return
        remove_slot(G.save_slot)
        G.save_slot = -1
        G.profile = None
        G.hub_confirm_del = False
        G.slot_mode = 'new' if not any(read_slot(i) for i in range(SLOT_COUNT)) else 'load'
        G.scene = 'slots'
        layout()
        AUD.play('low', .5) if 'low' in AUD.sounds else AUD.play('pick', .5)
        return
    if act == 'hubback':
        G.hub_confirm_new = False
        G.hub_confirm_del = False
        G.slot_mode = 'load'
        G.scene = 'slots'
        layout()
        AUD.play('pick', .4)
        return
    if act in ('settings', 'codex', 'help', 'lab'):
        G.menu_back = G.scene if G.scene in ('title', 'pause', 'hub') else 'title'
        G.scene = act
        if act == 'codex':
            G.codex_page = 0
            grant_ach('curator')
        elif act == 'help':
            grant_ach('sop')
        elif act == 'lab':
            layout()
            AUD.play('pick', .4)
            return
        layout()
        AUD.play('pick', .4)
        return
    if act in ('setback', 'helpback', 'codexback', 'labback', 'menuback', 'shardsback'):
        G.scene = G.menu_back if G.menu_back in ('title', 'pause', 'hub') else 'title'
        layout()
        AUD.play('pick', .4)
        return
    if act.startswith('lab') and act[3:].isdigit():
        G.lab_sel = min(len(UPGRADES) - 1, max(0, int(act[3:])))
        AUD.play('pick', .35)
        return
    if act == 'labbuy':
        if not isinstance(G.profile, dict):
            toast(L('请先从存档进入工坊', 'Enter a save before using the workshop'), 'coral')
            return
        u = UPGRADES[G.lab_sel]
        cost = upg_cost(u)
        if cost is None:
            toast(L('这项永久升级已经满级', 'This upgrade is already maxed'), 'gold')
            AUD.play('pick', .4)
            return
        if int(G.profile.get('shards', 0)) < cost:
            toast(L('回声结晶不足：需要 %d' % cost, 'Not enough shards: need %d' % cost), 'coral')
            AUD.play('low', .5) if 'low' in AUD.sounds else AUD.play('pick', .5)
            return
        G.profile['shards'] = int(G.profile.get('shards', 0)) - cost
        upg = G.profile.setdefault('upg', {})
        upg[u['id']] = upg.get(u['id'], 0) + 1
        G.profile['updated'] = _stamp()
        save_profile(G.save_slot, G.profile)
        grant_ach('workshop')
        if upg[u['id']] >= u['max']:
            grant_ach('workshop_max')
        if all(upg_level(x['id']) >= 1 for x in UPGRADES):
            grant_ach('lab_all')
        toast(L('%s 升级到 LV%d' % (u['name'], upg[u['id']]),
                '%s upgraded to LV%d' % (u['en'], upg[u['id']])), 'gold')
        AUD.play('buy', .8) if 'buy' in AUD.sounds else AUD.play('big', .6)
        return
    if act == 'setvol-' or act == 'setvol+':
        META['vol'] = clamp(META.get('vol', .7) + (-.05 if act == 'setvol-' else .05), 0, 1)
        AUD.set_master(META['vol'])
        grant_ach('calibrated')
        save_meta()
        AUD.play('pick', .5)
        return
    if act == 'setshake':
        META['shake'] = 0 if META.get('shake', 1) else 1
        G.shake_scale = 1.0 if META['shake'] else 0.0
        grant_ach('calibrated')
        save_meta()
        AUD.play('pick', .5)
        return
    if act == 'setflash':
        META['flash'] = 0 if META.get('flash', 1) else 1
        G.flash_scale = 1.0 if META['flash'] else 0.0
        grant_ach('calibrated')
        save_meta()
        AUD.play('pick', .5)
        return
    if act == 'setfull':
        apply_display(not META.get('fullscreen', 0))
        grant_ach('calibrated')
        save_meta()
        AUD.play('pick', .5)
        return
    if act == 'setaim':
        META['aim'] = 0 if META.get('aim', 0) else 1
        G.aim_mode = 'auto' if META['aim'] else 'mouse'
        grant_ach('calibrated')
        save_meta()
        AUD.play('pick', .5)
        return
    if act == 'setlang':
        META['lang'] = 0 if META.get('lang', 0) else 1
        grant_ach('polyglot')
        save_meta()
        AUD.play('pick', .5)
        return
    if act == 'setvoice':
        META['voice'] = 0 if META.get('voice', 1) else 1
        if META['voice']:
            grant_ach('voice_link')
        save_meta()
        AUD.play('pick', .5)
        return
    if act == 'setjoy':
        init_joystick()
        save_meta()
        AUD.play('pick', .5)
        return
    if act.startswith('codex') and act[5:].isdigit():
        G.codex_tab = int(act[5:])
        G.codex_page = 0
        if G.codex_tab == 1:
            grant_ach('boss_lore')
        elif G.codex_tab == 2:
            grant_ach('aug_lore')
        layout()
        AUD.play('pick', .4)
        return
    if act == 'codeprev':
        G.codex_page = max(0, G.codex_page - 1)
        AUD.play('pick', .4)
        return
    if act == 'codenext':
        G.codex_page = min(codex_page_count(G.codex_tab) - 1, G.codex_page + 1)
        AUD.play('pick', .4)
        return
    if act == 'start':
        G.slot_mode = 'new'
        G.confirm_slot = -1
        G.scene = 'slots'
        layout()
        return
    elif act.startswith('mode') and act[4:].isdigit():
        G.mode = int(act[4:])
        META['mode'] = G.mode
        save_meta()
        AUD.play('pick', .5)
        layout()
        return
    elif act.startswith('diff') and act[4:].isdigit():
        G.diff = int(act[4:])
        META['diff'] = G.diff
        save_meta()
        AUD.play('pick', .5)
        layout()
        return
    elif act.startswith('ship') and act[4:].isdigit():
        i = int(act[4:])
        if ship_unlocked(SHIPS[i]):
            G.sel = i
            AUD.play('pick', .5)
    elif act == 'shipprev':
        G.ship_page = max(0, G.ship_page - 1)
        G.sel = G.ship_page * SHIPS_PER_PAGE
        layout()
        AUD.play('pick', .4)
        return
    elif act == 'shipnext':
        G.ship_page = min((len(SHIPS) - 1) // SHIPS_PER_PAGE, G.ship_page + 1)
        G.sel = G.ship_page * SHIPS_PER_PAGE
        layout()
        AUD.play('pick', .4)
        return
    elif act == 'dive':
        slot = G.save_slot
        if slot is None or int(slot) < 0 or int(slot) >= SLOT_COUNT:
            slot = first_empty_slot()
            if slot < 0:
                toast(L('三个存档槽都已占用，请先选择一个槽覆盖', 'All slots are full; choose one to overwrite'), 'coral', 2.4)
                G.slot_mode = 'new'
                G.scene = 'slots'
                layout()
                return
        new_run(SHIPS[G.sel]['id'], slot=slot)
        return
    elif act == 'back':
        G.scene = 'hub' if G.save_slot is not None and int(G.save_slot) >= 0 else 'title'
        layout()
        return
    elif act.startswith('card'):
        choose_card(int(act[4:]))
        return
    elif act == 'resume':
        G.scene = 'play'
    elif act == 'quit':
        slot = G.save_slot
        if slot is not None and int(slot) >= 0:
            clear_slot(slot)
            G.profile = slot_profile(slot)
            G.run = None
            G.player = None
            G.hub_confirm_new = False
            G.scene = 'hub'
            layout()
        else:
            G.scene = 'title'
            G.menu_sel = 0
            layout()
    elif act == 'again':
        new_run(G.run.ship['id'], slot=(G.save_slot if G.save_slot is not None and int(G.save_slot) >= 0 else None))
        return
    elif act == 'ships':
        G.scene = 'select'
        G.sel = [s['id'] for s in SHIPS].index(G.run.ship['id']) if G.run else 0
        G.ship_page = G.sel // SHIPS_PER_PAGE
    layout()
    AUD.play('card', .4)


def menu_move(step):
    """键盘选择时跳过不可用的「继续游戏」，避免高亮落在禁用项上。"""
    for _ in range(6):
        G.menu_sel = (G.menu_sel + step) % 6
        if G.menu_sel != 1 or any(read_slot(i) for i in range(SLOT_COUNT)):
            return


def start_intro(slot):
    G.intro_slot = int(slot)
    G.intro_after = 'hub'
    G.intro_page = 0
    G.intro_t = 0
    G.scene = 'intro'
    layout()


def finish_intro():
    slot = G.intro_slot
    if slot is not None and 0 <= int(slot) < SLOT_COUNT:
        p = G.profile or slot_profile(slot)
        if not p:
            p = new_slot_profile()
        p['intro_seen'] = 1
        G.profile = p
        save_profile(int(slot), p)
    G.intro_slot = None
    G.scene = G.intro_after if G.intro_after in ('hub', 'title') else 'hub'
    if G.scene == 'hub':
        G.slot_sel = int(G.save_slot) if G.save_slot is not None and int(G.save_slot) >= 0 else 0
    layout()
    AUD.play('pick', .45)


def open_slot(i):
    """进入一个存档的专属总览页；新档第一次进入时先放序章。"""
    i = int(i)
    if i < 0 or i >= SLOT_COUNT:
        return False
    d = read_slot(i)
    if not d:
        p = new_slot_profile()
        d = {'ver': VERSION, 'empty': False, 'run_active': False,
             'profile': p, 'updated': _stamp()}
        write_slot(i, d)
    else:
        p = normalize_profile(d.get('profile'))
        d['profile'] = p
        write_slot(i, d)
    G.save_slot = i
    G.slot_sel = i
    G.profile = p
    G.run = None
    G.player = None
    G.hub_confirm_new = False
    G.hub_confirm_del = False
    if d.get('run_active'):
        G.mode = int(clamp(int(d.get('mode', META.get('mode', 0))), 0, len(MODES) - 1))
        G.diff = int(clamp(int(d.get('diff', META.get('diff', 0))), 0, len(DIFFS) - 1))
    if not p.get('intro_seen'):
        start_intro(i)
    else:
        G.scene = 'hub'
        layout()
    AUD.play('pick', .45)
    return True


def advance_intro():
    txt = intro_page_text(G.intro_page)
    if G.intro_t < len(txt) - 2:
        G.intro_t = len(txt)
        return
    if G.intro_page < len(INTRO_PAGES) - 1:
        G.intro_page += 1
        G.intro_t = 0
        AUD.play('pick', .45)
    else:
        finish_intro()


def toggle_mute():
    AUD.set_muted(not AUD.muted)
    toast('音效：关闭' if AUD.muted else '音效：开启', 'dim')


def handle_event(e):
    if e.type == pygame.QUIT:
        return False

    if e.type == pygame.JOYDEVICEADDED:
        if G.joy is None:
            init_joystick()
        return True
    if e.type == pygame.JOYDEVICEREMOVED:
        G.joy = None
        G.joy_name = ''
        return True
    if e.type == pygame.JOYHATMOTION:
        key = None
        hx, hy = e.value
        if hx < 0:
            key = pygame.K_LEFT
        elif hx > 0:
            key = pygame.K_RIGHT
        elif hy > 0:
            key = pygame.K_UP
        elif hy < 0:
            key = pygame.K_DOWN
        if key:
            return handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        return True
    if e.type == pygame.JOYBUTTONDOWN:
        b = e.button
        if G.scene == 'cards':
            key = {0: pygame.K_1, 2: pygame.K_2, 3: pygame.K_3, 1: pygame.K_ESCAPE}.get(b)
        elif G.scene == 'play':
            if b == 3:
                key = pygame.K_t
            elif b == 7:
                key = pygame.K_ESCAPE
            else:
                key = None
        else:
            if b == 0:
                key = pygame.K_RETURN
            elif b in (1, 6, 7):
                key = pygame.K_ESCAPE
            else:
                key = None
        if key:
            return handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        return True

    if e.type == pygame.KEYDOWN:
        if e.key in (pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_LEFT,
                     pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_LSHIFT, pygame.K_RSHIFT):
            G.held.add(e.key)
        if e.key == pygame.K_m:
            toggle_mute()
            return True
        if e.key == pygame.K_F11:
            if not HEADLESS:
                apply_display(not META.get('fullscreen', 0))
                save_meta()
            return True
        if G.scene == 'title':
            if e.key in (pygame.K_UP, pygame.K_w):
                menu_move(-1)
                AUD.play('pick', .3)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                menu_move(1)
                AUD.play('pick', .3)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                acts = ('newgame', 'continue', 'codex', 'settings', 'help', 'exitgame')
                do_action(acts[int(clamp(G.menu_sel, 0, 5))])
            elif e.key == pygame.K_ESCAPE:
                do_action('exitgame')
            elif e.key == pygame.K_o:
                do_action('settings')
            elif e.key == pygame.K_c:
                do_action('codex')
            elif e.key == pygame.K_h:
                do_action('help')
        elif G.scene == 'intro':
            if e.key == pygame.K_ESCAPE:
                do_action('introskip')
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                advance_intro()
        elif G.scene == 'slots':
            if e.key == pygame.K_ESCAPE:
                do_action('slotback')
            elif e.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                G.slot_sel = (G.slot_sel - 1) % SLOT_COUNT
                G.confirm_slot = -1
                AUD.play('pick', .3)
            elif e.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                G.slot_sel = (G.slot_sel + 1) % SLOT_COUNT
                G.confirm_slot = -1
                AUD.play('pick', .3)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                do_action('slot%d' % G.slot_sel)
        elif G.scene == 'hub':
            if e.key == pygame.K_ESCAPE:
                do_action('hubback')
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                do_action('hubdive')
            elif e.key == pygame.K_w:
                do_action('hublab')
            elif e.key == pygame.K_e:
                do_action('hubshards')
            elif e.key == pygame.K_DELETE:
                do_action('hubdelete')
        elif G.scene == 'shards':
            if e.key == pygame.K_ESCAPE:
                do_action('shardsback')
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                do_action('shardsback')
        elif G.scene == 'select':
            if e.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w, pygame.K_PAGEUP):
                step = -SHIPS_PER_PAGE if e.key == pygame.K_PAGEUP else -1
                G.sel = (G.sel + step) % len(SHIPS)
                while not ship_unlocked(SHIPS[G.sel]):
                    G.sel = (G.sel + step) % len(SHIPS)
                G.ship_page = G.sel // SHIPS_PER_PAGE
                layout()
                AUD.play('pick', .4)
            elif e.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s, pygame.K_PAGEDOWN):
                step = SHIPS_PER_PAGE if e.key == pygame.K_PAGEDOWN else 1
                G.sel = (G.sel + step) % len(SHIPS)
                while not ship_unlocked(SHIPS[G.sel]):
                    G.sel = (G.sel + step) % len(SHIPS)
                G.ship_page = G.sel // SHIPS_PER_PAGE
                layout()
                AUD.play('pick', .4)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                slot = G.save_slot
                if slot is None or int(slot) < 0 or int(slot) >= SLOT_COUNT:
                    slot = first_empty_slot()
                    if slot < 0:
                        toast(L('三个存档槽都已占用', 'All slots are full'), 'coral', 2.0)
                        G.slot_mode = 'new'
                        G.scene = 'slots'
                        layout()
                        return True
                new_run(SHIPS[G.sel]['id'], slot=slot)
            elif e.key == pygame.K_TAB:
                G.diff = (G.diff + 1) % len(DIFFS)
                META['diff'] = G.diff
                save_meta()
                AUD.play('pick', .4)
            elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6):
                G.mode = e.key - pygame.K_1
                if G.mode >= len(MODES):
                    G.mode = len(MODES) - 1
                META['mode'] = G.mode
                save_meta()
                AUD.play('pick', .5)
                layout()
        elif G.scene == 'play':
            if e.key == pygame.K_ESCAPE:
                G.scene = 'pause'
                layout()
            elif e.key == pygame.K_t:
                G.aim_mode = 'auto' if G.aim_mode == 'mouse' else 'mouse'
                if G.aim_mode == 'auto':
                    toast('瞄准 · 自动索敌', 'gold')
                else:
                    toast('瞄准 · 鼠标跟随', 'aqua')
                AUD.play('pick', .4)
        elif G.scene == 'pause':
            if e.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                G.scene = 'play'
                layout()
            elif e.key == pygame.K_s:
                do_action('savegame')
            elif e.key in (pygame.K_o, pygame.K_F1):
                do_action('settings')
            elif e.key == pygame.K_c:
                do_action('codex')
            elif e.key == pygame.K_h:
                do_action('help')
            elif e.key == pygame.K_u:
                do_action('lab')
        elif G.scene == 'lab':
            if e.key in (pygame.K_ESCAPE, pygame.K_u):
                do_action('labback')
            elif e.key in (pygame.K_UP, pygame.K_w):
                G.lab_sel = max(0, G.lab_sel - 1)
                AUD.play('pick', .3)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                G.lab_sel = min(len(UPGRADES) - 1, G.lab_sel + 1)
                AUD.play('pick', .3)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                do_action('labbuy')
        elif G.scene == 'settings':
            if e.key == pygame.K_ESCAPE:
                do_action('setback')
            elif e.key in (pygame.K_UP, pygame.K_w):
                G.set_sel = max(0, G.set_sel - 1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                G.set_sel = min(7, G.set_sel + 1)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                do_action(settings_selected_action())
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                do_action('setvol-')
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                do_action('setvol+')
        elif G.scene == 'help':
            if e.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                do_action('helpback')
        elif G.scene == 'codex':
            if e.key == pygame.K_ESCAPE:
                do_action('codexback')
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                do_action('codenext')
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                G.codex_tab = (G.codex_tab - 1) % 4
                G.codex_page = 0
                layout()
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                G.codex_tab = (G.codex_tab + 1) % 4
                G.codex_page = 0
                layout()
            elif e.key in (pygame.K_UP, pygame.K_w, pygame.K_PAGEUP):
                do_action('codeprev')
            elif e.key in (pygame.K_DOWN, pygame.K_s, pygame.K_PAGEDOWN):
                do_action('codenext')
        elif G.scene == 'cards':
            if e.key in (pygame.K_1, pygame.K_KP1):
                choose_card(0)
            elif e.key in (pygame.K_2, pygame.K_KP2):
                choose_card(1)
            elif e.key in (pygame.K_3, pygame.K_KP3):
                choose_card(2)
        elif G.scene in ('dead', 'win'):
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r, pygame.K_SPACE):
                new_run(G.run.ship['id'])
            elif e.key == pygame.K_ESCAPE:
                G.scene = 'select'
                layout()

    elif e.type == pygame.MOUSEMOTION:
        G.pointer = e.pos
        if G.scene == 'play' and G.pdown:
            G.pdrag = True

    elif e.type == pygame.MOUSEBUTTONDOWN:
        G.pointer = e.pos
        if e.button == 1:
            if G.scene == 'play':
                G.pdown = True
                G.pointer = e.pos
                return True
            if G.scene == 'intro':
                skip = G.intro_skip or pygame.Rect(W - 190, H - 82, 130, 38)
                if skip.collidepoint(e.pos):
                    do_action('introskip')
                else:
                    advance_intro()
                return True
            for act, r in G.rects:
                if r.collidepoint(e.pos):
                    do_action(act)
                    break
            else:
                if G.scene == 'select':
                    for i, r in enumerate(G.mode_rects):
                        if r.collidepoint(e.pos):
                            do_action('mode%d' % i)
                            break
        elif e.button == 3 and G.scene == 'play':
            if G.player and G.player.skill_t <= 0:
                cast_skill()
    elif e.type == pygame.MOUSEBUTTONUP:
        if e.button == 1:
            G.pdown = False
            G.pdrag = False
    elif e.type == pygame.KEYUP:
        G.held.discard(e.key)
    elif e.type == pygame.WINDOWFOCUSLOST:
        G.held.clear()
        G.pdown = False
        G.pdrag = False
    return True


# ================================================================
#  主循环
# ================================================================
def draw_scene(dt):
    if G.scene == 'intro':
        draw_intro(SCREEN, dt)
    elif G.scene == 'title':
        draw_title(SCREEN, dt)
    elif G.scene == 'slots':
        draw_slots(SCREEN, dt)
    elif G.scene == 'hub':
        draw_hub(SCREEN, dt)
    elif G.scene == 'shards':
        draw_shards(SCREEN, dt)
    elif G.scene == 'select':
        draw_select(SCREEN, dt)
    elif G.scene == 'settings':
        draw_settings(SCREEN)
    elif G.scene == 'lab':
        draw_lab(SCREEN)
    elif G.scene == 'help':
        draw_help(SCREEN)
    elif G.scene == 'codex':
        draw_codex(SCREEN)
    else:
        if G.run and G.player:
            draw_world(SCREEN, dt)
        if G.scene == 'cards':
            draw_cards(SCREEN)
        elif G.scene == 'pause':
            draw_pause(SCREEN)
        elif G.scene == 'dead':
            draw_dead(SCREEN)
        elif G.scene == 'win':
            draw_win(SCREEN)
    if not HEADLESS:
        want_cursor = G.scene != 'play'
        if want_cursor != G.cursor_visible:
            try:
                pygame.mouse.set_visible(want_cursor)
                G.cursor_visible = want_cursor
            except Exception:
                pass


def boot():
    global SCREEN, DIM
    if not HEADLESS and os.name == 'nt':
        # 高 DPI 屏上别让 Windows 拉伸窗口，字才会清晰、不被缩放糊掉
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    if not HEADLESS:
        pygame.mixer.pre_init(SR, -16, 1, 512)
    pygame.init()
    pygame.display.set_caption('深渊回廊 · v%s · 六模式 · 无尽层域' % VERSION)
    flags = pygame.FULLSCREEN if META.get('fullscreen') else 0
    SCREEN = pygame.display.set_mode((W, H), flags)
    init_joystick()
    try:
        # 关掉文本输入，避免中文输入法抢走 WASD 等字母键
        pygame.key.stop_text_input()
    except Exception:
        pass
    find_font()
    for k in ('aqua', 'amber', 'coral', 'violet', 'green', 'white', 'gold', 'steel'):
        for lvl in (1, 2):
            _glow_base(COL[k], lvl)
    build_bg()
    build_snow()
    build_shaft()
    build_flame()
    for s in SHIPS:
        make_ship(s['col'], s['id'])
    DIM = pygame.Surface((W, H), pygame.SRCALPHA)
    DIM.fill((2, 7, 11, 205))
    AUD.boot()
    AUD.set_master(META.get('vol', .7))
    G.scene = 'title'
    G.menu_sel = 0
    layout()


def main():
    clock = pygame.time.Clock()
    running = True
    try:
        boot()
        while running:
            dt = min(clock.tick(FPS) / 1000.0, 1 / 25)
            for e in pygame.event.get():
                if not handle_event(e):
                    running = False
                    break
            update(dt)
            draw_scene(dt)
            pygame.display.flip()
    except Exception:
        import traceback
        report_crash(traceback.format_exc())
        try:
            pygame.mouse.set_visible(True)
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass
        return
    try:
        pygame.mouse.set_visible(True)
    except Exception:
        pass
    pygame.quit()


def selftest():
    out = []
    try:
        boot()
        out.append('boot ok')
        for sid in [s['id'] for s in SHIPS]:
            new_run(sid)
            for i in range(900):
                if G.scene == 'cards':
                    choose_card(0)
                update(1 / 60)
                draw_scene(1 / 60)
            out.append('%s ok  scene=%s hp=%d score=%d' % (sid, G.scene, G.player.hp, G.run.score))
        new_run('echo')
        G.run.layer = 5
        G.run.wave = waves_for_layer()
        start_wave()
        for i in range(900):
            if G.scene == 'cards':
                choose_card(0)
            update(1 / 60)
            draw_scene(1 / 60)
        out.append('boss ok  boss=%s scene=%s' % (G.boss is not None, G.scene))
        pygame.image.save(SCREEN, os.path.join(os.environ.get('TEMP', '.'), 'abyss_shot_play.png'))
        out.append('screenshot ok')
    except Exception as e:
        import traceback
        out.append('FAIL: ' + repr(e))
        out.append(traceback.format_exc())
    p = os.path.join(os.environ.get('TEMP', '.'), 'abyss_selftest.txt')
    try:
        with open(p, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out))
    except Exception:
        pass
    return p


if __name__ == '__main__':
    try:
        with open(os.path.join(diag_dir(), 'last_start.txt'), 'w', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S') + '  argv=' + ' '.join(sys.argv) + '\n')
    except Exception:
        pass
    try:
        if '--selftest' in sys.argv:
            selftest()
        else:
            main()
    except Exception:
        import traceback
        report_crash(traceback.format_exc())
        sys.exit(1)
