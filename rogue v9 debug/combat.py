# combat.py - 전투 진행 담당 (턴 순서, 카드 사용, 몬스터 행동, 상태이상)
# 몬스터 pattern 액션 문자열은 _monster_turn_logic 분기와 항상 맞아야 함
import time
import random
import os
import assets
from assets import STATUS_INFO
from rich.console import Console, Group as RGroup
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# 터미널 셀이 세로로 길어서 너비:높이 2:1로 맞춰야 화면에서 정방형으로 보임
SPRITE_DIR = "sprites"
SPRITE_SIZE = (64, 32)         # 적
PARTY_SPRITE_SIZE = (44, 22)   # 아군

try:
    from rich_pixels import Pixels
    PIXELS_AVAILABLE = True
except ImportError:
    PIXELS_AVAILABLE = False

console = Console()
#플레이어:2 1몬스터:5 2몬스터:5 보스:2
SPRITE_KEY_MAP = {
    # 플레이어
    "전사":         "warrior",
    "마법사":        "mage",
    # 1스테이지 몬스터
    "고블린":        "goblin",
    "늑대":          "wolf",
    "독거미":        "spider",
    "오크 광전사":   "orc",
    "도적":          "thief",
    # 2스테이지 몬스터
    "해골전사":      "skeleton",
    "불도마뱀":      "salamander",
    "저주받은 기사": "cursed_knight",
    "독 마녀":       "witch",
    "광분한 전사":   "berserker",
    # 보스
    "숲의 군주":     "forest_lord",
    "심연의 근원":   "abyss",
}
#특별히 지정된 이미지 이름이 있으면 그걸 쓰고, 없으면 띄어쓰기를 언더바로 바꿔서 이미지 파일 이름을 유추
#만약의 에러 상황에도 게임이 멈추지 않게 대비
def _sprite_basename(name: str):
    # 매핑에 있으면 그걸 쓰고, 없으면 공백을 언더바로 바꿔서 추정
    if name in SPRITE_KEY_MAP:
        return SPRITE_KEY_MAP[name]
    try:
        n = name.replace(' ', '_')
    except Exception:
        n = name
    return n
#캐릭터의 이름과 행동(action) 상태를 조합하여 최종 스프라이트 파일명을 생성
def _sprite_filename(name: str, action: str | None = None):
    base = _sprite_basename(name)
    if action:
        return f"{base}_{action}"
    return base

# 전투 로그
_combat_log: list = []
_MAX_LOG = 7

def _log(msg: str):
    _combat_log.append(msg)
    if len(_combat_log) > _MAX_LOG:
        _combat_log.pop(0)

def _clear_log():
    _combat_log.clear()

#주어진 이름을 기반으로 스프라이트 이미지를 터미널에 렌더링 가능한 객체로 변환
def _render_sprite(name, size=None):
    # 스프라이트 탐색 순서:
    # 1) sprites/{name}_0.png, _1.png, ... 있으면 애니메이션으로
    # 2) sprites/{name}.png
    # 3) sprites/{name}_def.png
    # 4) sprites/error.png
    # 5) 다 없으면 텍스트 표시 (rich-pixels 미설치해도
    if size is None:
        size = SPRITE_SIZE
    if not PIXELS_AVAILABLE:
        return Text("  [rich-pixels 미설치]\n", style="dim red")

    # 파일명 언더바 개수 차이를 허용하려고 후보를 여러 개 시도
    frames = []
    candidates = [name]
    if '_' in name:
        candidates.append(name.replace('_', '__'))
        candidates.append(name.replace('__', '_'))
    candidates.append(name.lower())
    #우선순위에 따른 파일명 후보군(candidates)을 순회하며 이미지 탐색
    for cand in candidates:
        base = os.path.join(SPRITE_DIR, cand)
        i = 0
        found = False
        # 애니메이션 프레임(_0.png, _1.png ...)이 몇 개인지 모르므로 순차 탐색
        while True:
            fpath = f"{base}_{i}.png"
            # 해당 번호의 프레임 파일이 존재하는 경우
            if os.path.exists(fpath):
                frames.append(Pixels.from_image_path(fpath, resize=size))
                i += 1
                found = True
                continue
            # 해당 번호의 파일이 없으면 애니메이션 시퀀스가 끝난 것으로 간주하고 루프 탈출
            break
        if found:
            break
    # 2순위: 단일 프레임 이미지 경로 리스트
    single_candidates = [os.path.join(SPRITE_DIR, f"{c}.png") for c in candidates]
# 3순위: 기본 대체 이미지 경로 리스트 (예: sprites/hero_def.png)
    def_candidates = [os.path.join(SPRITE_DIR, f"{c}_def.png") for c in candidates]
