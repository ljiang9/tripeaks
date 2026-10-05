#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tripeaks: 终端三峰纸牌 (TriPeaks solitaire)。纯标准库。

玩法: 牌桌 28 张(3 个峰 + 底行 10 张), 牌库 23 张, 废牌堆首张明牌。
把与废牌堆顶「点数相邻」(差 1)的明牌移到废牌堆; 无牌可走时从牌库摸牌。
清光牌桌即胜利; 牌库摸完且无牌可走即失败。
计分: 连续走牌(不摸牌)形成连击, 第 n 次连走得 10*n 分; 摸牌清零连击。
相邻判定: A 与 K 不相邻(无回绕), 这是有意的设计选择。
"""

import argparse
import random
import secrets
import sys

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}  # 2..14
SUITS = ["♠", "♥", "♦", "♣"]

# 牌桌索引 0..27。三个峰各 6 张(顶1/中2/底3), 底行 10 张。
# COVERS[i] = 压住 i 的牌: 它们全部被拿走后 i 才翻开。
# 底行中 18 只压 3、27 只压 17, 其余每张压相邻两张峰底牌。
COVERS = {
    0: (1, 2), 1: (3, 4), 2: (4, 5),
    6: (7, 8), 7: (9, 10), 8: (10, 11),
    12: (13, 14), 13: (15, 16), 14: (16, 17),
    3: (18, 19), 4: (19, 20), 5: (20, 21),
    9: (21, 22), 10: (22, 23), 11: (23, 24),
    15: (24, 25), 16: (25, 26), 17: (26, 27),
}

CELL_W = 7
POS = {
    0: 7, 1: 3, 2: 11, 3: 0, 4: 7, 5: 14,
    6: 35, 7: 31, 8: 39, 9: 28, 10: 35, 11: 42,
    12: 63, 13: 59, 14: 67, 15: 56, 16: 63, 17: 70,
    18: 0, 19: 7, 20: 14, 21: 21, 22: 28, 23: 35,
    24: 49, 25: 56, 26: 63, 27: 70,
}
ROWS = [
    [0, 6, 12],
    [1, 2, 7, 8, 13, 14],
    [3, 4, 5, 9, 10, 11, 15, 16, 17],
    [18, 19, 20, 21, 22, 23, 24, 25, 26, 27],
]
LINE_W = 77


def card_text(card):
    r, s = card
    return f"{r}{s}"


class Game:
    def __init__(self, seed=None):
        rng = random.Random(seed) if seed is not None else random.Random(secrets.randbits(64))
        deck = [(r, s) for s in SUITS for r in RANKS]
        rng.shuffle(deck)
        self.tableau = deck[:28]   # 索引 -> 牌, 拿走后为 None
        self.stock = deck[28:51]   # 23 张
        self.waste = deck[51]
        self.score = 0
        self.streak = 0
        self.draws = 0
        self.removed = 0

    def face_up(self, i):
        """牌还在桌上且压它的牌都被拿走 -> 明牌。"""
        return self.tableau[i] is not None and all(
            self.tableau[c] is None for c in COVERS.get(i, ()))

    def available(self):
        return [i for i in range(28) if self.face_up(i)]

    @staticmethod
    def adjacent(a, b):
        """两张牌点数差 1 即相邻。A(14) 与 K(13) 相邻, 但 K 与 A 之间无回绕到 2。"""
        return abs(RANK_VALUE[a[0]] - RANK_VALUE[b[0]]) == 1

    def moves(self):
        return [i for i in self.available() if Game.adjacent(self.tableau[i], self.waste)]

    def remove(self, i):
        if i not in self.moves():
            raise ValueError(f"第 {i} 张不是合法走法")
        card = self.tableau[i]
        self.tableau[i] = None
        self.waste = card
        self.removed += 1
        self.streak += 1
        self.score += 10 * self.streak

    def draw(self):
        if not self.stock:
            raise ValueError("牌库已空")
        self.waste = self.stock.pop()
        self.draws += 1
        self.streak = 0

    def won(self):
        return all(c is None for c in self.tableau)

    def stuck(self):
        return not self.moves() and not self.stock


def uncover_count(g, i):
    """走第 i 张能直接翻开几张暗牌(贪心机器人用)。"""
    n = 0
    for j in range(28):
        if g.tableau[j] is None or g.face_up(j):
            continue
        if i in COVERS.get(j, ()):
            n += 1
    return n


def auto_play(seed=None):
    """贪心机器人: 每次走能翻开最多暗牌的可走牌, 无牌可走则摸牌。"""
    g = Game(seed)
    while not g.won():
        m = g.moves()
        if m:
            best = max(m, key=lambda i: uncover_count(g, i))
            g.remove(best)
        elif g.stock:
            g.draw()
        else:
            break
    return g


def render(g):
    lines = []
    for row in ROWS:
        line = [" "] * LINE_W
        for i in row:
            x = POS[i]
            if g.tableau[i] is None:
                cell = " " * CELL_W
            elif g.face_up(i):
                cell = f"{i:2d}:{card_text(g.tableau[i])}".ljust(CELL_W)
            else:
                cell = f"{i:2d}:##".ljust(CELL_W)
            for k, ch in enumerate(cell[:CELL_W]):
                if x + k < LINE_W:
                    line[x + k] = ch
        lines.append("".join(line).rstrip())
    lines.append(f"废牌堆: {card_text(g.waste)}  牌库: {len(g.stock)} 张  "
                 f"得分: {g.score}  连击: {g.streak}  已移走: {g.removed}/28")
    return "\n".join(lines)


def play_interactive(seed=None):
    if not sys.stdin.isatty():
        print("error: 交互模式需要终端, 管道/脚本请用 --auto", file=sys.stderr)
        return 2
    g = Game(seed)
    while True:
        print(render(g))
        if g.won():
            print(f"🎉 胜利! 得分 {g.score}, 共摸牌 {g.draws} 次。")
            return 0
        m = g.moves()
        if m:
            print("可走:", " ".join(str(i) for i in m))
        elif g.stock:
            print("没有可走的牌, 输入 d 从牌库摸牌。")
        else:
            print(f"无牌可走, 游戏结束。得分 {g.score}, 移走 {g.removed}/28 张。")
            return 0
        try:
            cmd = input("走牌输入编号 / d 摸牌 / q 退出: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return 0
        if cmd == "q":
            print("已退出。")
            return 0
        if cmd == "d":
            if not g.stock:
                print("牌库已空, 不能摸牌。")
                continue
            g.draw()
            continue
        try:
            i = int(cmd)
        except ValueError:
            print("请输入 0-27 的编号、d 或 q。")
            continue
        if not 0 <= i <= 27:
            print("编号超出范围 (0-27)。")
            continue
        try:
            g.remove(i)
        except ValueError as e:
            print(e)


def main(argv=None):
    ap = argparse.ArgumentParser(description="三峰纸牌 TriPeaks: 终端纸牌接龙")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--auto", action="store_true", help="贪心机器人自动游玩")
    args = ap.parse_args(argv)
    if args.auto:
        g = auto_play(args.seed)
        result = "胜利" if g.won() else "失败"
        print(f"自动游玩结束: {result}, 得分 {g.score}, "
              f"移走 {g.removed}/28 张, 摸牌 {g.draws} 次。")
        return 0
    return play_interactive(args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
