import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import sys

from round import Round, parse_gamelog

"""
    @param rounds list of round objs
    @param player number (0/1)
    This method is to be used for observing locations of certain events
    in a gamelog
    currently tracks:
        bets: preflop bets, flop bets, turn bets, river bets
        total: total amount won by player
"""
def visual(rounds, player = 0):
    pfy, pfc = [], 'yo'  # preflop
    fx, fy, fc = [], [], 'mo'  # flop
    tx, ty, tc = [], [], 'co'  # turn
    rx, ry, rc = [], [], 'ro'  # river
    psx, psy, psc = [[] for _ in range(4)], [[] for _ in range(4)], 'ko' # player strengths
    opsx, opsy, opsc = [[] for _ in range(4)], [[] for _ in range(4)], 'ro' # opponent strengths


    fig1 = plt.figure(figsize=(30,15))
    strength = fig1.add_subplot()
    fig2 = plt.figure(figsize=(30,15))
    bets = fig2.add_subplot()
    for r in range(len(rounds)):
        ps = rounds[r].calc_strength(player = player, swaps = True)
        ops = rounds[r].calc_strength(player = (player+1)%2, swaps = True)
        for b in range(3):
            if ps[b]:
                psx[b].append(r)
                psy[b].append(ps[b])
            if ops[b]:
                opsx[b].append(r)
                opsy[b].append(ops[b])

        last = rounds[r].last_betting_round()
        pot = rounds[r].continue_cost(0, player)
        pfy.append(pot)
        if 1 <= last:
            fx.append(r+1)
            fy.append(rounds[r].continue_cost(1, player))
        if 2 <= last:
            tx.append(r+1)
            ty.append(rounds[r].continue_cost(2, player))
        if 3 <= last:
            rx.append(r+1)
            ry.append(rounds[r].continue_cost(3, player)) 
    bets.set_title('Bets')
    bets.plot(pfy, pfc, label = 'Pre-Flop')
    bets.plot(fx, fy, fc, label = 'Flop')
    bets.plot(tx, ty, tc, label = 'Turn')
    bets.plot(rx, ry, rc, label = 'River')
    bets.legend()

    strength.set_title('Strength')
    strength.plot(psx[1], psy[1], psc, label = "player turn strength")
    strength.plot(opsx[1], opsy[1], opsc, label = "opp. turn strength")
    strength.legend()

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
    NUM_ROWS = 9
    NUM_COLS = 6
    last = lambda round: round.last_betting_round()
    rows = {
        "names": ['All rounds', "pre-flop", "flop", "turn", 
            "river", "face-offs", "player folds","other player folds", "fold diff"],
        "identifiers": [
            lambda round: True,
            lambda round: True, # all rounds get to pre-flop,
            lambda round: True if 1 <= last(round) else False,
            lambda round: True if 2 <= last(round) else False,
            lambda round: True if 3 <= last(round) else False,
            lambda round: True if 4 == last(round) else False,
            lambda round: True if round.fold() == player else False,
            lambda round: True if round.fold() == (player+1)%2 else False,
            lambda round: True if round.fold() != 2 else False,
        ],
        "occurrences": [[] for _ in range(NUM_ROWS)],  # tracks round #'s when row is tracked
        "delta_rnd": [ # total cost to be considered (in rounds 
            4, 0, 1, 2, 3, 4, 4, 4, 4],
    }

    delta = lambda round, r: round.continue_cost(rows["delta_rnd"][r], player) # delta is the continue cost of interest
    avg = lambda avg0, sample, base0: (avg0*base0 + sample)/(base0+1)
    cols = {
        "names": [
            "Number Of Occurences", "cummulative Delta", "Avg. Delta", 
            "Min bet", "Max bet", "Avg. # Bet-Rounds"],
        "data": [[x for x in [0, 0, 0, 200, 0, 0]] for _ in range(NUM_ROWS)], # row, column: write in init val (x)
        "history": [[ [] for _ in range(NUM_COLS)] for _ in range(NUM_ROWS)], # tracks amount in real time (think moving average)
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

    
    row_ind = {rows["names"][i]: i for i in range(len(rows["names"]))}
    col_ind = {cols["names"][i]: i for i in range(len(cols["names"]))}

    # deltas
    for n in range(len(rounds)):
        round = rounds[n]
        for r in range(NUM_ROWS):
            if rows["identifiers"][r](round):
                rows["occurrences"][r].append(n)
                for c in range(NUM_COLS): # r corresponds with index of each var
                    calc = cols["calculation"][c](round, r, c)
                    cols["data"][r][c] = calc
                    cols["history"][r][c].append(calc)

    fig1 = plt.figure(figsize=(30,15))
    total = fig1.add_subplot()
    total.set_title('Cummulative')
    num_rounds = cols["data"][row_ind["All rounds"]][col_ind["Number Of Occurences"]]
    total.plot(np.linspace(num_rounds*1.5, 0, num_rounds), "k--", label = "upper threshold")
    total.plot(np.linspace(-num_rounds*1.5, 0, num_rounds), "k--", label = "lower threshold")
    total.plot(
        rows["occurrences"][row_ind["All rounds"]],
        cols["history"][row_ind["All rounds"]][col_ind["cummulative Delta"]],
        "r-", label = 'Total')
    total.plot(
        rows["occurrences"][row_ind["face-offs"]],
        cols["history"][row_ind["face-offs"]][col_ind["cummulative Delta"]],
        "b-", label = 'face-off total')
    total.plot(
        rows["occurrences"][row_ind["fold diff"]],
        cols["history"][row_ind["fold diff"]][col_ind["cummulative Delta"]],
        "g-", label = 'fold total')
    total.legend()
    plt.show()


    df = pd.DataFrame({cols["names"][c]: [row[c] for row in cols["data"]] for c in range(NUM_COLS)}, index = rows["names"])
    print(df)
    return df

if __name__ == '__main__':
    # run with path arg to gamelog: from gamelog_parser if interactive
    # from folder root if in terminal
    player = 0 # player 0 is challenger (always starts with button)
    log_path = "gamelogs/grandcentral1.txt"
    rounds = parse_gamelog(log_path)
    visual(rounds, player = player)
    analysis(rounds, player = player)
    