# 4순위: 모든 탐색 실패 시 사용할 최후의 에러 이미지 경로 (예: sprites/error.png)
    error_path = os.path.join(SPRITE_DIR, "error.png")
#최종 결정 단계
    if frames:
        return frames
    for single in single_candidates:
        if os.path.exists(single):
            return Pixels.from_image_path(single, resize=size)
    for def_path in def_candidates:
        if os.path.exists(def_path):
            return Pixels.from_image_path(def_path, resize=size)
    if os.path.exists(error_path):
        return Pixels.from_image_path(error_path, resize=size)
    return Text(f"  [{name}]\n", style="dim")


def _select_frame(frames, cycle_seconds: float = 0.7):
    # 현재 시각 기준으로 애니메이션 프레임 골라줌
    #  예외 처리: 프레임이 없거나 1장뿐이면 계산 생략
    if not frames:
        return None
    if len(frames) == 1:
        return frames[0] 
    #시간 루프 생성 (t는 0.0 ~ cycle_seconds 사이를 무한 반복)
    t = time.time() % cycle_seconds
    # 3. 애니메이션 진행률 계산 (frac은 0.0 ~ 0.999... 사이의 비율)
    frac = t / cycle_seconds
    # 4. 진행률을 바탕으로 현재 보여줄 프레임의 인덱스(번호) 계산
    idx = int(frac * len(frames)) % len(frames)
    return frames[idx]

#보유 중인 유물 목록을 순회하며, 특정 효과(key)의 보너스 수치 총합을 계산합니다.
def _relic_sum(relics, key):
    total = 0
    for r in relics:
        # 유물에 'effect'나 해당 'key'가 없더라도 KeyError 없이 안전하게 0을 더함
        total += r.get('effect', {}).get(key, 0)
    return total


def _init_statuses(entity):
    # 상태이상 딕셔너리 접근 전에 항상 호출, 키에러 방지용
    if 'statuses' not in entity:
        entity['statuses'] = {}


def get_effective_stat(entity, stat_name):
    # 버프/디버프 반영된 실제 수치 반환
    # atk 값 쓸 때는 entity['atk'] 직접 참조하지 말고 이 함수 사용하기
    _init_statuses(entity)
    val = entity.get(stat_name, 0)

    if stat_name == 'atk':
        if entity['statuses'].get('atk_up', 0) > 0:
            val = int(val * 1.2)   # 공격 강화: +20%
        if entity['statuses'].get('weak', 0) > 0:
            val = int(val * 0.75)  # 약화: -25%

    return val


def _apply_def_up(dmg, defender):
    # 방어막: 받는 피해 30% 감소
    if defender.get('statuses', {}).get('def_up', 0) > 0:
        dmg = int(dmg * 0.7)
    return dmg


def _calc_dmg(attacker, defender, mult=1.0):
    # 피해 계산 순서는 항상 공격력 계산 -> 방어막 -> 취약 순으로 고정
    atk = get_effective_stat(attacker, 'atk')
    raw = max(1, int(atk * mult))
    dmg = _apply_def_up(raw, defender)
    return _apply_vulnerable(dmg, defender)


def _apply_vulnerable(dmg, target):
    # 취약: 받는 피해 50% 증가
    _init_statuses(target)
    if target['statuses'].get('vulnerable', 0) > 0:
        dmg = int(dmg * 1.5)
    return dmg


def process_turn_statuses(entity):
    # 턴 종료마다 화상/중독 틱 처리하고 지속시간 1 줄임
    # stun은 여기서 안 건드림, _monster_turn_logic에서 행동할 때 소비하는 방식임
    _init_statuses(entity)
    expired = []

    for status, turns in list(entity['statuses'].items()):
        if turns <= 0:
            expired.append(status)
            continue

        if status == 'stun':
            continue  # stun은 _monster_turn_logic에서 따로 처리

        if status == 'burn':
            dmg = 5
            entity['current_hp'] = max(0, entity['current_hp'] - dmg)
            _log(f"[bold red]🔥 화상! {entity['name']}이(가) {dmg} 피해.[/bold red]")

        elif status == 'poison':
            dmg = turns
            entity['current_hp'] = max(0, entity['current_hp'] - dmg)
            _log(f"[bold green]☠ 중독! {entity['name']}이(가) {dmg} 피해. (남은 스택: {turns - 1})[/bold green]")

        entity['statuses'][status] -= 1
        if entity['statuses'][status] <= 0:
            expired.append(status)

    for s in expired:
        del entity['statuses'][s]

