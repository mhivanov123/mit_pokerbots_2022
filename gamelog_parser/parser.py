import pandas as pd
import os
import sys
from matplotlib import pyplot as plt
import re
from typing import List

class Round:
    """
        an object which keeps track of the information in a round of poker (with swaps)
        self.round: round number
        self.button: 0/1 indicating which player (0/1) has the small blind button
            * the challenger (first player) starts with the button in gamelogs. 
            * actions, cards, and awards are all in button order. 
        self.comm: most community cards seen 
        self.cards: list representing pre-flop, flop, and turn cards
            each index has a list of 2 card pairs (in button order) (each card pair is a list)
        self.actions: actions taken by each player (in button order). 
            does not have blinds. recorded in engine format
            C: call, K: check, R#: raise, F: Fold
        self.awards: total amount awarded to each player (in button order)

        These atributes can be accessed without methods. Do not mutate
    """
    def __init__(self, round, button, comm, cards, actions, awards) -> None:
        # 
        # ie. 
        assert(round > 0)
        assert(button == 0 or button == 1)
        assert(len(comm) in {0,3,4,5})
        assert(len(cards) == 3)
        assert(len(actions) == 4)  # and all valid. to be assumed
        assert(len(awards) != 2, abs(awards[0]) <= 200, abs(awards[1]) <= 200)
        self.round = round
        self.button = button
        self.comm = comm
        self.cards = cards
        self.actions = actions
        self.awards = awards

    """
        @ret player number if no tie
            else, return 2
        * adjusted for button
    """
    def winner(self) -> int:
        for p in range(2): # len(self.awards)
            if self.awards[p] > 0:
                return (p+self.button)%2
        return 2

    """
        @ret 
        2x2 list(s) of list of tuples indicating cards swapped
        ex. player 0 has Ad swapped for Kh on turn
            player 1 has 4d swapped for As and Qh swapped for 4c on Flop
        [
            [[], [(Ad, Kh)]] 
            [[(4d, As), (Qh, 4c)], []]
        ]
        First index: player number * adjusted for button
        Second index: 0 - flop swap, 1 - turn swap
    """
    def swaps(self): # -> List[List[int], List[int]]
        ret = [[],[]]
        for swap in range(2):
            for p in range(2):
                player = (p+self.button)%2
                swap_num = 0
                swaps = []
                for card in range(2):
                    if self.cards[swap][player][card] != self.cards[swap+1][player][card]:
                        swaps.append((self.cards[swap][player][card], self.cards[swap+1][player][card]))
                ret[player].append(swaps)
        return ret

    """
        @ret returns the number of betting rounds in this round
        0 - pre flop, 1 - flop, 2 - turn, 3 - river, 4 - showoff
        there is no amount bet during showoff. just for simplicity
    """
    def last_betting_round(self):
        for r in range(len(self.actions)):
            if 'F' == self.actions[r][-1]: # fold can only be last action
                return r
        return 4

    """
        @ret if a player folds, return player number
            else return 2
        * adjusted for button order
    """
    def fold(self):
        last = self.last_betting_round()
        if last == 4:
            return 2
        # button order, so if even, non-button player folds 
        elif len(self.actions[last])%2:
            return (1+self.button)%2
        # otherwise it must be button player
        else:
            return (0+self.button)%2

    """"
        the amount of money the player puts in the pot by given round
        @param round, the round to be summed
        ** round must be less than or equal to last_betting_round.
        - handles round = 4 as award given to player
        @param player num, 
        ** if other player folds, this returns, this includes last raise 
        - this differs from award amount
        @return the total cost for the given round (always positive)

        * player is only relevant when there is a fold
        and when round = last betting round
    """
    def round_cost(self, round, player = 0):
        last = self.last_betting_round()
        winner = (self.winner != (player+1)%2) # if tie, both players are winner
        if not winner and len(self.actions[0]) == 1:
            return 1  
        if round == 4:  # also handles case of tie
            return self.awards[(player+1)%2]

        total = 2
        # if a player folds, last raise is actions[last][-2] since a fold 
        # can only come after a raise except if round == 4 (handled above)
        # this also implies len(actions[last]) >= 2
        if round == last and not winner:
            total -= int(self.actions[round][-2][1:])
        for r in range(round+1): # round is <= 4
            for a in range(len(self.actions[r])):
                if len(self.actions[r][a]) > 1: # only raises are more than 1 char
                    total += int(self.actions[r][a][1:])
        return total

        

