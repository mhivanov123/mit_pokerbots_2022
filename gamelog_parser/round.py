import pandas as pd
import os
import sys
from matplotlib import pyplot as plt
import re

from numpy import round_

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
        winner = (self.winner() != (player+1)%2) # if tie, both players are winner
        if not winner and len(self.actions[0]) == 1:
            return 1  
        if round == 4:  # also handles case of tie
            return self.awards[(player+self.button)%2]

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

    """
        @return The continue cost of the given round
        calculated as the difference between rounds
        @player, the player whose cost to determine
        @param round, must be <= last betting round
        * an input of 4 will be interpretted as 3
        - ie the continue cost of the river
    """
    def continue_cost(self, round, player = 0):
        if round == 4:
            return self.awards[(player+self.button)%2]
        if round == 0:
            return self.round_cost(round, player) 
        return self.round_cost(round, player) - self.round_cost(round -1, player)

"""
    @return list of parsed Round objects
    @param log_path, path to gamelog to be parsed
"""
def parse_gamelog(log_path):
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