#전투 중 캐릭터나 몬스터 이름 옆에 현재 상태를 보여주는 UI 
def _status_display(entity):
    parts = []
    for key, val in entity.get('statuses', {}).items():
        if val > 0:
            korean_name = STATUS_INFO.get(key, {}).get('name', key.upper())
            parts.append(f"[bold yellow]{korean_name}({val})[/bold yellow]")
    return " ".join(parts)


def _get_intent_text(monster, action):
    # 몬스터 다음 행동 미리 보여줘서 플레이어가 카드 선택할 때 참고하게 함
    base_dmg = get_effective_stat(monster, 'atk')
    intent_map = {
        'normal':            f"[red]일반 공격[/red]       (약 {base_dmg} 피해)",
        'power':             f"[bold red]강타[/bold red]           (약 {int(base_dmg * 1.5)} 피해)",
        'quick':             f"[yellow]속공 선제[/yellow]     (약 {int(base_dmg * 0.8)} 피해)",
        'dark_slash':        f"[magenta]암흑 베기[/magenta]    (약 {int(base_dmg * 1.5)} 피해)",
        'fire_aoe':          f"[red]광역 화염[/red]       (약 {int(base_dmg * 0.7)} 피해 x 전원)",
        'aoe':               f"[red]광역 공격[/red]       (약 {int(base_dmg * 1.1)} 피해 x 전원)",
        'poison_bite':       f"[green]독 이빨[/green]        (약 {int(base_dmg * 0.6)} 피해 + 중독 2스택)",
        'weaken_slash':      f"[yellow]약화 베기[/yellow]     (약 {int(base_dmg * 0.8)} 피해 + 약화 2턴)",
        'vulnerable_strike': f"[magenta]취약 강타[/magenta]    (약 {base_dmg} 피해 + 취약 2턴)",
        'poison_aoe':        f"[green]독 안개[/green]        (전원 약 {int(base_dmg * 0.4)} 피해 + 중독 2스택)",
    }
    return intent_map.get(action, "행동 준비 중")


def _energy_display(char):
    # 후방에서 충전하다가 스왑으로 들어오면 mp 초과할 수 있음, 과충전 상태는 노란색으로 강조
    cur = char['current_energy']
    mp  = char['mp']
    if cur > mp:
        return f"EN [bold yellow]{cur}[/bold yellow]/[dim]{mp}[/dim]  [yellow]과충전![/yellow]"
    return f"EN [cyan]{cur}/{mp}[/cyan]"

#hp바 UI
def _hp_bar(cur, max_hp, length=20):
    ratio = max(cur, 0) / max(max_hp, 1)
    if ratio > 0.5:
        color = "green"
    elif ratio > 0.25:
        color = "yellow"
    else:
        color = "red"
    filled = int(ratio * length)
    return f"[{color}]{'█' * filled}[/{color}][dim]{'░' * (length - filled)}[/dim]"