def parse(log_path):
    rx_dict = {
        'round': re.compile(r'Round #(?P<round>\d+), .*\((?P<cscore>-?\d+)\), .*\((?P<oscore>-?\d+)\)\n'), 
        'end': re.compile(r'\n'),
        'award': re.compile(r'.+ awarded (-?\d+)\n'),
        'deal': re.compile(r'.+ dealt \[((?:[2-9TJQKA][sdch]\s?)+)\]\n'),
        'hand': re.compile(r'.+\'s hand: \[((?:[2-9TJQKA][sdch]\s?)+)\]\n'),
        'fold': re.compile(r'.+ folds\n'),
        'call': re.compile(r'.+ calls\n'),
        'check': re.compile(r'.+ checks\n'),
        'bet': re.compile(r'.+ bets (\d+)\n'),
        'raise': re.compile(r'.+ raises to (\d+)\n'),
        'flop': re.compile(r'Flop \[((?:[2-9TJQKA][sdch]\s?)+)\].*\n'), # flop turn river parsing does not capture pot contributions
        'turn': re.compile(r'Turn \[((?:[2-9TJQKA][sdch]\s?)+)\].*\n'), # this info can be calculated by a round object's round cost func
        'river': re.compile(r'River \[((?:[2-9TJQKA][sdch]\s?)+)\].*\n')
    }

    rounds = []
    with open(log_path, 'r') as f:
        current = {  # list items are in button order
            "round": 1,
            "button": 0,
            'comm': [],
            "cards": [[], [], []],  # each index has list of two card lists 
            "actions": [[], [], [], []],  # each index has a list of string actions
            "awards": [] # will be of size two 
        }
        complete = True
        betting_round = 0 
        continue_cost = 2  # only used for raise/bet calcs
        line = f.readline()  # None should pose no issue
        while (line):
            match = lambda key: re.fullmatch(rx_dict[key], line)
            round_match = match('round') 
            end_match = match('end')
            award_match = match('award')
            deal_match = match('deal')
            hand_match = match('hand')
            fold_match = match('fold')
            call_match = match('call')
            check_match = match('check')
            bet_match = match('bet')
            raise_match = match('raise')
            flop_match = match('flop')
            turn_match = match('turn')
            river_match = match('river')
            get_cards = lambda m: m.groups()[0].split(" ")

            if round_match:
                complete = False
            elif deal_match:
                current['cards'][betting_round].append(get_cards(deal_match))
            elif hand_match:
                current['cards'][betting_round].append(get_cards(hand_match))
            elif award_match:
                current['awards'].append(int(award_match.groups()[0]))
            elif flop_match:
                current['comm'] = get_cards(flop_match)
                betting_round += 1
                continue_cost = 0
            elif turn_match:
                current['comm'] = get_cards(turn_match)
                betting_round += 1
                continue_cost = 0
            elif river_match:
                current['comm'] = get_cards(river_match)
                betting_round += 1
                continue_cost = 0
            elif fold_match:
                current['actions'][betting_round].append('F')
            elif check_match:
                current['actions'][betting_round].append('K')
            elif call_match:
                current['actions'][betting_round].append('C')
            elif bet_match:
                current['actions'][betting_round].append('R'+str(int(bet_match.groups()[0])))
                continue_cost = int(bet_match.groups()[0])
            elif raise_match: 
                current['actions'][betting_round].append('R'+str(int(raise_match.groups()[0]) - continue_cost))
                continue_cost = int(raise_match.groups()[0])
            elif end_match:
                if not complete:
                    rounds.append(Round(current['round'], current['button'], current['comm'], current['cards'], current['actions'], current['awards']))
                    current['round'] += 1
                    current['button'] = (current['button']+1)%2
                    current['comm'] = []
                    current['cards'] = [[], [], []]
                    current['actions'] = [[], [], [], []]
                    current['awards'] = []
                    betting_round = 0
                    continue_cost = 2
                complete = True
            line = f.readline()  # None should pose no issue
    return rounds