def draw_combat_screen(player, monster, turn, intent=None, message=None):
    # 좌 우 2단 레이아웃
    console.clear()

    # 상단 헤더
    console.print(Panel(
        f"턴 {turn}  |  {player.gold}G  |  {player.current_floor}층",
        box=box.SQUARE,
        border_style="bright_white",
        padding=(0, 1),
        expand=True
    ))

    # 적 패널
    m_info = "\n".join([
        f"{_hp_bar(monster['current_hp'], monster['hp'], 15)}  [white]{monster['current_hp']}/{monster['hp']}[/white]",
        f"[dim]ATK {monster.get('atk','?')}  SPD {monster.get('spd','?')}[/dim]",
    ])
    m_status = _status_display(monster)
    if m_status:
        m_info += f"\n{m_status}"

    # 적은 action_frame 없이 기본 스프라이트만 씀
    enemy_key = _sprite_filename(monster['name'])
    enemy_sprite = _render_sprite(enemy_key, size=SPRITE_SIZE)
    if isinstance(enemy_sprite, list):
        enemy_sprite = _select_frame(enemy_sprite, cycle_seconds=0.7)

    enemy_panel = Panel(
        RGroup(
            Align.center(enemy_sprite),
            Align.center(Text.from_markup(m_info, style="bright_white"))
        ),
        title=f"[bold bright_red]{monster['name']}[/bold bright_red]",
        border_style="bright_red",
        box=box.SIMPLE,
        padding=(1, 1)
    )

    # 아군 패널 (전방/후방 2칸)
    def _char_section(char, is_front):
        label  = "[bold green]▶ 전방[/bold green]" if is_front else "[dim]  후방[/dim]"
        border = "green" if is_front else "dim"
        stat_lines = [
            f"[bold]{char['name']}[/bold]",
            f"{_hp_bar(char['current_hp'], char['hp'], 12)} {char['current_hp']}/{char['hp']}",
            f"{_energy_display(char)}",
        ]
        buffs = _status_display(char)
        if buffs:
            stat_lines.append(buffs)
        char_key = _sprite_filename(char['name'], char.get('action_frame'))
        char_sprite = _render_sprite(char_key, size=PARTY_SPRITE_SIZE)
        if isinstance(char_sprite, list):
            char_sprite = _select_frame(char_sprite, cycle_seconds=0.7)
        content = RGroup(
            Align.center(char_sprite),
            Text.from_markup("\n".join(stat_lines), style="bright_white"),
        )
        return Panel(
            content,
            title=Text.from_markup(label),
            border_style=border,
            box=box.SIMPLE,
            padding=(2, 1, 1, 1)
        )

    front = player.active_char
    back  = player.party[1 - player.active_index]

    # 3단 레이아웃: 후방 | 전방 | 적
    grid = Table(expand=True, show_header=False, box=box.SIMPLE_HEAVY)
    grid.add_column(ratio=1)  # 후방
    grid.add_column(ratio=1)  # 전방
    grid.add_column(ratio=1)  # 적
    grid.add_row(_char_section(back, False), _char_section(front, True), enemy_panel)
    console.print(grid)

    # 대사창과 전투 로그
    if message is None:
        message = intent or "전투 상황을 확인하세요."
    dialog_panel = Panel(
        Text.from_markup(message, style="bright_white"),
        title="[bold bright_yellow]대사창[/bold bright_yellow]",
        border_style="bright_yellow",
        box=box.ROUNDED,
        padding=(1, 1)
    )

    log_text = "\n".join(_combat_log) if _combat_log else "[bright_white]전투 대기 중...[/bright_white]"
    log_panel = Panel(
        Text.from_markup(log_text, style="bright_white"),
        title="[bold bright_white]전투 기록[/bold bright_white]",
        border_style="bright_white",
        box=box.ROUNDED,
        padding=(1, 1)
    )

    bottom = Table.grid(expand=True)
    bottom.add_column(ratio=2)
    bottom.add_column(ratio=1)
    bottom.add_row(dialog_panel, log_panel)
    console.print(bottom)


def _check_player_alive(player):
    # 전방이 죽으면 후방으로 자동 스왑
    if player.active_char['current_hp'] > 0:
        return True

    other_index = 1 - player.active_index
    if player.party[other_index]['current_hp'] > 0:
        dead_name = player.active_char['name']
        player.active_index = other_index
        _log(f"[bold red]💀 {dead_name} 전사![/bold red] [yellow]→ {player.active_char['name']}(으)로 긴급 교체![/yellow]")
        return True

    return False  # 파티 전멸


def run_combat(player, monster):
    # 반환값: True는 승리, False는 전멸 - world.handle_combat에서 이걸 보고 게임오버 처리함
    turn = 1
    player.init_combat_decks()
    _init_statuses(monster)

    # 전투 시작 유물 효과 처리
    _clear_log()
    poison_stacks = _relic_sum(player.relics, 'poison_start')
    if poison_stacks > 0:
        monster['statuses']['poison'] = poison_stacks
        _log(f"[bold green]☠ 중독 유물 발동! {monster['name']}에게 중독 {poison_stacks}스택![/bold green]")

    burn_turns = _relic_sum(player.relics, 'burn_start')
    if burn_turns > 0:
        monster['statuses']['burn'] = max(monster['statuses'].get('burn', 0), burn_turns)
        _log(f"[bold red]🔥 화염 유물 발동! {monster['name']}에게 화상 {burn_turns}턴![/bold red]")

    pattern = monster.get('pattern', ['normal'])

    while True:
        active = player.active_char
        player.reset_energy()
        player.draw_cards(active, 4)

        # hp_drain 유물 처리 (피의 서약 등)
        # max(1, ...)로 드레인만으로는 캐릭터가 죽지 않게 막아뒀음
        total_drain = _relic_sum(player.relics, 'hp_drain')
        if total_drain > 0 and active['current_hp'] > 1:
            active['current_hp'] = max(1, active['current_hp'] - total_drain)
            drain_names = ", ".join(r['name'] for r in player.relics if r.get('effect', {}).get('hp_drain', 0) > 0)
            _log(f"[dim red]{drain_names} — {active['name']} HP -{total_drain}[/dim red]")

        # turn이 1부터 시작해서 그냥 쓰면 pattern[0]을 건너뜀, (turn-1)로 보정
        current_action = pattern[(turn - 1) % len(pattern)]
        next_action    = pattern[turn % len(pattern)]

        # 선공 결정: quick이면 무조건 몬스터 선공, 그 외엔 SPD 비교, 동점이면 플레이어 선공
        monster_first = False
        if current_action == "quick":
            monster_first = True
            priority_msg = "[bold yellow]경고! 적이 속공 기습을 준비합니다![/bold yellow]"
        elif monster.get('spd', 5) > active.get('spd', 10):
            monster_first = True
            priority_msg = f"[bold red]적이 더 빠릅니다! (적:{monster.get('spd','?')} vs 나:{active.get('spd','?')})[/bold red]"
        elif monster.get('spd', 5) == active.get('spd', 10):
            priority_msg = f"[bold white]속도가 같습니다! 선공 우선 (나:{active.get('spd','?')} vs 적:{monster.get('spd','?')})[/bold white]"
        else:
            priority_msg = f"[bold green]내가 더 빠릅니다! (나:{active.get('spd','?')} vs 적:{monster.get('spd','?')})[/bold green]"

        if monster_first:
            _log(priority_msg)
            prev_index = player.active_index
            _monster_turn_logic(monster, player.active_char, player, current_action, turn)
            if not _check_player_alive(player):
                return False
            # 긴급 스왑 발생했으면 새 전방 캐릭터한테 카드 드로우 해줘야 함, 안 하면 손패가 없음
            if player.active_index != prev_index and not player.active_char['hand']:
                player.draw_cards(player.active_char, 4)

            next_intent = _get_intent_text(monster, next_action)
            if not _player_turn_logic(player, monster, turn, next_intent):
                return True
        else:
            _log(priority_msg)
            current_intent = _get_intent_text(monster, current_action)
            if not _player_turn_logic(player, monster, turn, current_intent):
                return True

            _monster_turn_logic(monster, player.active_char, player, current_action, turn)
            if not _check_player_alive(player):
                return False

        # 턴 종료 - 상태이상 틱 처리
        # back_char를 여기서 미리 저장해야 함, 전방 사망으로 스왑이 일어나도 원래 후방을 처리해야 하니까
        back_char = player.party[1 - player.active_index]

        process_turn_statuses(player.active_char)
        if not _check_player_alive(player):
            return False

        # 후방도 광역기로 화상/중독 걸릴 수 있어서 처리해줌, 후방이 죽어도 전투는 계속 (힐로 부활 가능)
        process_turn_statuses(back_char)

        process_turn_statuses(monster)
        if monster['current_hp'] <= 0:
            _victory_sequence(player, monster)
            return True

        turn += 1
        time.sleep(1)


def _player_turn_logic(player, monster, turn, intent):
    # 카드사용/스왑/턴종료 반복, 몬스터 처치하면 False 반환해서 run_combat이 전투 종료 처리함
    # 스왑은 턴당 1회 제한인데 긴급 교대 카드로 하는 스왑은 이 제한 무시함
    swap_used = False

    while True:
        active = player.active_char
        draw_combat_screen(player, monster, turn, intent)

        energy = active['current_energy']
        other  = player.party[1 - player.active_index]
        other_alive = other['current_hp'] > 0

        if swap_used:
            swap_label = "[dim]2. 스왑 (이미 사용)[/dim]"
        elif not other_alive:
            swap_label = f"[dim]2. 스왑 ({other['name']} 전사)[/dim]"
        else:
            swap_label = "[bold cyan]2.[/bold cyan] 스왑"

        console.print(
            f"  [bold cyan]1.[/bold cyan] 카드 사용 [dim](EN {energy} 남음)[/dim]   "
            f"{swap_label}   "
            f"[bold cyan]3.[/bold cyan] 턴 종료"
        )
        cmd = console.input("  선택: ").strip()

        if cmd == '1':
            result = _handle_card_use(player, monster, active, turn)
            if result == 'swap_free':
                # 긴급 교대 카드는 swap_used 소비 없이 스왑 가능
                other = player.party[1 - player.active_index]
                if other['current_hp'] > 0:
                    player.swap()
                    new_active = player.active_char
                    player.draw_cards(new_active, 4)
                else:
                    console.print(f"  [red]교체할 수 있는 아군이 없습니다![/red]")
                    time.sleep(0.6)
            turn_over = False

        elif cmd == '2':
            if swap_used:
                console.print("  [red]이미 이번 턴에 스왑했습니다![/red]")
                time.sleep(0.6)
                turn_over = False
            elif not other_alive:
                console.print(f"  [red]{other['name']}은(는) 전사해서 스왑할 수 없습니다.[/red]")
                time.sleep(0.6)
                turn_over = False
            else:
                player.swap()
                new_active = player.active_char
                player.draw_cards(new_active, 4)
                console.print(f"  [cyan]{new_active['name']}(으)로 교체되었습니다![/cyan]")
                swap_used = True
                time.sleep(0.8)
                turn_over = False

        elif cmd == '3':
            turn_over = True

        else:
            turn_over = False

        if monster['current_hp'] <= 0:
            _victory_sequence(player, monster)
            return False

        if turn_over:
            break

    return True