"""
    @param rounds list of round objs
    @param player number (0/1)
    This method is to be used for graphical interpretation of a gamelog
    currently tracks:
        bets: preflop bets, flop bets, turn bets, river bets
        total: total amount won by player
"""
def visual(rounds, player = 0):
    pfy, pfc = [], 'y-'
    fx, fy, fc = [], [], 'm-'
    tx, ty, tc = [], [], 'c-'
    rx, ry, rc = [], [], 'r-'
    deltay, deltac = [], 'g-'

    total = 0
    fig1 = plt.figure(figsize=(30,15))
    delta = fig1.add_subplot()
    fig2 = plt.figure(figsize=(30,15))
    bets = fig2.add_subplot()
    for r in range(len(rounds)):
        total += rounds[r].awards[player]
        last = rounds[r].last_betting_round()
        pfy.append(rounds[r].round_cost(0))
        deltay.append(total)
        if 1 <= last:
            fx.append(r+1)
            fy.append(rounds[r].round_cost(1))
        if 2 <= last:
            tx.append(r+1)
            ty.append(rounds[r].round_cost(2))
        if 3 <= last:
            rx.append(r+1)
            ry.append(rounds[r].round_cost(3)) 
    bets.set_title('Bets')
    bets.plot(pfy, pfc, label = 'Pre-Flop')
    bets.plot(fx, fy, fc, label = 'Flop')
    bets.plot(tx, ty, tc, label = 'Turn')
    bets.plot(rx, ry, rc, label = 'River')

    delta.set_title('Total')
    delta.plot(deltay, deltac, label = 'Total')
    bets.legend()
    plt.show()
    

"""
    @return pandas dataframe with tabular analysis 
    @param rounds list of round objs
    @param player number (0/1)
    This method is to be used for tabular interpretation of a gamelog
    currently tracks: 
        rows: all rounds, pre-flop, flop, turn, river, player folds, other player folds, face-offs 
        cols: title, number of occurences, cummulative delta, avg delta, delta range, avg. # bet round, 
"""
def analysis(rounds, player = 0):
    # all irrellevant values can be filled with None
    NUM_ROWS = 8
    NUM_COLS = 6
    last = lambda round: round.last_betting_round()
    rows = {
        "names": ['All rounds', "pre-flop", "flop", "turn", 
            "river", "face-offs", "player folds","other player folds"],
        "identifiers": [
            lambda round: True,
            lambda round: True, # all rounds get to pre-flop,
            lambda round: True if 1 <= last(round) else False,
            lambda round: True if 2 <= last(round) else False,
            lambda round: True if 3 <= last(round) else False,
            lambda round: True if 4 == last(round) else False,
            lambda round: True if round.fold() == player else False,
            lambda round: True if round.fold() == (player+1)%2 else False
        ],
        "delta_rnd": [ # total cost to be considered (in rounds 
            4, 0, 1, 2, 3, 4, 4, 4] 
    }

    delta = lambda round, r: round.round_cost(rows["delta_rnd"][r], player)
    avg = lambda avg0, sample, base0: (avg0*base0 + sample)/(base0+1)
    cols = {
        "names": [
            "Number Of Occurences", "cummulative Delta", "Avg. Delta", 
            "Min bet", "Max bet", "Avg. # Bet-Rounds"],
        "data": [[x for x in [0, 0, 0, 200, 0, 0]] for _ in range(NUM_ROWS)], # row, column: write in init val (x)
        "calculation": [  # online metric calculation::= lambda round, r, c: <...>
            # c is a known value in a sense, but it is easier/flexible for this as a param
            lambda round, r, c: cols["data"][r][c] + 1,
            lambda round, r, c: cols["data"][r][c] + delta(round, r),
            lambda round, r, c: avg(cols["data"][r][c], delta(round, r), cols["data"][r][0]),
            lambda round, r, c: min(abs(cols["data"][r][c]), abs(delta(round, r))),
            lambda round, r, c: max(abs(cols["data"][r][c]), abs(delta(round, r))),
            lambda round, r, c: avg(cols["data"][r][c], last(round), cols["data"][r][0]),
        ]
    }
    assert(NUM_ROWS == len(x) for x in rows.values()) # size assertion
    assert(NUM_COLS == len(x) for x in cols.values())

    # deltas
    for round in rounds:
        for r in range(NUM_ROWS):
            if rows["identifiers"][r](round):
                for c in range(NUM_COLS): # r corresponds with index of each var
                    cols["data"][r][c] = cols["calculation"][c](round, r, c)

    df = pd.DataFrame({cols["names"][c]: [row[c] for row in cols["data"]] for c in range(NUM_COLS)}, index = rows["names"])
    print(df)
    return df

if __name__ == '__main__':
    # run with path arg to gamelog: from gamelog_parser if interactive
    # from folder root if in terminal
    player = 0 # player 0 is challenger (always starts with button)
    log_path = f"{os.getcwd()}/gamelog_parser/gamelogs/improved_betting.txt"
    rounds = parse(log_path)
    visual(rounds, player = player)
    analysis(rounds, player = player)
    