def _handle_card_use(player, monster, active, turn):
    # 카드 선택 UI, 효과 적용하고 swap_free 카드면 'swap_free' 반환, 그 외엔 None이나 False
    if not active['hand']:
        remaining = len(active['draw_pile'])
        console.print(f"  [red]손패가 없습니다.[/red] [dim](드로우 파일 잔여: {remaining}장)[/dim]")
        time.sleep(0.8)
        return False

    console.print("  [cyan]현재 손패[/cyan]")
    for i, card_name in enumerate(active['hand'], 1):
        card = assets.CARDS.get(card_name, {})
        console.print(f"    {i}. [bold]{card_name}[/bold] (EN:{card['cost']}) - [dim]{card['description']}[/dim]")
    console.print("    0. 뒤로가기")

    try:
        idx = int(console.input("  사용할 카드 번호: ")) - 1
        if idx == -1:
            return False

        card_name = active['hand'][idx]
        card = assets.CARDS[card_name]

        if active['current_energy'] < card['cost']:
            console.print("  [red]에너지가 부족합니다![/red]")
            time.sleep(0.8)
            return False

        active['current_energy'] -= card['cost']
        active['discard_pile'].append(active['hand'].pop(idx))
        result = _execute_card_effects(card, active, player, monster)

        # 카드 사용 시 짧은 연출 - 데미지 카드랑 독구름은 attack, 힐/버프/디버프는 buff
        _DEBUFF_EFFECTS = {'weak', 'vulnerable', 'burn', 'stun'}
        action_type = None
        if card.get('damage_mult', 0) > 0 or card.get('effect') == 'poison':
            action_type = 'attack'
        elif (card.get('heal', 0) > 0
            or card.get('effect') in ('atk_up', 'def_up', 'mp_restore', 'draw2', 'cleanse')
            or card.get('effect') in _DEBUFF_EFFECTS):
            action_type = 'buff'

        if action_type:
            active['action_frame'] = action_type
            try:
                draw_combat_screen(player, monster, turn, intent=None, message=None)
                time.sleep(0.32)
            finally:
                active.pop('action_frame', None)

        time.sleep(1.2)
        return result

    except (ValueError, IndexError):
        return False


def _execute_card_effects(card, active, player, monster):
    # 카드 effect 분기 처리
    _log(f"[bold cyan]▶ '{card['name']}' 발동![/bold cyan]")
    effect = card.get('effect')
    dur_bonus = _relic_sum(player.relics, 'duration_bonus')

    if card.get('damage_mult', 0) > 0:
        dmg = _calc_dmg(active, monster, card['damage_mult'])
        monster['current_hp'] -= dmg
        _log(f"[bold red]⚔ {monster['name']}에게 {dmg} 피해![/bold red]")

    if effect == 'atk_up':
        for c in player.party:
            _init_statuses(c)
            c['statuses']['atk_up'] = max(c['statuses'].get('atk_up', 0), 3)
        _log("[yellow]⬆ 파티 전체 공격력 상승! (3턴)[/yellow]")

    elif effect == 'def_up':
        _init_statuses(active)
        active['statuses']['def_up'] = max(active['statuses'].get('def_up', 0), 3)
        _log(f"[blue]🛡 {active['name']}의 방어막! (3턴)[/blue]")

    elif effect == 'weak':
        _init_statuses(monster)
        monster['statuses']['weak'] = max(monster['statuses'].get('weak', 0), 2 + dur_bonus)
        _log(f"[yellow]↓ {monster['name']} 약화! 공격력 25% 감소 ({2 + dur_bonus}턴)[/yellow]")

    elif effect == 'vulnerable':
        _init_statuses(monster)
        monster['statuses']['vulnerable'] = max(monster['statuses'].get('vulnerable', 0), 2 + dur_bonus)
        _log(f"[magenta]↓ {monster['name']} 취약! 받는 피해 50% 증가 ({2 + dur_bonus}턴)[/magenta]")

    elif effect == 'poison':
        _init_statuses(monster)
        monster['statuses']['poison'] = monster['statuses'].get('poison', 0) + 3
        total = monster['statuses']['poison']
        _log(f"[bold green]☠ {monster['name']}에게 중독 3스택! (총 {total}스택)[/bold green]")

    elif effect == 'burn':
        _init_statuses(monster)
        monster['statuses']['burn'] = max(monster['statuses'].get('burn', 0), 3 + dur_bonus)
        _log(f"[red]🔥 {monster['name']}에게 화상! ({3 + dur_bonus}턴)[/red]")

    elif effect == 'stun':
        # 보스는 기절 면역임, 디자인 결정
        if monster.get('is_boss', False):
            _log(f"[dim]{monster['name']}은(는) 기절에 면역입니다![/dim]")
        elif random.random() < 0.5:
            _init_statuses(monster)
            monster['statuses']['stun'] = max(monster['statuses'].get('stun', 0), 1)
            _log(f"[bold yellow]⚡ {monster['name']} 기절![/bold yellow]")
        else:
            _log(f"[yellow]{monster['name']}이(가) 기절을 버텼습니다![/yellow]")

    if card.get('heal', 0) > 0:
        heal_amt = card['heal']
        if card['target'] == 'ally':
            console.print("  누구를 치료할까요? [1] 전사  [2] 마법사")
            try:
                t_idx = int(console.input("  대상: ")) - 1
                target = player.party[t_idx]
            except (ValueError, IndexError):
                target = active
            target['current_hp'] = min(target['hp'], target['current_hp'] + heal_amt)
            _log(f"[green]❤ {target['name']}의 체력 {heal_amt} 회복![/green]")

    if effect == 'mp_restore':
        restore = random.randint(2, 3)
        active['current_energy'] += restore
        _log(f"[cyan]✦ {active['name']} 에너지 +{restore}![/cyan]")

    elif effect == 'draw2':
        drawn = player.draw_cards_add(active, 2)
        _log(f"[cyan]✦ {active['name']} — 카드 {drawn}장 추가 드로우![/cyan]")

    elif effect == 'cleanse':
        NEGATIVE = {'burn', 'poison', 'stun', 'vulnerable', 'weak'}
        alive = [c for c in player.party if c['current_hp'] > 0]
        if len(alive) == 1:
            target = alive[0]
        else:
            console.print(f"  해독 대상: [1] {player.party[0]['name']}  [2] {player.party[1]['name']}")
            try:
                t_idx = int(console.input("  대상: ")) - 1
                target = player.party[t_idx] if player.party[t_idx]['current_hp'] > 0 else alive[0]
            except (ValueError, IndexError):
                target = active
        neg = {k: v for k, v in target.get('statuses', {}).items() if k in NEGATIVE and v > 0}
        if not neg:
            _log(f"[dim]{target['name']}에게 제거할 상태이상이 없습니다.[/dim]")
        else:
            worst = None
            for status_name, stacks in neg.items():
                if worst is None or stacks > neg[worst]:
                    worst = status_name
            del target['statuses'][worst]
            korean = STATUS_INFO.get(worst, {}).get('name', worst)
            _log(f"[green]✨ {target['name']}의 {korean} 해제![/green]")

    elif effect == 'swap_free':
        return 'swap_free'

    return None


def _try_dodge(player, active):
    # 단일 공격에 한해서만 회피 판정, AOE 공격에는 이 함수 호출하면 안 됨

    dodge = _relic_sum(player.relics, 'dodge_chance')
    if dodge > 0 and random.random() < dodge:
        _log(f"[bold cyan]💨 {active['name']}이(가) 공격을 회피했습니다! ({int(dodge * 100)}%)[/bold cyan]")
        return True
    return False


def _monster_turn_logic(monster, active, player, action, turn=None):
    # 몬스터 행동 처리, 기절 상태면 행동 스킵하고 기절 1 소비
    # stun을 process_turn_statuses 대신 여기서 소비하는 이유: 기절 걸자마자 그 턴에 공격하는 버그 방지
    _init_statuses(monster)

    if monster['statuses'].get('stun', 0) > 0:
        _log(f"[bold yellow]⚡ {monster['name']}은(는) 기절해 움직이지 못합니다![/bold yellow]")
        monster['statuses']['stun'] -= 1
        if monster['statuses']['stun'] <= 0:
            del monster['statuses']['stun']
        return

    if action == "poison_bite":
        dmg = _calc_dmg(monster, active, 0.6)
        _log(f"[bold green]🐍 {monster['name']}의 독 이빨![/bold green]")
        if _try_dodge(player, active):
            return
        active['current_hp'] -= dmg
        _init_statuses(active)
        active['statuses']['poison'] = active['statuses'].get('poison', 0) + 2
        _log(f"[red]  └ {active['name']}에게 {dmg} 피해 + 중독 2스택[/red]")
        return

    if action == "weaken_slash":
        dmg = _calc_dmg(monster, active, 0.8)
        _log(f"[bold yellow]🗡 {monster['name']}의 약화 베기![/bold yellow]")
        if _try_dodge(player, active):
            return
        active['current_hp'] -= dmg
        _init_statuses(active)
        active['statuses']['weak'] = max(active['statuses'].get('weak', 0), 2)
        _log(f"[red]  └ {active['name']}에게 {dmg} 피해 + 약화 2턴[/red]")
        return

    if action == "vulnerable_strike":
        dmg = _calc_dmg(monster, active, 1.0)
        _log(f"[bold magenta]🗡 {monster['name']}의 취약 강타![/bold magenta]")
        if _try_dodge(player, active):
            return
        active['current_hp'] -= dmg
        _init_statuses(active)
        active['statuses']['vulnerable'] = max(active['statuses'].get('vulnerable', 0), 2)
        _log(f"[red]  └ {active['name']}에게 {dmg} 피해 + 취약 2턴[/red]")
        return

    if action == "poison_aoe":
        _log(f"[bold green]💀 {monster['name']}의 독 안개![/bold green]")
        for c in player.party:
            dmg = _calc_dmg(monster, c, 0.4)
            c['current_hp'] -= dmg
            _init_statuses(c)
            c['statuses']['poison'] = c['statuses'].get('poison', 0) + 2
            _log(f"[red]  └ {c['name']}에게 {dmg} 피해 + 중독 2스택[/red]")
        return

    if action == "fire_aoe":
        _log(f"[bold red]🔥 {monster['name']}의 광역 화염![/bold red]")
        for c in player.party:
            dmg = _calc_dmg(monster, c, 0.7)
            c['current_hp'] -= dmg
            _log(f"[red]  └ {c['name']}에게 {dmg} 피해[/red]")
        return

    if action == "aoe":
        _log(f"[bold red]💢 {monster['name']}의 광역 공격![/bold red]")
        for c in player.party:
            dmg = _calc_dmg(monster, c, 1.1)
            c['current_hp'] -= dmg
            _log(f"[red]  └ {c['name']}에게 {dmg} 피해[/red]")
        return

    mult_map = {
        "quick":      (0.8, f"[bold yellow]⚡ 속공! {monster['name']}이 기습합니다![/bold yellow]"),
        "power":      (1.5, f"[bold red]💥 {monster['name']}의 강타![/bold red]"),
        "dark_slash": (1.5, f"[bold magenta]🌑 {monster['name']}의 암흑 베기![/bold magenta]"),
        "normal":     (1.0, f"[red]⚔ {monster['name']}의 공격![/red]"),
    }
    mult, msg = mult_map.get(action, mult_map["normal"])

    dmg = _calc_dmg(monster, active, mult)
    _log(msg)
    if _try_dodge(player, active):
        return
    active['current_hp'] -= dmg
    _log(f"[red]  └ {active['name']}에게 {dmg} 피해[/red]")

#승리시 받는 돈
def _victory_sequence(player, monster):
    console.clear()
    base = monster.get('reward_gold', 20)
    gold = max(20, random.randint(int(base * 0.8), int(base * 1.2)))
    player.gold += gold
    console.print(Panel(
        f"[bold green]승리! {monster['name']}을(를) 물리쳤습니다![/bold green]\n"
        f"획득: [yellow]+{gold}G[/yellow]   보유: [yellow]{player.gold}G[/yellow]",
        box=box.DOUBLE
    ))
    time.sleep(1.5)
    _card_reward_event(player)

#전투 승리시 보상
def _card_reward_event(player):
   
    alive = [c for c in player.party if c['current_hp'] > 0]
    char = random.choice(alive)
    class_cards = [k for k, v in assets.CARDS.items() if v['class'] == char['name']]
    choices = random.sample(class_cards, min(3, len(class_cards)))

    console.print(f"[bold yellow]새로운 기술을 발견했습니다! ({char['name']})[/bold yellow]")
    for i, card_name in enumerate(choices, 1):
        card = assets.CARDS[card_name]
        console.print(f"  {i}. [cyan]{card['name']}[/] (EN:{card['cost']}) - {card['description']}")
    console.print("  0. 스킵")

    while True:
        cmd = console.input("번호 선택: ").strip()
        if cmd == '0':
            break
        if cmd in [str(j) for j in range(1, len(choices) + 1)]:
            new_card = choices[int(cmd) - 1]

            if len(char['deck']) >= 15:
                console.print("[red]덱이 꽉 찼습니다 (최대 15장). 버릴 카드를 선택하세요:[/red]")
                for idx, name in enumerate(char['deck'], 1):
                    console.print(f"  {idx}. {name}")
                try:
                    drop = int(console.input("번호: ")) - 1
                    char['deck'].pop(drop)
                except (ValueError, IndexError):
                    continue

            char['deck'].append(new_card)
            console.print(f"[bold green]'{new_card}' 카드가 덱에 추가되었습니다![/bold green]")
            break

    time.sleep(1)
